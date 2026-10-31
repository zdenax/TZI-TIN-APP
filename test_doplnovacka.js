// Test ui/novy.html: syntaxe JS, matcher Doplňovačky a varianty v bance, míchání možností u choice otázek.
// Deklarace využití AI: vytvořeno s pomocí nástroje Claude Opus 5.5 (Anthropic, 2026).
// Spuštění:  node test_doplnovacka.js
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, 'ui/novy.html'), 'utf8');
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
new vm.Script(js, {filename: 'ui/novy.html'}); // jen kompilace = kontrola syntaxe

// matcher se vezme přímo z UI (blok od značky po další sekci)
const start = js.indexOf('// ── doplňovačka: porovnání odpovědi ──'), end = js.indexOf('// ── otázka ──');
assert(start > 0 && end > start, 'matcher v novy.html nenalezen');
const ctx = {};
vm.runInNewContext(js.slice(start, end) + '\nthis.matchRecall = matchRecall; this.recallNorm = recallNorm;', ctx);
const {matchRecall, recallNorm} = ctx;

const bank = JSON.parse(fs.readFileSync(path.join(__dirname, 'banky/doplnovacka/04r-doplnovacka.json'), 'utf8')).questions;
const byText = t => { const q = bank.find(q => q.text === t); assert(q, 'chybí otázka: ' + t); return q.accept; };
const OR = byText('Co je to za symbol: ∨ ?'), AND = byText('Co je to za symbol: ∧ ?');
const SYM = byText('Jak se nazývá vlastnost relace: xRy ⇒ yRx?');
const REFL = byText('Jak se nazývá vlastnost relace R na A: ∀x ∈ A; xRx?');
const NEPRIMY = byText('Jak se nazývá důkaz, při kterém místo x ⇒ y dokážeme ¬y ⇒ ¬x?');
const PODIL = byText('Jak se nazývá množina všech tříd ekvivalence množiny A, značená A/∼?');
const SYMETRIE = byText('Podle symetrie kombinačních čísel platí (n nad k) = (n nad ?). Co patří místo otazníku?');
const C52 = byText('Kolik je (5 nad 2)?'), TRIDY = byText('Kolik tříd ekvivalence má relace „stejný zbytek po dělení 3“ na M = {1, …, 8}?');
const ZBYTKY = byText('Převod z desítkové soustavy opakovaným dělením základem: v jakém pořadí se čtou zbytky?');
const NA = byText('Jak se nazývá zobrazení f: M → P, pro které H_f = P (každý prvek P je obrazem)?');
// přednáška 29. 10. (variace, permutace, kombinace s opakováním, binomická věta, konečné automaty)
const VAR = byText('Jak se nazývá uspořádaná k-tice prvků z n-prvkové množiny M, ve které se žádný prvek neopakuje?');
const VAR_O = byText('Jak se nazývá uspořádaná k-tice prvků z n-prvkové množiny M, ve které se prvky mohou opakovat?');
const PERM_O = byText('Jak se nazývá uspořádaná k-tice, ve které je každý prvek a_i základní množiny M = {a_1, …, a_n} přesně k_i-krát (k = k_1 + … + k_n)?');
const CLENY = byText('Kolik sčítanců má rozvoj (a+b)^n podle binomické věty?');
const KOEF3 = byText('Jaké koeficienty má rozvoj (a+b)^3, od a^3 po b^3?');
const DET = byText('Jaký je konečný automat, u kterého má každý stav pro každý vstupní symbol právě jeden přechod?');
const START = byText('Jak se nazývá q₀ v pětici konečného automatu?');
const STROM = byText('Jak se nazývá zápis automatu z přednášky, ve kterém z počátečního stavu (kořene) vedou větve pro každý znak do stavu podle δ a stav, který už se objevil, se dál nerozvíjí?');
const RJ = byText('Jak se na náčrtu konečného automatu z přednášky nazývá část Ř. J., ke které patří množina stavů Q?');

