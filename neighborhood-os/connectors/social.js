// connectors/social.js
// Social platform data collection for NeighborhoodOS.
// Nextdoor and Facebook Groups - the two platforms where neighborhood
// conversations actually happen.
//
// Reality check on what's scrapeable:
//   Nextdoor: Has a public-facing page per neighborhood but login-gates content.
//             No official API. Best approach: Nextdoor's own "Agency" program
//             for governments + nonprofits (free, requires org verification).
//             Short-term: scrape the public neighborhood landing page for basic info.
//   Facebook Groups: Entirely login-gated. Three options:
//             1. Facebook Groups API (requires app review + group admin approval)
//             2. Member manually exports data (Settings > Your Facebook info > Download)
//             3. Browser automation with a logged-in session (fragile, ToS gray area)
//
// This module implements option 1 for both (official API path) + a manual
// import fallback so data can flow even before API access is granted.
//
// IMPORTANT: Social data is signals, not records. It tells us what neighbors
// are TALKING about. It supplements official data; it doesn't replace it.
// We never store individual user profiles from social platforms.

import Database from 'better-sqlite3';
import crypto from 'crypto';
import { readFileSync } from 'fs';

// ----------------------------------------------------------------
// SCHEMA
// ----------------------------------------------------------------

export function ensureSocialTables(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS social_posts (
      id           TEXT PRIMARY KEY,
      source       TEXT NOT NULL,    -- 'nextdoor' | 'facebook' | 'manual'
      platform_id  TEXT,             -- platform's own post ID (if available)
      content      TEXT NOT NULL,    -- post text (sanitized, no PII)
      topic_tags   TEXT,             -- JSON array of extracted topic tags
      sentiment    TEXT,             -- 'positive' | 'negative' | 'neutral' | null
      geo_hint     TEXT,             -- street/intersection mentioned, if any
      posted_at    TEXT,
      ingested_at  TEXT NOT NULL DEFAULT (datetime('now')),
      neighborhood TEXT NOT NULL,    -- which neighborhood node this belongs to

      -- We do NOT store author names, IDs, or profile info
      -- Even if available from the API, we discard it
      UNIQUE(source, platform_id)
    );

    CREATE TABLE IF NOT EXISTS social_topics (
      id              TEXT PRIMARY KEY,
      neighborhood    TEXT NOT NULL,
      tag             TEXT NOT NULL,
      count_7d        INTEGER NOT NULL DEFAULT 0,
      count_30d       INTEGER NOT NULL DEFAULT 0,
      first_seen      TEXT NOT NULL DEFAULT (datetime('now')),
      last_seen       TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE(neighborhood, tag)
    );

    CREATE INDEX IF NOT EXISTS idx_social_posts_source ON social_posts(source);
    CREATE INDEX IF NOT EXISTS idx_social_posts_posted ON social_posts(posted_at);
    CREATE INDEX IF NOT EXISTS idx_social_posts_neighborhood ON social_posts(neighborhood);
    CREATE INDEX IF NOT EXISTS idx_social_topics_neighborhood ON social_topics(neighborhood);
  `);
}

// ----------------------------------------------------------------
// NEXTDOOR
// ----------------------------------------------------------------

// Nextdoor's Agency Portal: https://partners.nextdoor.com/agency
// Free for verified nonprofits and government agencies.
// After approval, they provide API access to public posts in your area.
//
// Until approved, we can pull the public neighborhood profile page.

export async function scrapeNextdoorPublicPage(neighborhoodSlug) {
  // Nextdoor's public neighborhood pages: nextdoor.com/neighborhood/<slug>
  // These show some basic info but most content is login-gated.
  // This is best-effort - we're looking for: member count, recent public activity.
  const url = `https://nextdoor.com/neighborhood/${neighborhoodSlug}--kansas-city--mo/`;
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; NeighborhoodOS/1.0; civic data collector)'
    }
  });

  if (!res.ok) return { error: `HTTP ${res.status}`, url };

  const html = await res.text();

  // Extract what we can from the public page (very limited)
  const memberMatch = html.match(/(\d[\d,]+)\s+(?:members?|neighbors?)/i);
  const members = memberMatch ? parseInt(memberMatch[1].replace(',', '')) : null;

  return {
    slug: neighborhoodSlug,
    url,
    membersApprox: members,
    scrapedAt: new Date().toISOString(),
    note: 'Public page only - most content requires login. Apply at partners.nextdoor.com/agency for full access.'
  };
}

