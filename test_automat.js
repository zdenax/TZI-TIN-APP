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

// 7. úloha „čtyři reprezentace“: δ, tabulka, strom po úrovních
const rep = Auto.TASKS.find(t => t.id === 'repr'), al = ['0', '1'];
const good = { q0: { 0: 'q0', 1: 'q2' }, q1: { 0: 'q1', 1: 'q3' }, q2: { 0: 'q1', 1: 'q3' }, q3: { 0: 'q1', 1: 'q3' } };
assert.deepEqual(Auto.gradeDelta(good, rep.ref, al), []);
assert.deepEqual(Auto.gradeDelta({ ...good, q2: { 0: 'Q₁', 1: ' q3 ' } }, rep.ref, al), []); // velikost písmen, dolní index, mezery
assert.deepEqual(Auto.gradeDelta({ ...good, q1: { 0: 'q1', 1: 'q2' } }, rep.ref, al), [{ q: 'q1', a: '1' }]);
assert.equal(Auto.gradeDelta({}, rep.ref, al).length, 8);
const marks = { q0: { start: true }, q1: { accept: true }, q2: { accept: true } };
assert.ok(Auto.gradeTable(good, marks, rep.ref, al).ok);
assert.deepEqual(Auto.gradeTable(good, { ...marks, q3: { accept: true } }, rep.ref, al).badMarks, ['q3']);
const lv = Auto.treeLevels(asModel(rep.ref));
assert.deepEqual(lv, [['q0'], ['q0', 'q2'], ['q1', 'q3'], ['q1', 'q3', 'q1', 'q3']]);
assert.ok(Auto.gradeLevels(['q0', 'q0 q2', 'q1, q3', 'q1 q3 q1 q3'], asModel(rep.ref)).ok);
assert.deepEqual(Auto.gradeLevels(['q0', 'q2 q0', 'q1 q3', ''], asModel(rep.ref)).wrong, [1, 3]);

// 8. čtení slova: trénink má přijatá i nepřijatá slova, kontrola pozná chybný stav i chybný verdikt
const rm = asModel(rep.ref), acc = rep.words.map(w => Auto.run(rm, w).accepted);
assert.ok(acc.includes(true) && acc.includes(false));
assert.equal(rep.words[0], '1011010'); assert.ok(acc[0]);
assert.ok(Auto.gradeRun(['q2', 'q1', 'q3', 'q3', 'q1', 'q3', 'q1'], true, rm, '1011010').ok);
assert.ok(Auto.gradeRun(['Q₂', 'q1', 'q3', 'q3', 'q1', 'q3', 'q1'], true, rm, '1011010').ok);
const bad1 = Auto.gradeRun(['q2', 'q1', 'q3', 'q1', 'q1', 'q3', 'q1'], true, rm, '1011010');
assert.deepEqual(bad1.wrong, [3]); assert.equal(bad1.ok, false);
const bad2 = Auto.gradeRun(['q2', 'q1', 'q3', 'q3', 'q1', 'q3', 'q1'], false, rm, '1011010');
assert.equal(bad2.ok, false); assert.equal(bad2.verdictOk, false); assert.deepEqual(bad2.wrong, []);
assert.equal(Auto.gradeRun(['q2'], null, rm, '1011010').ok, false);

console.log('automat test OK');
