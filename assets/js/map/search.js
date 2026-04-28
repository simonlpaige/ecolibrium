/**
 * search.js: thin glue between the "What are you trying to do?" panel and
 * the scoring engine.
 *
 * Reads window.allPoints / window.allEdges set by map.html, plus the city
 * centroids file fetched at boot. Renders results into #need-result and
 * pushes a transient deck.gl edge layer (user_need_match) onto the map via
 * window._setNeedHighlight(...).
 *
 * All DOM is built with textContent / appendChild; no innerHTML.
 */
(function (global) {
  'use strict';

  let centroids = null;
  let lastResult = null;

  async function loadCentroids() {
    if (centroids) return centroids;
    try {
      const r = await fetch('data/map/city_centroids.json');
      if (!r.ok) throw new Error('city_centroids missing');
      const j = await r.json();
      centroids = j.centroids || [];
    } catch (e) {
      console.warn('city centroids unavailable, location parsing disabled:', e);
      centroids = [];
    }
    return centroids;
  }

  function appendText(el, text) {
    el.appendChild(document.createTextNode(text));
  }
  function appendStrong(el, text) {
    const s = document.createElement('strong');
    s.textContent = text;
    el.appendChild(s);
  }

  function renderSummary(container, parsed) {
    const el = document.createElement('div');
    el.className = 'nr-summary';
    const segments = [];
    if (parsed.location) {
      const span = document.createElement('span');
      appendText(span, 'near ');
      appendStrong(span, parsed.location.city + ', ' + parsed.location.country);
      segments.push(span);
    }
    if (parsed.sections.length) {
      const span = document.createElement('span');
      span.textContent = 'sections: ' + parsed.sections.join(', ');
      segments.push(span);
    }
    if (parsed.needs.length) {
      const span = document.createElement('span');
      span.textContent = 'needs/offers: ' + parsed.needs.join(', ');
      segments.push(span);
    }
    if (segments.length === 0) {
      const em = document.createElement('em');
      em.textContent = 'no recognisable location, sections, or needs - showing global matches';
      el.appendChild(em);
    } else {
      segments.forEach((seg, i) => {
        if (i) appendText(el, ' · ');
        el.appendChild(seg);
      });
    }
    container.appendChild(el);
  }

  function renderRow(scored) {
    const o = scored.org;
    const pct = Math.round((scored.score || 0) * 100);
    const meta = [o.cc, o.f].filter(Boolean).join(' · ');
    const a = document.createElement('a');
    a.className = 'nr-row';
    a.href = '#' + o.id;
    a.setAttribute('data-org-id', o.id);
    const name = document.createElement('div');
    name.className = 'nr-name';
    name.textContent = o.n || o.id;
    const m = document.createElement('div');
    m.className = 'nr-meta';
    m.textContent = meta + ' · score ' + pct + '%';
    a.appendChild(name);
    a.appendChild(m);
    return a;
  }

  function renderResult(parsed, result) {
    const el = document.getElementById('need-result');
    if (!el) return;
    el.hidden = false;
    while (el.firstChild) el.removeChild(el.firstChild);

    renderSummary(el, parsed);

    const matchesH = document.createElement('h4');
    matchesH.textContent = 'Best matches (' + result.matches.length + ')';
    el.appendChild(matchesH);
    if (result.matches.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'nr-empty';
      empty.textContent = 'No direct matches in radius. Try a wider section list or different city.';
      el.appendChild(empty);
    } else {
      result.matches.forEach(m => el.appendChild(renderRow(m)));
    }

    if (result.complements.length) {
      const compH = document.createElement('h4');
      compH.textContent = 'Complementary nearby';
      el.appendChild(compH);
      result.complements.forEach(c => el.appendChild(renderRow(c)));
    }

    if (result.gaps.length) {
      const gapsH = document.createElement('h4');
      gapsH.textContent = 'Local gaps';
      el.appendChild(gapsH);
      const gapsRow = document.createElement('div');
      gapsRow.className = 'nr-gaps';
      gapsRow.textContent = result.gaps.join(', ').replace(/_/g, ' ');
      el.appendChild(gapsRow);
    }

    el.querySelectorAll('.nr-row').forEach(row => {
      row.addEventListener('click', (e) => {
        e.preventDefault();
        const id = row.getAttribute('data-org-id');
        if (typeof global._selectOrgById === 'function') global._selectOrgById(id);
      });
    });
  }

  async function run() {
    const input = document.getElementById('need-input');
    const clearBtn = document.getElementById('need-clear');
    if (!input) return;
    const text = input.value.trim();
    if (!text) {
      const el = document.getElementById('need-result');
      if (el) { el.hidden = true; while (el.firstChild) el.removeChild(el.firstChild); }
      if (clearBtn) clearBtn.hidden = true;
      if (typeof global._setNeedHighlight === 'function') global._setNeedHighlight(null);
      lastResult = null;
      return;
    }
    await loadCentroids();
    const parsed = global.CommonweaveScoring.parseQuery(text, centroids);
    const result = global.CommonweaveScoring.runQuery(parsed, global.allPoints || [], { maxResults: 10 });
    lastResult = result;
    renderResult(parsed, result);
    if (clearBtn) clearBtn.hidden = false;

    if (typeof global._setNeedHighlight === 'function') {
      global._setNeedHighlight({
        location: parsed.location,
        matches: result.matches,
        complements: result.complements,
      });
    }

    if (parsed.location && global.mlMap && global.viewMode === 'geo') {
      try {
        global.mlMap.flyTo({ center: [parsed.location.lon, parsed.location.lat], zoom: 6 });
      } catch (_) { /* MapLibre not yet initialised; ignore. */ }
    }
  }

  function clear() {
    const input = document.getElementById('need-input');
    if (input) input.value = '';
    run();
  }

  function init() {
    const goBtn = document.getElementById('need-go');
    const clearBtn = document.getElementById('need-clear');
    const input = document.getElementById('need-input');
    if (goBtn) goBtn.addEventListener('click', run);
    if (clearBtn) clearBtn.addEventListener('click', clear);
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          run();
        }
      });
    }
    loadCentroids();
  }

  global.CommonweaveSearch = { init, run, clear, lastResult: () => lastResult };
})(typeof window !== 'undefined' ? window : globalThis);
