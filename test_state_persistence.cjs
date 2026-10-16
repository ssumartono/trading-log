const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('mockup/index.html', 'utf8');
const extract = (start, end) => html.slice(html.indexOf(start), html.indexOf(end, html.indexOf(start)));

function setup() {
  const state = {records: [{id: 1, note: 'first'}, {id: 2, note: 'second'}], funds: [], brokers: [], settings: {}, syncRevision: 0};
  const saved = [], backups = new Map(), alerts = [], statuses = new Map();
  let reads = 0;
  const context = {
    state, ready: true, busy: false, stateDirty: false, stateEditVersion: 0, writes: Promise.resolve(),
    acknowledgedState: structuredClone(state), lastState: JSON.stringify(state),
    snapshot: () => { reads++; return state; },
    saveWithRetry: async payload => saved.push(payload),
    localStorage: {setItem: (key, value) => backups.set(key, value), removeItem: key => backups.delete(key)},
    notify: message => alerts.push(message),
    setAppStatus: (key, message, state, action) => statuses.set(key, {message, state, action}),
    window: {currentUser: {id: 1}},
  };
  vm.createContext(context);
  vm.runInContext(extract('function markStateDirty()', 'const snapshot='), context);
  vm.runInContext(extract('function editPayload(', 'async function saveWithRetry('), context);
  vm.runInContext(extract('function persist()', 'function hydrate('), context);
  return {context, saved, backups, alerts, statuses, reads: () => reads};
}

test('navigation and tab rerenders do not serialize or save trading history', async () => {
  const {context, saved, reads} = setup();
  for (let i = 0; i < 100; i++) context.persist();
  await context.writes;
  assert.equal(reads(), 0);
  assert.equal(saved.length, 0);
});

test('queued edits send only changed rows against the last acknowledged save', async () => {
  const {context, saved, backups} = setup();
  context.state.records[0].note = 'edited first';
  context.markStateDirty(); context.persist();
  context.state.records[1].note = 'edited second';
  context.markStateDirty(); context.persist();
  await context.writes;
  assert.equal(saved.length, 2);
  assert.deepEqual(Array.from(saved[0].records, row => row.id), [1]);
  assert.deepEqual(Array.from(saved[1].records, row => row.id), [2]);
  assert.equal(context.acknowledgedState.records[0].note, 'edited first');
  assert.equal(context.acknowledgedState.records[1].note, 'edited second');
  assert.equal(backups.size, 0);
});

test('failed saves retain the local backup and retry on the next persist', async () => {
  const {context, saved, backups, statuses} = setup();
  context.saveWithRetry = async () => { throw Error('server unavailable'); };
  context.state.records[0].note = 'unsaved edit';
  context.markStateDirty(); context.persist();
  await context.writes;
  assert.equal(context.stateDirty, true);
  assert.equal(backups.size, 1);
  assert.equal(statuses.get('save').state, 'error');
  assert.equal(statuses.get('save').action.label, 'Coba lagi');
  context.saveWithRetry = async payload => saved.push(payload);
  context.persist();
  await context.writes;
  assert.equal(saved.length, 1);
  assert.equal(saved[0].records[0].note, 'unsaved edit');
  assert.equal(backups.size, 0);
});

test('edits made while busy are preserved until saving is allowed', async () => {
  const {context, saved} = setup();
  context.busy = true;
  context.state.records[0].note = 'waiting edit';
  context.markStateDirty(); context.persist();
  assert.equal(context.stateDirty, true);
  context.busy = false; context.persist();
  await context.writes;
  assert.equal(saved[0].records[0].note, 'waiting edit');
});

test('slow MT5 requests allow autosave and do not overwrite local edits on return', async () => {
  const {context, saved} = setup();
  let release, entered, hydrations = 0;
  const blocked = new Promise(resolve => { release = resolve; });
  const waiting = new Promise(resolve => { entered = resolve; });
  const status = {textContent: ''};
  Object.assign(context, {
    terminalBusy: false, page: 'notes', settingsTab: 'profile',
    mt5Settings: {brokerId: '1'},
    $: id => id === 'mt5form' ? {reportValidity: () => true} : status,
    collectIntegration: () => context.markStateDirty(),
    hydrate: () => { hydrations++; },
    api: async path => {
      if (path === '/api/sync') { entered(); await blocked; return {message: 'Synced'}; }
      return structuredClone(context.state);
    },
  });
  vm.runInContext(extract('async function liveAction(', 'async function boot('), context);
  const operation = context.liveAction('/api/sync');
  await waiting;
  assert.equal(context.busy, false);
  context.state.records[0].note = 'edit while syncing';
  context.markStateDirty(); context.persist();
  await context.writes;
  assert.equal(saved.at(-1).records[0].note, 'edit while syncing');
  release(); await operation;
  assert.equal(context.state.records[0].note, 'edit while syncing');
  assert.equal(hydrations, 0);
  assert.equal(context.terminalBusy, false);
});