// [odpověď, varianty, očekávání]: 'ok' přesná shoda, 'typo' překlep, null neuznáno
const cases = [
  ['OR', OR, 'ok'], ['or', OR, 'ok'], ['Disjunkce', OR, 'ok'], ['nebo', OR, 'ok'], ['NEBO', OR, 'ok'],
  ['  logické   nebo ', OR, 'ok'], ['logicke nebo', OR, 'ok'], ['Logický součet.', OR, 'ok'], ['„nebo“', OR, 'ok'],
  ['disjunkcí', OR, 'typo'], ['disjunkcee', OR, 'typo'], ['dijsunkce', OR, null],
  ['a', OR, null], ['a zároveň', OR, null], ['konjunkce', OR, null], ['AND', OR, null], ['logický součin', OR, null],
  ['', OR, null], ['   ', OR, null], ['a', AND, 'ok'], ['nebo', AND, null],
  ['symetrická', SYM, 'ok'], ['symetricka', SYM, 'ok'], ['symetrcká', SYM, 'typo'], ['asymetrická', SYM, null],
  ['antisymetrická', SYM, null], ['ireflexivní', REFL, null], ['reflexivni', REFL, 'ok'], ['reflexvní', REFL, 'typo'],
  ['přímý důkaz', NEPRIMY, null], ['nepřímý', NEPRIMY, 'ok'], ['Důkaz obměnou', NEPRIMY, 'ok'],
  ['faktorová množina', PODIL, 'ok'], ['podilova mnozina', PODIL, 'ok'], ['rozklad', PODIL, null],
  ['n-k', SYMETRIE, 'ok'], ['n − k', SYMETRIE, 'ok'], ['n - k', SYMETRIE, 'ok'], ['n+k', SYMETRIE, null], ['k', SYMETRIE, null],
  ['10', C52, 'ok'], ['deset', C52, 'ok'], ['20', C52, null], ['3', TRIDY, 'ok'], ['8', TRIDY, null],
  ['zdola nahoru', ZBYTKY, 'ok'], ['shora dolů', ZBYTKY, null], ['na', NA, 'ok'], ['do', NA, null], ['surjekce', NA, 'ok'],
  ['variace', VAR, 'ok'], ['kombinace', VAR, null], ['permutace', VAR, null], ['variace s opakovanim', VAR_O, 'ok'],
  ['kombinace s opakováním', VAR_O, null], ['permutace s opakováním', PERM_O, 'ok'], ['permutace', PERM_O, null],
  ['n+1', CLENY, 'ok'], ['n + 1', CLENY, 'ok'], ['n', CLENY, null], ['n − 1', CLENY, null],
  ['1, 3, 3, 1', KOEF3, 'ok'], ['1331', KOEF3, 'ok'], ['1 2 1', KOEF3, null],
  ['deterministicky', DET, 'ok'], ['DFA', DET, 'ok'], ['nedeterministický', DET, null],
  ['pocatecni stav', START, 'ok'], ['koncový stav', START, null], ['stavovy strom', STROM, 'ok'], ['stavový diagram', STROM, null],
  ['řídící jednotka', RJ, 'ok'], ['ridici jednotka', RJ, 'ok'],
];
let fail = 0;
for (const [ans, acc, want] of cases) {
  const m = matchRecall(ans, acc), got = m ? (m.typo ? 'typo' : 'ok') : null;
  if (got !== want) { fail++; console.log(`FAIL „${ans}“ vs [${acc[0]}]: čekáno ${want}, je ${got}`); }
}

