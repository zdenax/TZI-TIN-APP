// Kontrola glosáře: glosar/doplnky.json je validní, hesla v balíčku se neopakují, doplněná hesla mají deklaraci AI.
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
  for (const h of hesla)
    if (!(glosar[b] || []).some(g => g.term === h.term)) chyba(`glosar.json ${b}: chybí doplněk „${h.term}“, spusť build_glosar.py`);

for (const b of ['06-2026-11-05', '07-2026-11-12'])
  console.log(`${b}: ${(glosar[b] || []).length} hesel (z toho doplněk ${(doplnky[b] || []).length})`);
console.log(`glosář: chyb ${chyby}`);
process.exit(chyby ? 1 : 0);
