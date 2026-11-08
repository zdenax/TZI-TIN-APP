// Logika návrháře automatů (bez DOM, jde testovat v node: test_automat.js).
// Model: { alphabet: ['0','1'], states: [{id, x, y}], start: id|null, accept: [id], trans: [{from, to, symbols: ['0']}] }
(function (root) {
  const Auto = {};

  // stav -> znak -> [cíle]
  Auto.delta = function (m) {
    const d = {};
    for (const s of m.states) d[s.id] = {};
    for (const t of m.trans) {
      if (!d[t.from]) continue;
      for (const a of t.symbols) {
        const cell = (d[t.from][a] = d[t.from][a] || []);
        if (!cell.includes(t.to)) cell.push(t.to);
      }
    }
    return d;
  };

  // Co brání tomu, aby to byl deterministický úplný automat.
  Auto.check = function (m) {
    const d = Auto.delta(m), problems = [];
    if (!m.states.length) problems.push({ kind: 'empty', text: 'Automat nemá žádný stav.' });
    else if (!m.start) problems.push({ kind: 'start', text: 'Není určený počáteční stav.' });
    const missing = [], multi = [], foreign = [];
    for (const s of m.states) {
      for (const a of m.alphabet) {
        const c = d[s.id][a] || [];
        if (!c.length) missing.push({ q: s.id, a });
        else if (c.length > 1) multi.push({ q: s.id, a, to: c });
      }
      for (const a of Object.keys(d[s.id])) if (!m.alphabet.includes(a)) foreign.push({ q: s.id, a });
    }
    if (missing.length) problems.push({ kind: 'missing', text: `Chybí ${missing.length} ${missing.length === 1 ? 'přechod' : missing.length < 5 ? 'přechody' : 'přechodů'}: ` + missing.map(x => `δ(${x.q}, ${x.a})`).join(', ') + '.' });
    if (multi.length) problems.push({ kind: 'multi', text: 'Není deterministický: ' + multi.map(x => `δ(${x.q}, ${x.a}) vede do ${x.to.join(' i ')}`).join('; ') + '.' });
    if (foreign.length) problems.push({ kind: 'foreign', text: 'Znak mimo abecedu: ' + foreign.map(x => `${x.q} (${x.a})`).join(', ') + '.' });
    return { ok: !problems.length, problems, missing, multi, foreign };
  };

  // Přečte slovo: kroky [{from, read, to}], nebo zaseknutí (chybí přechod / znak mimo abecedu).
  Auto.run = function (m, word) {
    const d = Auto.delta(m);
    let q = m.start;
    const steps = [];
    if (!q) return { steps, stuck: 'Není počáteční stav.', state: null, accepted: false };
    for (const a of word) {
      const c = (d[q] || {})[a] || [];
      if (c.length !== 1) return { steps, stuck: c.length ? `δ(${q}, ${a}) vede do více stavů.` : `Chybí přechod δ(${q}, ${a}).`, state: q, accepted: false };
      steps.push({ from: q, read: a, to: c[0] });
      q = c[0];
    }
    return { steps, stuck: null, state: q, accepted: m.accept.includes(q) };
  };

  // Stavový strom podle přednášky (Vais, kap. 1.3): od počátečního stavu shora dolů, z každého uzlu hrana pro každý znak;
  // stav, který už je ve stromu rozvinutý, se dál nerozvíjí. Rozvíjí se po úrovních, zleva doprava.
  Auto.tree = function (m) {
    const d = Auto.delta(m);
    if (!m.start) return null;
    const root = { state: m.start, children: [], seen: false };
    const queue = [root], expanded = new Set();
    let count = 0;
    while (queue.length && count < 500) {
      const n = queue.shift();
      count++;
      if (expanded.has(n.state)) { n.seen = true; continue; }
      expanded.add(n.state);
      for (const a of m.alphabet) {
        for (const to of (d[n.state] || {})[a] || []) {
          const c = { sym: a, state: to, children: [], seen: false };
          n.children.push(c);
          queue.push(c);
        }
      }
    }
    return root;
  };

  // Ekvivalence dvou úplných deterministických automatů (průnik stavů do dvojic, BFS):
  // nejkratší slovo, na kterém se liší, nebo { equal: true }. Přesné pro všechna slova, ne jen do nějaké délky.
  Auto.equivalent = function (m1, m2, alphabet) {
    const d1 = Auto.delta(m1), d2 = Auto.delta(m2);
    const key = (p, q) => p + '\u0000' + q;
    const seen = new Set([key(m1.start, m2.start)]);
    const queue = [{ p: m1.start, q: m2.start, word: '' }];
    while (queue.length) {
      const { p, q, word } = queue.shift();
      const a1 = m1.accept.includes(p), a2 = m2.accept.includes(q);
      if (a1 !== a2) return { equal: false, word, mine: a1, expected: a2 };
      for (const a of alphabet) {
        const np = d1[p][a][0], nq = d2[q][a][0];
        if (!seen.has(key(np, nq))) { seen.add(key(np, nq)); queue.push({ p: np, q: nq, word: word + a }); }
      }
    }
    return { equal: true };
  };

  // Stavy zapsané textem ("q0, q2", "q₀ q₂") -> ['q0','q2']; podle tabulky se piš i dolní indexy.
  Auto.parseStates = function (text) {
    return String(text).replace(/[₀-₉]/g, c => String(c.charCodeAt(0) - 0x2080)).split(/[\s,;→]+/).filter(Boolean).map(x => x.toLowerCase());
  };

  // Přechodová funkce zapsaná jako { q: { a: 'q1' } } proti referenčnímu automatu: seznam chybných buněk.
  Auto.gradeDelta = function (cells, ref, alphabet) {
    const d = Auto.delta(ref), wrong = [];
    for (const s of ref.states) for (const a of alphabet) {
      const got = Auto.parseStates((cells[s.id] || {})[a] || '');
      if (got.length !== 1 || got[0] !== d[s.id][a][0]) wrong.push({ q: s.id, a });
    }
    return wrong;
  };

  // Tabulka: buňky jako δ, k tomu značky počátečního (→) a přijímacích (←) stavů.
  Auto.gradeTable = function (cells, marks, ref, alphabet) {
    const wrong = Auto.gradeDelta(cells, ref, alphabet), badMarks = [];
    for (const s of ref.states) {
      const m = marks[s.id] || {};
      if (!!m.start !== (ref.start === s.id) || !!m.accept !== ref.accept.includes(s.id)) badMarks.push(s.id);
    }
    return { ok: !wrong.length && !badMarks.length, wrong, badMarks };
  };

  // Strom po úrovních: stavy zleva doprava (úroveň 0 je kořen).
  Auto.treeLevels = function (m) {
    const t = Auto.tree(m), levels = [];
    if (!t) return levels;
    let cur = [t];
    while (cur.length) { levels.push(cur.map(n => n.state)); cur = cur.flatMap(n => n.children); }
    return levels;
  };

  // Úrovně stromu zadané uživatelem (pole textů) proti automatu: indexy chybných úrovní.
  Auto.gradeLevels = function (inputs, m) {
    const exp = Auto.treeLevels(m), wrong = [];
    exp.forEach((lv, i) => { if (Auto.parseStates(inputs[i] || '').join(' ') !== lv.join(' ')) wrong.push(i); });
    return { ok: !wrong.length, wrong, count: exp.length };
  };

  // Čtení slova: stavy po jednotlivých znacích (pole textů) a verdikt (true = přijato) proti tomu, co automat doopravdy udělá.
  Auto.gradeRun = function (states, verdict, m, word) {
    const r = Auto.run(m, word), wrong = [];
    for (let i = 0; i < word.length; i++) {
      const got = Auto.parseStates((states || [])[i] || '');
      if (got.length !== 1 || !r.steps[i] || got[0] !== r.steps[i].to) wrong.push(i);
    }
    return { ok: !wrong.length && verdict === r.accepted, wrong, verdictOk: verdict === r.accepted, accepted: r.accepted };
  };

  // Rozložení stavového stromu: list = další pozice zleva, rodič je nad středem svých dětí; y = hloubka.
  Auto.treeLayout = function (root) {
    const nodes = []; let leaf = 0, depth = 0;
    (function walk(n, y, parent) {
      const o = { n, y, parent, x: 0 }; nodes.push(o); depth = Math.max(depth, y);
      if (!n.children.length) { o.x = leaf++; return o; }
      const kids = n.children.map(c => walk(c, y + 1, o));
      o.x = (kids[0].x + kids[kids.length - 1].x) / 2;
      return o;
    })(root, 0, null);
    return { nodes, leaves: leaf, depth };
  };

  // Zadání automatu textem (δ(q0, 0) = q1 …, Σ = {…}, počáteční stav, F = {…}) -> automat; problems = co ještě chybí.
  Auto.parseSpec = function (text) {
    const src = String(text).replace(/[₀-₉]/g, c => String(c.charCodeAt(0) - 0x2080));
    const id = "[A-Za-z_][A-Za-z0-9_′']*", problems = [], trans = [], low = s => s.toLowerCase();
    const list = s => s.split(/[,\s;]+/).filter(Boolean);
    const ids = s => list(s).filter(x => new RegExp('^' + id + '$').test(x)).map(low);
    const add = (f, a, t) => trans.push({ from: low(f), to: low(t), symbols: [a] });
    let m;
    const re = new RegExp(`(?:δ|delta)?\\s*\\(\\s*(${id})\\s*[,;]\\s*([^\\s,;()])\\s*\\)\\s*(?:=|->|→)\\s*(${id})`, 'gi');
    while ((m = re.exec(src))) add(m[1], m[2], m[3]);
    if (!trans.length) {
      const re2 = new RegExp(`^\\s*(${id})[\\s,]+([^\\s,])[\\s,]*(?:->|→|=)?\\s*(${id})\\s*$`, 'gmi');
      while ((m = re2.exec(src))) add(m[1], m[2], m[3]);
    }
    if (!trans.length) problems.push('Nenašel jsem žádný přechod. Piš je jako δ(q0, 0) = q1, každý na jeden řádek.');
    const sigma = (src.match(/[Σ∑]\s*=\s*\{([^}]*)\}/) || src.match(/abeceda[^\n:=]*[:=]\s*\{?([^}\n]*)\}?/i) || [])[1];
    const qset = (src.match(/(?:^|[^A-Za-z])Q\s*=\s*\{([^}]*)\}/) || [])[1];
    const fset = (src.match(/(?:^|[^A-Za-z])F\s*=\s*\{([^}]*)\}/) || src.match(/(?:koncov|p[řr]ij[ií]mac)\w*[^\n:=]*[:=]\s*\{?([^}\n]*)\}?/i) || [])[1];
    const sm = src.match(new RegExp(`po[cč](?:[aá]te[cč]n\\S*|\\.)(?:\\s+stav\\w*)?(?:\\s+je)?\\s*[:=]?\\s*(${id})`, 'i')) || src.match(new RegExp(`\\bstart\\w*\\s*[:=]?\\s*(${id})`, 'i'));
    const alphabet = sigma ? list(sigma) : [...new Set(trans.flatMap(t => t.symbols))].sort();
    if (alphabet.some(a => [...a].length !== 1)) problems.push('Znaky abecedy musí být jednopísmenné.');
    const accept = fset !== undefined ? ids(fset) : [];
    const start = sm ? low(sm[1]) : (trans[0] && trans[0].from) || null;
    if (!sm && trans.length) problems.push(`Počáteční stav jsem nenašel, beru ${start}. Napiš např. „počáteční stav q0“.`);
    const stateIds = [...new Set([...(qset ? ids(qset) : []), ...trans.flatMap(t => [t.from, t.to]), ...(start ? [start] : []), ...accept])];
    const d = {};
    for (const t of trans) {
      const a = t.symbols[0];
      if (!alphabet.includes(a)) { problems.push(`Znak ${a} není v abecedě {${alphabet.join(', ')}}.`); continue; }
      const k = t.from + '|' + a;
      if (d[k] && d[k] !== t.to) problems.push(`δ(${t.from}, ${a}) je zadáno dvakrát různě (${d[k]} a ${t.to}).`);
      d[k] = t.to;
    }
    const missing = [];
    for (const q of stateIds) for (const a of alphabet) if (!d[q + '|' + a]) missing.push(`δ(${q}, ${a})`);
    if (trans.length && missing.length) problems.push('Chybí přechody: ' + missing.join(', ') + '.');
    if (fset === undefined && trans.length) problems.push('Nenašel jsem přijímací stavy. Napiš např. F = {q1}.');
    const uniq = []; // znaky jedné hrany do jednoho záznamu
    for (const t of trans) { const e = uniq.find(u => u.from === t.from && u.to === t.to); if (e) e.symbols.push(...t.symbols); else uniq.push({ ...t, symbols: [...t.symbols] }); }
    return { ok: !problems.length && stateIds.length > 0, problems, alphabet, start, accept, states: stateIds.map(i => ({ id: i })), trans: uniq };
  };

  // Přejmenuje stavy na q0, q1, … podle pořadí objevení od počátečního stavu (prohledávání do šířky).
  Auto.normalize = function (ref, alphabet) {
    const d = Auto.delta(ref), order = [ref.start], map = {};
    for (let i = 0; i < order.length; i++) for (const a of alphabet) for (const t of (d[order[i]] || {})[a] || []) if (!order.includes(t)) order.push(t);
    for (const s of ref.states) if (!order.includes(s.id)) order.push(s.id);
    order.forEach((s, i) => { map[s] = 'q' + i; });
    return {
      start: map[ref.start], accept: ref.accept.map(x => map[x]), states: order.map(s => ({ id: map[s] })),
      trans: ref.trans.map(t => ({ ...t, from: map[t.from], to: map[t.to] })),
    };
  };

  // Zadání automatu jako text: Q, Σ, počáteční stav, F a všechna δ.
  Auto.specText = function (ref, alphabet) {
    const d = Auto.delta(ref);
    return `Q = {${ref.states.map(s => s.id).join(', ')}}\nΣ = {${alphabet.join(', ')}}\npočáteční stav ${ref.start}\nF = {${ref.accept.join(', ')}}\n` +
      ref.states.flatMap(s => alphabet.map(a => `δ(${s.id}, ${a}) = ${d[s.id][a][0]}`)).join('\n');
  };

  // Slova k tréninku čtení: čtyři přijatá a čtyři nepřijatá délky 3 až 7, výběr stálý podle seed.
  Auto.pickWords = function (ref, alphabet, seed) {
    const acc = [], rej = [];
    let level = [''];
    for (let len = 1; len <= 7 && level.length * alphabet.length <= 4000; len++) {
      level = level.flatMap(w => alphabet.map(a => w + a));
      if (len >= 3) for (const w of level) (Auto.run(ref, w).accepted ? acc : rej).push(w);
    }
    let x = [...String(seed)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
    const rnd = () => (x = (x * 1664525 + 1013904223) >>> 0) / 4294967296;
    const take = (arr, n) => { const a = arr.slice(), out = []; while (a.length && out.length < n) out.push(a.splice(Math.floor(rnd() * a.length), 1)[0]); return out; };
    const A = take(acc, 4), R = take(rej, 4), out = [];
    for (let i = 0; i < 4; i++) { if (R[i]) out.push(R[i]); if (A[i]) out.push(A[i]); }
    return out.length ? out : [alphabet[0]];
  };

  // Úloha „zadaný automat“ (δ, tabulka, diagram, strom, čtení slova): o.ref + o.alphabet; o.normalize přejmenuje stavy na q0, q1, …
  Auto.makeGiven = function (o) {
    const ref = o.normalize ? Auto.normalize(o.ref, o.alphabet) : o.ref;
    return { id: o.id, title: o.title, steps: true, custom: !!o.custom, alphabet: o.alphabet, ref, image: o.image || null, lang: o.lang || '',
      text: o.text || Auto.specText(ref, o.alphabet), pred: o.pred, words: o.words || Auto.pickWords(ref, o.alphabet, o.id) };
  };

  const dfa = (start, accept, rows) => ({
    start, accept,
    states: Object.keys(rows).map(id => ({ id })),
    trans: Object.entries(rows).flatMap(([from, r]) => Object.entries(r).map(([a, to]) => ({ from, to, symbols: [a] }))),
  });

  // Úlohy: zadání, abeceda, referenční automat a nezávislý predikát (test_automat.js je porovná na všech slovech do délky 12).
  Auto.TASKS = [
    { id: 'konci0', lang: 'slova končící nulou', title: 'Slova končící nulou', alphabet: ['0', '1'], pred: w => w.endsWith('0'),
      text: 'Navrhni automat nad abecedou {0, 1}, který přijímá právě slova končící znakem 0.',
      ref: dfa('a', ['b'], { a: { 0: 'b', 1: 'a' }, b: { 0: 'b', 1: 'a' } }) },
    { id: 'aspon1', lang: 'slova s aspoň jednou jedničkou', title: 'Obsahuje aspoň jednu 1', alphabet: ['0', '1'], pred: w => w.includes('1'),
      text: 'Přijímej právě slova, ve kterých je aspoň jedna jednička.',
      ref: dfa('a', ['b'], { a: { 0: 'a', 1: 'b' }, b: { 0: 'b', 1: 'b' } }) },
    { id: 'sude1', lang: 'slova se sudým počtem jedniček', title: 'Sudý počet jedniček', alphabet: ['0', '1'], pred: w => [...w].filter(c => c === '1').length % 2 === 0,
      text: 'Přijímej právě slova se sudým počtem jedniček (nula jedniček je sudý počet).',
      ref: dfa('e', ['e'], { e: { 0: 'e', 1: 'o' }, o: { 0: 'o', 1: 'e' } }) },
    { id: 'bez11', lang: 'slova bez dvou jedniček za sebou (q_x je past)', title: 'Neobsahuje 11', alphabet: ['0', '1'], pred: w => !w.includes('11'),
      text: 'Přijímej právě slova, ve kterých nejdou dvě jedničky hned za sebou. Tip: potřebuješ stav „právě jsem přečetl 1" a past, ze které se nedá vrátit.',
      ref: dfa('a', ['a', 'b'], { a: { 0: 'a', 1: 'b' }, b: { 0: 'a', 1: 'x' }, x: { 0: 'x', 1: 'x' } }) },
    { id: 'konci01', lang: 'slova končící na 01', title: 'Končí na 01', alphabet: ['0', '1'], pred: w => w.endsWith('01'),
      text: 'Přijímej právě slova, která končí dvojicí znaků 01.',
      ref: dfa('a', ['c'], { a: { 0: 'b', 1: 'a' }, b: { 0: 'b', 1: 'c' }, c: { 0: 'b', 1: 'a' } }) },
    { id: 'delka3', lang: 'slova s délkou dělitelnou třemi', title: 'Délka dělitelná třemi', alphabet: ['0', '1'], pred: w => w.length % 3 === 0,
      text: 'Přijímej právě slova, jejichž délka je dělitelná třemi (včetně prázdného slova). Znaky samotné nehrají roli.',
      ref: dfa('r0', ['r0'], { r0: { 0: 'r1', 1: 'r1' }, r1: { 0: 'r2', 1: 'r2' }, r2: { 0: 'r0', 1: 'r0' } }) },
    { id: 'dvere', lang: 'slova končící 1 (dveře)', title: 'Dveře (otevřeno / zavřeno)', alphabet: ['0', '1'], pred: w => w.endsWith('1'),
      text: 'Automat řídí vstupní dveře. Vstup 0 znamená, že před dveřmi nikdo není, vstup 1 znamená, že před nimi někdo stojí. Dveře jsou na začátku zavřené, otevřené dveře jsou přijímací stav. Navrhni automat (2 stavy).',
      ref: dfa('q0', ['q1'], { q0: { 0: 'q0', 1: 'q1' }, q1: { 0: 'q0', 1: 'q1' } }) },
    { id: 'prednaska', lang: 'automat z přednášky: aspoň jedna 1 a končí 0, nebo tvar 0…01', title: 'Automat z přednášky', alphabet: ['0', '1'], pred: w => /^0*1$/.test(w) || (w.endsWith('0') && w.includes('1')),
      text: 'Překresli automat z přednášky podle tabulky: q₀ je počáteční, přijímací jsou q₁ a q₂.  δ: q₀ → (0: q₀, 1: q₂), q₁ → (0: q₁, 1: q₃), q₂ → (0: q₁, 1: q₃), q₃ → (0: q₁, 1: q₃). Stavy pojmenuj q0, q1, q2, q3.',
      ref: dfa('q0', ['q1', 'q2'], { q0: { 0: 'q0', 1: 'q2' }, q1: { 0: 'q1', 1: 'q3' }, q2: { 0: 'q1', 1: 'q3' }, q3: { 0: 'q1', 1: 'q3' } }) },
    { id: 'repr', steps: true, image: '/automat-delta.jpg', words: ['1011010', '0', '1', '10', '0110', '100', '11', '0010'], lang: 'automat z přednášky zadaný přechodovou funkcí', title: 'Čtyři reprezentace (δ → tabulka → diagram → strom)', alphabet: ['0', '1'], pred: w => /^0*1$/.test(w) || (w.endsWith('0') && w.includes('1')),
      text: 'Automat je zadaný přechodovou funkcí na obrázku: Q = {q0, q1, q2, q3}, Σ = {0, 1}, počáteční stav q0, F = {q1, q2}. Nejdřív přepiš hodnoty δ, pak vyplň tabulku, nakresli diagram a sestav stavový strom.',
      ref: dfa('q0', ['q1', 'q2'], { q0: { 0: 'q0', 1: 'q2' }, q1: { 0: 'q1', 1: 'q3' }, q2: { 0: 'q1', 1: 'q3' }, q3: { 0: 'q1', 1: 'q3' } }) },
  ];

  // Zkontroluje návrh proti úloze: nejdřív podmínky DKA, potom přesná ekvivalence.
  Auto.grade = function (m, task) {
    if (m.alphabet.join(',') !== task.alphabet.join(',')) return { ok: false, kind: 'invalid', problems: [{ kind: 'alphabet', text: `Abeceda úlohy je {${task.alphabet.join(', ')}}.` }] };
    const c = Auto.check(m);
    if (!c.ok) return { ok: false, kind: 'invalid', problems: c.problems };
    const r = Auto.equivalent(m, task.ref, task.alphabet);
    if (r.equal) return { ok: true };
    return { ok: false, kind: 'wrong', word: r.word, mine: r.mine, expected: r.expected };
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = Auto;
  else root.Auto = Auto;
})(typeof window !== 'undefined' ? window : globalThis);