// každá varianta z banky musí projít přesně, normalizované varianty nesmí být prázdné ani duplicitní
for (const q of bank) {
  const norms = q.accept.map(recallNorm);
  if (norms.some(n => !n) || new Set(norms).size !== norms.length) { fail++; console.log(`FAIL ${q.id}: prázdná/duplicitní varianta po normalizaci`); }
  for (const v of q.accept) { const m = matchRecall(v, q.accept); if (!m || m.typo) { fail++; console.log(`FAIL ${q.id}: „${v}“ neprošla`); } }
}
console.log(`${cases.length} případů matcheru, ${bank.length} otázek v bance`);

// ── míchání možností: skutečné renderQ / klávesy / confirmAnswer z novy.html nad malým falešným DOM ──
class El {
  constructor(id) {
    Object.assign(this, {id, style: {}, children: [], value: '', _h: '', _c: new Set()});
    this.classList = {add: (...c) => c.forEach(x => this._c.add(x)), remove: (...c) => c.forEach(x => this._c.delete(x)), contains: c => this._c.has(c)};
  }
  set innerHTML(v) { this._h = v; if (v === '') this.children = []; } get innerHTML() { return this._h; }
  set textContent(v) { this._h = String(v); } get textContent() { return this._h; }
  set className(v) { this._c = new Set(String(v).split(' ').filter(Boolean)); } get className() { return [...this._c].join(' '); }
  appendChild(c) { this.children.push(c); } addEventListener(t, f) { this['on' + t] = f; }
  setAttribute() {} focus() {}
}
const els = {opts: new El('opts')}, docOn = {};
const page = vm.createContext({
  document: {getElementById: id => id.startsWith('opt-') ? els.opts.children.find(c => c.id === id) || null : (els[id] ||= new El(id)),
    createElement: () => new El(''), addEventListener: (t, f) => { docOn[t] = f; }, querySelectorAll: () => []},
  localStorage: {getItem: () => null, setItem() {}}, fetch: () => new Promise(() => {}), // server se nevolá
  setTimeout, setInterval, clearInterval, alert() {}, confirm: () => false,
});
vm.runInContext(js, page);
const run = code => vm.runInContext(code, page);
const key = k => docOn.keydown({key: k, target: {tagName: 'DIV'}, preventDefault() {}});
const shown = () => els.opts.children.map(c => ({key: c.id.slice(4), letter: /class="letter">(\w)</.exec(c.innerHTML)[1], html: c.innerHTML}));
const choices = fs.readdirSync(path.join(__dirname, 'banky')).filter(f => f.endsWith('.json'))
  .flatMap(f => JSON.parse(fs.readFileSync(path.join(__dirname, 'banky', f), 'utf8')).questions).filter(q => q.type === 'choice');
const Q1 = choices.find(q => q.correct.length === 1 && Object.keys(q.options).length === 4);
const Q2 = choices.find(q => q.correct.length > 1);
page.Q1 = Q1; page.Q2 = Q2;

