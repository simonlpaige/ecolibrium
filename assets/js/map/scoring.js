/**
 * scoring.js: need-pathway and viewport System Health scoring.
 *
 * Pure functions. Reads from window.allPoints / window.allEdges (set by the
 * map shell). No DOM access. No fetch. The map calls these and renders the
 * results.
 *
 * The scoring formulas come straight from MAP-V3-BRIEF.md sections 4 and 10.
 */
(function (global) {
  'use strict';

  // Section keyword vocabulary. The parser maps user words to framework
  // section ids; ids match data/taxonomy.yaml.
  const SECTION_KEYWORDS = {
    democracy: ['democracy', 'participatory', 'civic', 'government', 'election', 'budgeting', 'voting', 'governance'],
    cooperatives: ['cooperative', 'co-op', 'coop', 'co-operative', 'mutual', 'solidarity', 'worker-owned', 'mondragon'],
    healthcare: ['health', 'medical', 'clinic', 'mutual aid', 'community health', 'wellness', 'mental health'],
    food: ['food', 'farm', 'farming', 'agriculture', 'agroecology', 'csa', 'garden', 'food sovereignty', 'pantry'],
    education: ['education', 'school', 'teaching', 'literacy', 'tutoring', 'university', 'learning'],
    housing_land: ['housing', 'land trust', 'clt', 'shelter', 'tenant', 'homes', 'real estate', 'eviction', 'rent'],
    conflict: ['conflict', 'mediation', 'restorative', 'peace', 'reconciliation', 'transformative justice'],
    energy_digital: ['energy', 'solar', 'renewable', 'digital', 'platform', 'technology', 'broadband', 'open source'],
    recreation_arts: ['art', 'arts', 'music', 'culture', 'recreation', 'theater', 'community center'],
    ecology: ['ecology', 'restoration', 'wildlife', 'conservation', 'reforest', 'biodiversity', 'watershed', 'forest'],
  };

  // Needs / offers vocabulary. Match across user query and (later) org records.
  const NEEDS_OFFERS = [
    'volunteers', 'volunteer', 'funding', 'grants', 'donations', 'donors',
    'training', 'mentorship', 'legal support', 'legal', 'pro bono',
    'land', 'housing', 'space', 'office space', 'equipment',
    'mutual aid', 'tools', 'software', 'platform', 'website',
    'translation', 'interpreters', 'food', 'transportation', 'childcare',
    'storage', 'meeting space', 'venue',
  ];

  function tokenize(text) {
    return (text || '').toLowerCase().match(/[a-zA-Z][a-zA-Z'-]+/g) || [];
  }

  function extractSections(text) {
    const tokens = (text || '').toLowerCase();
    const found = new Set();
    for (const [section, keywords] of Object.entries(SECTION_KEYWORDS)) {
      for (const kw of keywords) {
        if (tokens.includes(kw.toLowerCase())) {
          found.add(section);
          break;
        }
      }
    }
    return Array.from(found);
  }

  function extractNeeds(text) {
    const lower = (text || '').toLowerCase();
    return NEEDS_OFFERS.filter(n => lower.includes(n));
  }

  // Find a city by name in the centroids file. Matches case-insensitively
  // with word boundaries; returns the longest name match, breaking ties by
  // org count (so "Kansas City" beats "Kansas" when both are in the file).
  function findCity(text, centroids) {
    if (!text || !centroids) return null;
    const lower = text.toLowerCase();
    let best = null;
    centroids.forEach(c => {
      const cityLower = (c.city || '').trim().toLowerCase();
      if (!cityLower || cityLower.length < 3) return;
      // Strip the city name down to ASCII alpha+space for the boundary
      // regex. If it collapses to empty (e.g. all Greek letters), fall back
      // to a plain `includes` of the raw lowercase name.
      const ascii = cityLower.replace(/[^a-z\s]/g, '').trim();
      let hit = false;
      if (ascii) {
        const escaped = ascii.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        hit = new RegExp('\\b' + escaped + '\\b', 'i').test(text);
      } else {
        hit = lower.includes(cityLower);
      }
      if (!hit) return;
      // Prefer longer matches first, break ties by org count.
      if (!best || cityLower.length > best.city.toLowerCase().length ||
          (cityLower.length === best.city.toLowerCase().length && c.count > best.count)) {
        best = c;
      }
    });
    return best;
  }

  // Haversine distance, km.
  function distKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dlat = (lat2 - lat1) * Math.PI / 180;
    const dlon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dlat / 2) ** 2 +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dlon / 2) ** 2;
    return R * 2 * Math.asin(Math.sqrt(a));
  }

  /**
   * Parse free-text need query into a structured record.
   *
   * { goal, location: {city, lat, lon, radius_km}, sections, needs }
   */
  function parseQuery(text, centroids) {
    const sections = extractSections(text);
    const needs = extractNeeds(text);
    const city = findCity(text, centroids);
    return {
      raw: text,
      sections,
      needs,
      location: city ? {
        city: city.city,
        region: city.region,
        country: city.country,
        lat: city.lat,
        lon: city.lon,
        radius_km: 250,
      } : null,
    };
  }

  /**
   * Score a candidate org against a parsed query in [0, 1].
   *
   *   0.45 * section_match
   * + 0.35 * proximity (1 - dist/radius, clipped)
   * + 0.20 * needs_offers_overlap
   *
   * Sections matter most because we're answering "who does X near here";
   * proximity matters next; offers/needs matters less because the data is
   * thin (most orgs do not declare offers/needs yet).
   */
  function scoreOrg(org, query) {
    let sectionMatch = 0;
    if (query.sections && query.sections.length) {
      sectionMatch = query.sections.includes(org.f) ? 1.0 : 0.0;
    } else {
      sectionMatch = 0.5;
    }
    let proximity = 0.5;
    if (query.location && org.lo !== undefined && org.la !== undefined) {
      const d = distKm(query.location.lat, query.location.lon, org.la, org.lo);
      const r = query.location.radius_km || 250;
      proximity = Math.max(0, 1 - d / r);
    }
    let needsOverlap = 0;
    if (query.needs && query.needs.length) {
      const hay = ((org.d || '') + ' ' + (org.n || '')).toLowerCase();
      const hits = query.needs.filter(n => hay.includes(n.toLowerCase())).length;
      needsOverlap = Math.min(1, hits / query.needs.length);
    }
    return Math.min(1.0, 0.45 * sectionMatch + 0.35 * proximity + 0.20 * needsOverlap);
  }

  /**
   * Run a need query against the map's points. Returns:
   *   { matches: [...], complements: [...], gaps: [...], summary }
   */
  function runQuery(query, points, opts) {
    opts = opts || {};
    const minScore = opts.minScore != null ? opts.minScore : 0.40;
    const maxResults = opts.maxResults || 10;
    const radius = (query.location && query.location.radius_km) || 250;

    const inRadius = (org) => {
      if (!query.location) return true;
      if (org.lo === undefined || org.la === undefined) return false;
      return distKm(query.location.lat, query.location.lon, org.la, org.lo) <= radius;
    };

    const candidates = points.filter(p => inRadius(p));
    const scored = candidates.map(p => ({ org: p, score: scoreOrg(p, query) }));

    const matches = scored
      .filter(r => r.score >= minScore && (!query.sections.length || query.sections.includes(r.org.f)))
      .sort((a, b) => b.score - a.score)
      .slice(0, maxResults);

    // Complementary: in-radius, NOT in the requested sections, but in a section
    // that complements one of the requested sections.
    const complementaryPairs = {
      food: ['housing_land', 'cooperatives', 'ecology'],
      housing_land: ['food', 'cooperatives', 'democracy'],
      healthcare: ['education', 'conflict'],
      energy_digital: ['cooperatives', 'democracy'],
      education: ['democracy', 'healthcare'],
      ecology: ['food'],
      cooperatives: ['food', 'housing_land', 'energy_digital'],
      democracy: ['housing_land', 'education', 'energy_digital'],
      conflict: ['healthcare'],
    };
    const compSections = new Set();
    query.sections.forEach(s => (complementaryPairs[s] || []).forEach(c => compSections.add(c)));
    const compSet = new Set(matches.map(m => m.org.id));
    const complements = scored
      .filter(r => !compSet.has(r.org.id) && compSections.has(r.org.f))
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    // Local gaps: which framework sections are NOT represented in the radius?
    const sectionsPresent = new Set(candidates.map(p => p.f));
    const allSections = ['democracy', 'cooperatives', 'healthcare', 'food', 'education',
                         'housing_land', 'conflict', 'energy_digital', 'recreation_arts', 'ecology'];
    const gaps = allSections.filter(s => !sectionsPresent.has(s));

    return {
      query,
      matches,
      complements,
      gaps,
      summary: {
        candidates: candidates.length,
        kept: matches.length,
        radius_km: radius,
      },
    };
  }

  /**
   * Compute viewport System Health (Phase 4): which sections are present /
   * missing in the visible bbox, the verified ratio, and a few suggested
   * bridge orgs.
   */
  function computeViewportHealth(bbox, points, edges) {
    const inside = points.filter(p => {
      return p.lo >= bbox.west && p.lo <= bbox.east &&
             p.la >= bbox.south && p.la <= bbox.north;
    });
    const sectionCount = {};
    let verifiedCount = 0;
    inside.forEach(p => {
      sectionCount[p.f] = (sectionCount[p.f] || 0) + 1;
      if (p.t === 'A' || p.t === 'B') verifiedCount++;
    });
    const allSections = ['democracy', 'cooperatives', 'healthcare', 'food', 'education',
                         'housing_land', 'conflict', 'energy_digital', 'recreation_arts', 'ecology'];
    const present = allSections.filter(s => (sectionCount[s] || 0) > 0);
    const missing = allSections.filter(s => !(sectionCount[s] || 0));
    // "Strongest" / "weakest" ranked by raw count.
    const ranked = Object.entries(sectionCount).sort((a, b) => b[1] - a[1]);
    const strongest = ranked.slice(0, 3).map(r => r[0]);
    const weakest = ranked.slice(-3).map(r => r[0]).filter(s => sectionCount[s] > 0);

    // Suggested bridges: high-degree orgs in this viewport (most edges to
    // others in the viewport). Cheap proxy for "most networked here".
    const insideIds = new Set(inside.map(p => p.id));
    const degree = new Map();
    (edges || []).forEach(e => {
      if (insideIds.has(e.source_id) && insideIds.has(e.target_id)) {
        degree.set(e.source_id, (degree.get(e.source_id) || 0) + 1);
        degree.set(e.target_id, (degree.get(e.target_id) || 0) + 1);
      }
    });
    const bridges = Array.from(degree.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5).map(r => r[0]);

    return {
      viewport_org_count: inside.length,
      sections_present: present.length,
      sections_missing: missing,
      strongest_sections: strongest,
      weakest_sections: weakest,
      verified_ratio: inside.length ? verifiedCount / inside.length : 0,
      suggested_bridges: bridges,
    };
  }

  global.CommonweaveScoring = {
    parseQuery,
    runQuery,
    scoreOrg,
    distKm,
    computeViewportHealth,
    SECTION_KEYWORDS,
    NEEDS_OFFERS,
  };
})(typeof window !== 'undefined' ? window : globalThis);
