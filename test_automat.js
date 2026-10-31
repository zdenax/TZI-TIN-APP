// Test logiky návrháře automatů: node test_automat.js
const assert = require('node:assert/strict');
const Auto = require('./ui/automat-core.js');

const words = (alpha, max) => { let out = [''], cur = ['']; for (let i = 0; i < max; i++) { cur = cur.flatMap(w => alpha.map(a => w + a)); out = out.concat(cur); } return out; };
const asModel = ref => ({ alphabet: ['0', '1'], states: ref.states, start: ref.start, accept: ref.accept, trans: ref.trans });

// 1. referenční automat každé úlohy odpovídá nezávislému predikátu na všech slovech do délky 12
for (const t of Auto.TASKS) {
  const m = asModel(t.ref);
  assert.ok(Auto.check(m).ok, `${t.id}: referenční automat musí být úplný a deterministický`);
  for (const w of words(t.alphabet, 12)) assert.equal(Auto.run(m, w).accepted, t.pred(w), `${t.id}: slovo "${w}"`);
  assert.deepEqual(Auto.grade(m, t), { ok: true }, `${t.id}: sám sebe musí přijmout`);
}

// 2. automat z přednášky: slovo 1011010 projde q0 q2 q1 q3 q3 q1 q3 q1 a skončí přijatě
const lecture = asModel(Auto.TASKS.find(t => t.id === 'prednaska').ref);
const r = Auto.run(lecture, '1011010');
assert.deepEqual([lecture.start, ...r.steps.map(s => s.to)], ['q0', 'q2', 'q1', 'q3', 'q3', 'q1', 'q3', 'q1']);
assert.ok(r.accepted);

// 3. stavový strom automatu z přednášky: 9 uzlů, 5 listů, které se dál nerozvíjejí
const tree = Auto.tree(lecture);
const flat = n => [n, ...n.children.flatMap(flat)];
assert.equal(flat(tree).length, 9);
assert.equal(flat(tree).filter(n => n.seen).length, 5);

// 4. špatný návrh dostane nejkratší protipříklad
const wrong = { alphabet: ['0', '1'], start: 'a', accept: ['a'], states: [{ id: 'a' }], trans: [{ from: 'a', to: 'a', symbols: ['0', '1'] }] };
const g = Auto.grade(wrong, Auto.TASKS.find(t => t.id === 'konci0'));
assert.equal(g.ok, false); assert.equal(g.kind, 'wrong'); assert.equal(g.word, ''); // prázdné slovo nekončí nulou, ale návrh ho přijímá
assert.equal(g.mine, true); assert.equal(g.expected, false);

// 5. chybějící a nedeterministické přechody se najdou, grade se na ně ptá dřív než na jazyk
const bad = { alphabet: ['0', '1'], start: 'a', accept: [], states: [{ id: 'a' }, { id: 'b' }], trans: [{ from: 'a', to: 'a', symbols: ['0'] }, { from: 'a', to: 'b', symbols: ['0'] }] };
const c = Auto.check(bad);
assert.equal(c.ok, false); assert.equal(c.multi.length, 1); assert.equal(c.missing.length, 3);
assert.equal(Auto.grade(bad, Auto.TASKS[0]).kind, 'invalid');
assert.equal(Auto.run(bad, '0').stuck, 'δ(a, 0) vede do více stavů.');
assert.equal(Auto.check({ alphabet: ['0'], states: [], start: null, accept: [], trans: [] }).ok, false);

// 6. jiná abeceda než v úloze
assert.equal(Auto.grade({ ...lecture, alphabet: ['a', 'b'] }, Auto.TASKS[0]).kind, 'invalid');

console.log('automat test OK');