const N = 400, pos = [0, 0, 0, 0], orders = new Set();
for (let t = 0; t < N; t++) {
  run('beginSession([Q1, Q2], false)');
  const s = shown(), order = s.map(o => o.key).join('');
  assert.deepStrictEqual(s.map(o => o.letter), ['A', 'B', 'C', 'D'], 'písmena A–D podle pozice');
  s.forEach(o => assert(o.html.includes(run('fmt')(Q1.options[o.key])), 'text možnosti patří ke klíči'));
  orders.add(order);
  const c = s.find(o => o.key === Q1.correct[0]); pos[s.indexOf(c)]++;
  if (t % 2) { // špatně: text „Správně: X“ musí ukázat zobrazené písmeno
    key(s.find(o => o !== c).letter.toLowerCase()); key('Enter');
    assert.strictEqual(els.feedback.textContent, `Špatně. Správně: ${c.letter}`);
  } else { key(c.letter.toLowerCase()); key('Enter'); }
  const rec = run('history[0]');
  assert.strictEqual(rec.isCorrect, !(t % 2), 'vyhodnocení');
  assert.deepStrictEqual([...rec.correctKeys], Q1.correct, 'history ukládá původní klíče');
  key('Enter'); // další otázka (Q2, víc správných)
  const s2 = shown();
  Q2.correct.forEach(k => key(s2.find(o => o.key === k).letter)); key('Enter');
  assert.strictEqual(run('history[1]').isCorrect, true, 'víc správných odpovědí');
  run('prevQ()'); // zpět na Q1: pořadí se nesmí změnit
  assert.strictEqual(shown().map(o => o.key).join(''), order, 'pořadí stálé po Předchozí');
}
pos.forEach((n, i) => { if (n < N * 0.15 || n > N * 0.35) { fail++; console.log(`FAIL pozice ${'ABCD'[i]}: ${n}× z ${N}`); } });
console.log(`míchání: ${N} sad, správná odpověď na pozici A/B/C/D: ${pos.join('/')}, různých pořadí: ${orders.size}/24`);
// zlomky a kombinační čísla ve fmt (texty z bank); [ ÷ ] = zlomek, { nad } = kombinační číslo
const fm = s => run('fmt')(s).replace(/<span class="frac"><span>(.*?)<\/span><span>(.*?)<\/span><\/span>/g, '[$1 ÷ $2]')
  .replace(/<span class="binom"><span><span>(.*?)<\/span><span>(.*?)<\/span><\/span><\/span>/g, '{$1 nad $2}');
[['(n nad 0) = n! / (n! · 0!) = 1.', '{n nad 0} = [n! ÷ n! · 0!] = 1.'],
 ['(5 nad 2) = 5 · 4 / 2! = 20 / 2 = 10.', '{5 nad 2} = [5 · 4 ÷ 2!] = [20 ÷ 2] = 10.'],
 ['n·(n−1)·…·(n−k+1)/k!.', '[n·(n−1)·…·(n−k+1) ÷ k!].'], ['1 + 2 + ... + n = n(n + 1)/2 pro', '1 + 2 + … + n = [n(n + 1) ÷ 2] pro'],
 ['(n+1 nad k+1)', '{n+1 nad k+1}'], ['např. 1/2, −3/4, 5', 'např. [1 ÷ 2], −[3 ÷ 4], 5'], ['(= 6!/3!).', '(= [6! ÷ 3!]).'],
 ['pravda (1) / nepravda (0)', 'pravda (1) / nepravda (0)'], ['množina A/∼?', 'množina A/∼?'], ['(M/E)', '(M/E)'],
 ['pro každé / pro všechna', 'pro každé / pro všechna'], ['a <b> / 2', 'a &lt;b&gt; / 2'],
 // značení z přednášky 29. 10. (banky 05, 05a)
 ['V′_k(n) = n! / (n−k)!', 'V′<sub>k</sub>(n) = [n! ÷ (n−k)!]'],
 ['C′_2(3) = (3+2−1 nad 2) = (4 nad 2) = 6', 'C′<sub>2</sub>(3) = {3+2−1 nad 2} = {4 nad 2} = 6'],
 ['P′_(1,1,2)(4) = 4! / (1! · 1! · 2!) = 24 / 2 = 12', 'P′<sub>1,1,2</sub>(4) = [4! ÷ 1! · 1! · 2!] = [24 ÷ 2] = 12'],
 ['(a+b)^n = Σ (n nad k) · a^(n−k) · b^k', '(a+b)<sup>n</sup> = Σ {n nad k} · a<sup>n−k</sup> · b<sup>k</sup>'],
 ['δ(q₀, 1) = q₂, q₀ –0→ q₀', 'δ(q<sub>0</sub>, 1) = q<sub>2</sub>, q<sub>0</sub> –0→ q<sub>0</sub>'],
].forEach(([s, want]) => { const got = fm(s); if (got !== want) { fail++; console.log(`FAIL fmt: ${s}\n  dostal: ${got}\n  čekal:  ${want}`); } });
console.log(`chyb: ${fail}`);
process.exit(fail ? 1 : 0);
