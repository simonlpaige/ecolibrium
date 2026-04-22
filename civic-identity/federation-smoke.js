// civic-identity/federation-smoke.js
// Smoke test for federation: build a bundle on node A, receive it on node
// B, then try to replay it and confirm rejection.

import crypto from 'crypto';
import { existsSync, unlinkSync } from 'fs';
import { openDB, registerAnonymous } from './identity.js';
import { addPeer, activatePeer, buildShareBundle, receiveBundle,
         ensureFederationTable } from './federation.js';

const PATH_A = './fed-a.db';
const PATH_B = './fed-b.db';
for (const p of [PATH_A, PATH_B, PATH_A + '-wal', PATH_A + '-shm', PATH_B + '-wal', PATH_B + '-shm']) {
  if (existsSync(p)) unlinkSync(p);
}

let passed = 0, failed = 0;
function check(name, fn) {
  try { fn(); console.log(`  ✓ ${name}`); passed++; }
  catch (e) { console.log(`  ✗ ${name}: ${e.message}`); failed++; }
}

console.log('\nFederation smoke test\n');

const dbA = openDB(PATH_A);
const dbB = openDB(PATH_B);
ensureFederationTable(dbA);
ensureFederationTable(dbB);

// Give A a keypair
const { publicKey: aPub, privateKey: aPriv } = crypto.generateKeyPairSync('ed25519');
const aPubPem = aPub.export({ type: 'spki', format: 'pem' });
const aPrivPem = aPriv.export({ type: 'pkcs8', format: 'pem' });

// B registers A as a peer and activates
addPeer(dbB, {
  peerNode: 'nodeA@test',
  peerName: 'Node A',
  peerPubkey: aPubPem,
  shareScope: ['aggregated_votes', 'user_count']
});
activatePeer(dbB, 'nodeA@test');

// A also needs B as an active peer to build a bundle targeted at B
// (buildShareBundle queries federation_peers on the sending side).
addPeer(dbA, {
  peerNode: 'nodeB@test',
  peerName: 'Node B',
  peerPubkey: 'dummy', // A doesn't verify B's bundles in this test
  shareScope: ['aggregated_votes', 'user_count']
});
activatePeer(dbA, 'nodeB@test');

registerAnonymous(dbA, 'alicea', 'nodeA@test');

let bundle;
check('build bundle on A', () => {
  bundle = buildShareBundle(dbA, 'nodeA@test', aPrivPem, 'nodeB@test');
  if (!bundle.signature) throw new Error('no signature');
  if (!bundle.data) throw new Error('no data');
});

check('receive bundle on B', () => {
  const r = receiveBundle(dbB, bundle);
  if (!r.accepted) throw new Error('not accepted');
});

check('replay of same bundle blocked', () => {
  try { receiveBundle(dbB, bundle); throw new Error('should have blocked'); }
  catch (e) { if (!/already received|replay/i.test(e.message)) throw e; }
});

check('tampered bundle rejected', () => {
  const tampered = { ...bundle, data: { ...bundle.data, tampered: true } };
  try { receiveBundle(dbB, tampered); throw new Error('should have rejected'); }
  catch (e) { if (!/signature/i.test(e.message)) throw e; }
});

check('stale bundle rejected', () => {
  // Reach back past the staleness window
  const stale = {
    ...bundle,
    generatedAt: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString()
  };
  // Re-sign for a valid envelope but old timestamp
  const payload = JSON.stringify({
    sourceNode: stale.sourceNode,
    targetNode: stale.targetNode,
    generatedAt: stale.generatedAt,
    data: stale.data
  });
  stale.signature = crypto.sign(null, Buffer.from(payload), aPrivPem).toString('base64');
  try { receiveBundle(dbB, stale); throw new Error('should have rejected'); }
  catch (e) { if (!/outside accepted window|stale/i.test(e.message)) throw e; }
});

dbA.close();
dbB.close();

console.log(`\n${passed} passed, ${failed} failed\n`);
for (const p of [PATH_A, PATH_B, PATH_A + '-wal', PATH_A + '-shm', PATH_B + '-wal', PATH_B + '-shm']) {
  if (existsSync(p)) unlinkSync(p);
}
process.exit(failed > 0 ? 1 : 0);
