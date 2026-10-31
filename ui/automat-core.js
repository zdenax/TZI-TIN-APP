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
    { id: 'prednaska', lang: 'automat z přednášky: aspoň jedna 1 a končí 0, nebo tvar 0…01', title: 'Automat z přednášky', alphabet: ['0', '1'], pred: w => /^0*1$/.test(w) || (w.endsWith('0') && w.includes('1')),
      text: 'Překresli automat z přednášky podle tabulky: q₀ je počáteční, přijímací jsou q₁ a q₂.  δ: q₀ → (0: q₀, 1: q₂), q₁ → (0: q₁, 1: q₃), q₂ → (0: q₁, 1: q₃), q₃ → (0: q₁, 1: q₃). Stavy pojmenuj q0, q1, q2, q3.',
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
