// Kontrola glosáře: glosar/doplnky.json je validní, hesla v balíčku se neopakují, doplněná hesla mají deklaraci AI,
// hesla 6. a 7. přednášky mají příklad a časté omyly.
// Spuštění: node test_glosar.js
const fs = require('fs');
const path = require('path');

const nacti = f => JSON.parse(fs.readFileSync(path.join(__dirname, 'glosar', f), 'utf8')).banks;
let chyby = 0;
const chyba = msg => { console.log('CHYBA ' + msg); chyby++; };

const doplnky = nacti('doplnky.json');  // nevalidní JSON shodí test výjimkou
const banky = new Set(fs.readdirSync(path.join(__dirname, 'banky')).filter(f => f.endsWith('.json')).map(f => f.slice(0, -5)));
for (const [b, hesla] of Object.entries(doplnky)) {
  if (!banky.has(b)) chyba(`doplnky.json: balíček ${b} nemá banku v banky/`);
  const videt = new Set();
  for (const h of hesla) {
    if (h.pripoj_k !== undefined) {  // příloha k existujícímu heslu (build_glosar.py ji připojí na konec jeho těla)
      if (typeof h.pripoj_k !== 'string' || !h.pripoj_k || typeof h.body !== 'string' || !h.body || h.term !== undefined) chyba(`doplnky.json ${b}: příloha musí mít jen pripoj_k a body`);
      else if (!/^\*Zdroj: .*Doplněno z Claude.*\*$/m.test(h.body)) chyba(`doplnky.json ${b}: příloha k „${h.pripoj_k}“ nemá řádek *Zdroj: …* s „Doplněno z Claude“`);
      continue;
    }
    if (typeof h.term !== 'string' || !h.term || typeof h.body !== 'string' || !h.body) { chyba(`doplnky.json ${b}: heslo bez term nebo body`); continue; }
    if (videt.has(h.term)) chyba(`doplnky.json ${b}: duplicitní heslo „${h.term}“`);
    videt.add(h.term);
    if (!h.body.includes('Doplněno z Claude')) chyba(`doplnky.json ${b}: „${h.term}“ nemá označení „Doplněno z Claude“`);
    if (!/^\*Zdroj: .*\*$/m.test(h.body)) chyba(`doplnky.json ${b}: „${h.term}“ nemá řádek *Zdroj: …*`);
  }
}

// vygenerovaný glosář: v balíčku žádné heslo dvakrát a doplňky v něm opravdu jsou (build_glosar.py proběhl)
const glosar = nacti('glosar.json');
for (const [b, hesla] of Object.entries(glosar)) {
  const terms = hesla.map(h => h.term);
  terms.filter((t, i) => terms.indexOf(t) !== i).forEach(t => chyba(`glosar.json ${b}: duplicitní heslo „${t}“`));
}
for (const [b, hesla] of Object.entries(doplnky))
  for (const h of hesla) {
    if (h.pripoj_k !== undefined) {
      const cil = (glosar[b] || []).find(g => g.term === h.pripoj_k);
      if (!cil || !cil.body.endsWith('\n' + h.body)) chyba(`glosar.json ${b}: heslo „${h.pripoj_k}“ nemá na konci přílohu z doplnky.json, spusť build_glosar.py`);
    } else if (!(glosar[b] || []).some(g => g.term === h.term)) chyba(`glosar.json ${b}: chybí doplněk „${h.term}“, spusť build_glosar.py`);
  }

// hesla 6. a 7. přednášky: příklad (řádek *Příklad…) a časté omyly (*Časté omyly:* + odrážky ❌ … ✅ …, nejvýš 3),
// za nimi řádek *Zdroj…* s deklarací AI, která omyly zmiňuje. Výjimky jen s důvodem.
const BEZ_PRIKLADU = {
  'Přirozený jazyk jako jazyk': 'úvodní výrok z přednášky, příklad by byl umělý',
  'Automat z přednášky q_0–q_3: výpočty a jazyk': 'heslo je samo rozpracovaný příklad',
  'Příklad: systém 01 → 10, 10 → 01': 'heslo je samo rozpracovaný příklad',
  'Příklad: gramatika S → aBb': 'heslo je samo rozpracovaný příklad',
  'Příklad: gramatika k automatu q_0–q_2': 'heslo je samo rozpracovaný příklad',
  'Gramatiky a automaty: co rozpoznává který typ': 'přehledová tabulka, příklad by byl umělý',
};
for (const b of ['06-2026-11-05', '07-2026-11-12'])
  for (const h of glosar[b] || []) {
    const L = h.body.split('\n');
    if (!BEZ_PRIKLADU[h.term] && !/\*Příklad/.test(h.body)) chyba(`glosar.json ${b}: „${h.term}“ nemá příklad (*Příklad…)`);
    const i = L.indexOf('*Časté omyly:*');
    if (i < 0) { chyba(`glosar.json ${b}: „${h.term}“ nemá *Časté omyly:*`); continue; }
    let j = i + 1;
    for (; j < L.length && /^- /.test(L[j]); j++)
      if (!/^- ❌ .+ ✅ .+/.test(L[j])) chyba(`glosar.json ${b}: „${h.term}“: omyl není ve tvaru „- ❌ … ✅ …“`);
    if (j - i - 1 < 1 || j - i - 1 > 3) chyba(`glosar.json ${b}: „${h.term}“ má ${j - i - 1} omylů (má mít 1 až 3)`);
    if (!(L[j] || '').startsWith('*Zdroj') || !L[j].includes('Doplněno z Claude') || !/omyl/i.test(L[j]))
      chyba(`glosar.json ${b}: „${h.term}“: za omyly chybí řádek *Zdroj…* s „Doplněno z Claude“ a zmínkou o omylech`);
  }

for (const b of ['06-2026-11-05', '07-2026-11-12'])
  console.log(`${b}: ${(glosar[b] || []).length} hesel (z toho doplněk ${(doplnky[b] || []).filter(h => !h.pripoj_k).length}, příloh k heslům z Glosar.md ${(doplnky[b] || []).filter(h => h.pripoj_k).length})`);
console.log(`glosář: chyb ${chyby}`);
process.exit(chyby ? 1 : 0);
