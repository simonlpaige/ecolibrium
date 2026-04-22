// neighborhood-os/index.js
// NeighborhoodOS: main entry point.
// Exports the full API surface for programmatic use.
// Wires together: city data, legislative record, social signals,
// civic identity, voting, and Commonweave directory integration.

// Data connectors
export * as kcOpenData from './connectors/kc-open-data.js';
export * as legistar from './connectors/legistar.js';
export * as social from './connectors/social.js';
export * as ecoDirConnector from './connectors/commonweave-directory.js';

// Civic identity + voting (from sibling directory)
export * as identity from '../civic-identity/identity.js';
export * as voting from '../civic-identity/voting.js';
export * as federation from '../civic-identity/federation.js';

// ----------------------------------------------------------------
// Convenience: spin up a full node
// ----------------------------------------------------------------

import { openDB } from '../civic-identity/identity.js';
import { ensureLegistarTables } from './connectors/legistar.js';
import { ensureSocialTables } from './connectors/social.js';
import { ensureFederationTable } from '../civic-identity/federation.js';

export function createNode({
  dbPath = './neighborhood-os.db',
  nodeSlug = 'local@waldonet.local',
  bounds = null
} = {}) {
  // Open a unified DB for this node
  // Civic identity gets its own schema; all other tables co-exist
  const db = openDB(dbPath);
  ensureLegistarTables(db);
  ensureSocialTables(db);
  ensureFederationTable(db);

  return {
    db,
    nodeSlug,
    bounds,

    // Convenience accessors
    async syncCityData(datasetKey) {
      const { syncDataset } = await import('./connectors/kc-open-data.js');
      return syncDataset(db, datasetKey, bounds);
    },

    async syncLegislative(days = 14) {
      const { syncRecentMatters, syncRecentEvents } = await import('./connectors/legistar.js');
      const [matters, events] = await Promise.all([
        syncRecentMatters(db, { days }),
        syncRecentEvents(db, { days })
      ]);
      return { matters, events };
    },

    async getEcosystemRecommendations() {
      const { getEcosystemRecommendations } = await import('./connectors/commonweave-directory.js');
      return getEcosystemRecommendations(db, nodeSlug, bounds);
    },

    close() {
      db.close();
    }
  };
}