// Process posts received from the Nextdoor Agency API (when available)
// Input: array of post objects from the Nextdoor API
export function ingestNextdoorPosts(db, posts, neighborhood) {
  ensureSocialTables(db);
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO social_posts
      (id, source, platform_id, content, topic_tags, geo_hint, posted_at, neighborhood)
    VALUES (?, 'nextdoor', ?, ?, ?, ?, ?, ?)
  `);

  let inserted = 0;
  const insert = db.transaction((items) => {
    for (const post of items) {
      // Strip author info - we only keep content
      const content = (post.body || post.content || post.text || '').slice(0, 2000);
      if (!content.trim()) continue;

      const tags = extractTopicTags(content);
      const geo = extractGeoHint(content);
      const id = `nextdoor:${post.id || crypto.randomUUID()}`;

      stmt.run(
        id, post.id || null, content,
        JSON.stringify(tags), geo || null,
        post.created_at || post.publishedAt || null,
        neighborhood
      );
      inserted++;
    }
  });

  insert(posts);
  updateTopicCounts(db, neighborhood);
  return { inserted };
}

// ----------------------------------------------------------------
// FACEBOOK GROUPS
// ----------------------------------------------------------------

// Facebook Groups API requires:
// 1. A Facebook App (create at developers.facebook.com)
// 2. The group admin must connect the group to your app
// 3. App review for the "groups_access_member_info" permission
//
// Scopes needed: groups_access_member_info, publish_to_groups (if posting)
// This is the legitimate path. Worth pursuing once NeighborhoodOS has
// one pilot neighborhood as a reference.
//
// Access token goes in env: FB_ACCESS_TOKEN
// Group ID: the numeric ID of the Facebook Group

const FB_GRAPH = 'https://graph.facebook.com/v19.0';

export async function fetchFacebookGroupPosts(groupId, {
  limit = 25,
  since = null,
  accessToken = process.env.FB_ACCESS_TOKEN
} = {}) {
  if (!accessToken) {
    return {
      error: 'No Facebook access token configured.',
      setup: 'See connectors/social.js for setup instructions.',
      fallback: 'Use ingestFacebookExport() with a manually downloaded group export.'
    };
  }

  const params = new URLSearchParams({
    fields: 'message,story,created_time,permalink_url',
    // Note: we deliberately do NOT request: from, reactions, comments
    // We only want the content, not the social graph
    limit,
    access_token: accessToken
  });
  if (since) params.set('since', since);

  const res = await fetch(`${FB_GRAPH}/${groupId}/feed?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`Facebook API error: ${err.error?.message || res.status}`);
  }

  const data = await res.json();
  return data.data || [];
}

export function ingestFacebookPosts(db, posts, neighborhood) {
  ensureSocialTables(db);
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO social_posts
      (id, source, platform_id, content, topic_tags, geo_hint, posted_at, neighborhood)
    VALUES (?, 'facebook', ?, ?, ?, ?, ?, ?)
  `);

  let inserted = 0;
  const insert = db.transaction((items) => {
    for (const post of items) {
      const content = (post.message || post.story || '').slice(0, 2000);
      if (!content.trim()) continue;

      const tags = extractTopicTags(content);
      const geo = extractGeoHint(content);
      const id = `facebook:${post.id || crypto.randomUUID()}`;

      stmt.run(
        id, post.id || null, content,
        JSON.stringify(tags), geo || null,
        post.created_time || null,
        neighborhood
      );
      inserted++;
    }
  });

  insert(posts);
  updateTopicCounts(db, neighborhood);
  return { inserted };
}

// Manual import: accepts a JSON array exported from Facebook's
// "Download Your Information" feature (Settings > Your Facebook Info > Download)
// Format: the posts.json file from the "Groups" section of the export
export function ingestFacebookExport(db, exportPath, neighborhood) {
  const raw = JSON.parse(readFileSync(exportPath, 'utf8'));

  // Facebook export format: { group_posts: [ { data: [{ post: "..." }], timestamp: ... } ] }
  const posts = [];
  const items = raw.group_posts || raw.posts_v2 || raw;

  for (const item of items) {
    const content = item.data?.[0]?.post || item.data?.[0]?.update_timestamp || '';
    if (content) {
      posts.push({
        id: `export-${item.timestamp}`,
        message: content,
        created_time: new Date(item.timestamp * 1000).toISOString()
      });
    }
  }

  return ingestFacebookPosts(db, posts, neighborhood);
}

// ----------------------------------------------------------------
// NLP HELPERS
// Simple keyword extraction - no ML required.
// Replace with local Ollama call for better results once pipeline is stable.
// ----------------------------------------------------------------

const TOPIC_KEYWORDS = {
  traffic: ['traffic', 'speeding', 'speed bump', 'crosswalk', 'stop sign', 'car', 'accident', 'crash'],
  crime: ['crime', 'theft', 'break-in', 'suspicious', 'police', 'kcpd', 'stolen', 'vandal'],
  housing: ['rent', 'eviction', 'landlord', 'affordable', 'housing', 'vacant', 'development', 'rezoning'],
  parks: ['park', 'trail', 'playground', 'tree', 'green space', 'trolley track'],
  infrastructure: ['pothole', 'sidewalk', 'streetlight', 'sewer', 'flooding', 'road', 'construction'],
  noise: ['noise', 'loud', 'music', 'party', 'barking'],
  events: ['event', 'meeting', 'cleanup', 'volunteer', 'block party', 'sale', 'festival'],
  city_hall: ['council', 'mayor', 'city hall', 'ordinance', 'vote', 'zoning', 'permit', 'budget'],
  safety: ['safety', 'dangerous', 'hazard', 'light out', 'loose dog'],
  business: ['business', 'store', 'restaurant', 'opening', 'closing', 'shopping']
};

function extractTopicTags(text) {
  const lower = text.toLowerCase();
  const tags = [];
  for (const [topic, keywords] of Object.entries(TOPIC_KEYWORDS)) {
    if (keywords.some(kw => lower.includes(kw))) {
      tags.push(topic);
    }
  }
  return tags;
}

// Simple street/intersection extractor
// Matches "75th and Wornall", "Ward Pkwy", "W 78th St", etc.
const GEO_PATTERNS = [
  /\b(ward\s+parkway|wornall|holmes|summit|belleview|jefferson|madison|pennsylvania)\b/i,
  /\b(7[5-9]th|8[0-5]th)\s*(st|street|ave|avenue)?\b/i,
  /\bW\s+\d+th\s+(st|street)\b/i,
  /\b\d+th\s+and\s+\w+/i
];

function extractGeoHint(text) {
  for (const pattern of GEO_PATTERNS) {
    const match = text.match(pattern);
    if (match) return match[0].trim();
  }
  return null;
}

// ----------------------------------------------------------------
// TOPIC AGGREGATION
// ----------------------------------------------------------------

function updateTopicCounts(db, neighborhood) {
  // Recount tags from last 7 and 30 days
  const tags7 = db.prepare(`
    SELECT json_each.value as tag, COUNT(*) as cnt
    FROM social_posts, json_each(topic_tags)
    WHERE neighborhood = ? AND posted_at > datetime('now', '-7 days')
    GROUP BY tag
  `).all(neighborhood);

  const tags30 = db.prepare(`
    SELECT json_each.value as tag, COUNT(*) as cnt
    FROM social_posts, json_each(topic_tags)
    WHERE neighborhood = ? AND posted_at > datetime('now', '-30 days')
    GROUP BY tag
  `).all(neighborhood);

  const counts30 = Object.fromEntries(tags30.map(r => [r.tag, r.cnt]));

  const stmt = db.prepare(`
    INSERT INTO social_topics (id, neighborhood, tag, count_7d, count_30d, first_seen, last_seen)
    VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ON CONFLICT(neighborhood, tag) DO UPDATE SET
      count_7d = excluded.count_7d,
      count_30d = excluded.count_30d,
      last_seen = datetime('now')
  `);

  const upsert = db.transaction((items) => {
    for (const { tag, cnt } of items) {
      stmt.run(
        `${neighborhood}:${tag}`, neighborhood, tag,
        cnt, counts30[tag] || cnt
      );
    }
  });

  upsert(tags7);
}

// ----------------------------------------------------------------
// READS
// ----------------------------------------------------------------

export function getTopTopics(db, neighborhood, { days = 30, limit = 10 } = {}) {
  ensureSocialTables(db);
  const field = days <= 7 ? 'count_7d' : 'count_30d';
  return db.prepare(`
    SELECT tag, count_7d, count_30d, last_seen
    FROM social_topics
    WHERE neighborhood = ?
    ORDER BY ${field} DESC
    LIMIT ?
  `).all(neighborhood, limit);
}

export function getRecentPosts(db, neighborhood, { source = null, limit = 50 } = {}) {
  ensureSocialTables(db);
  let query = `SELECT * FROM social_posts WHERE neighborhood = ?`;
  const params = [neighborhood];
  if (source) { query += ` AND source = ?`; params.push(source); }
  query += ` ORDER BY posted_at DESC LIMIT ?`;
  params.push(limit);
  return db.prepare(query).all(...params);
}

export function getSocialSummary(db, neighborhood) {
  ensureSocialTables(db);
  return {
    totalPosts: db.prepare(`SELECT COUNT(*) as cnt FROM social_posts WHERE neighborhood = ?`).get(neighborhood).cnt,
    bySource: db.prepare(`SELECT source, COUNT(*) as cnt FROM social_posts WHERE neighborhood = ? GROUP BY source`).all(neighborhood),
    topTopics: getTopTopics(db, neighborhood, { days: 7, limit: 5 }),
    last7days: db.prepare(`SELECT COUNT(*) as cnt FROM social_posts WHERE neighborhood = ? AND ingested_at > datetime('now', '-7 days')`).get(neighborhood).cnt
  };
}
