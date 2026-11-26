// Kontrola výpisků: vypisky/vypisky.json se načte, sekce mají nadpis, id a tělo, v textu nezůstal LaTeX ani wikilinky,
// banka existuje a AI doplnění zůstala označená. Spuštění: node test_vypisky.js
const fs = require('fs');
const path = require('path');

const banks = JSON.parse(fs.readFileSync(path.join(__dirname, 'vypisky', 'vypisky.json'), 'utf8')).banks;
let chyby = 0;
const chyba = msg => { console.log('CHYBA ' + msg); chyby++; };

for (const [stem, d] of Object.entries(banks)) {
  if (!fs.existsSync(path.join(__dirname, 'banky', stem + '.json'))) chyba(`${stem}: banka v banky/ neexistuje`);
  if (!d.title || !d.date || !d.source || !d.sections.length) chyba(`${stem}: chybí title, date, source nebo sekce`);
  const ids = new Set();
  for (const s of d.sections) {
    if (!s.heading || !s.id || !s.body) chyba(`${stem}: sekce „${s.heading}“ bez nadpisu, id nebo těla`);
    if (ids.has(s.id)) chyba(`${stem}: duplicitní id ${s.id}`);
    ids.add(s.id);
    for (const [re, co] of [[/\$/, '$'], [/\\[A-Za-z]/, 'příkaz LaTeXu'], [/\[\[|\]\]/, 'wikilink'], [/!\[/, 'vložený soubor'], [/<\/?small>/, 'HTML <small>']])
      if (re.test(s.heading + s.body)) chyba(`${stem}: „${s.heading}“ obsahuje ${co}`);
  }
  if (!d.sections.some(s => s.body.includes('Doplněno z Claude'))) chyba(`${stem}: chybí označení „Doplněno z Claude“ (zdroj ho obsahuje)`);
  console.log(`${stem}: ${d.sections.length} sekcí`);
}
// cvičení: stejné kontroly textu, banka existuje, id sekcí jsou unikátní
const cv = path.join(__dirname, 'vypisky', 'cviceni.json');
if (fs.existsSync(cv)) for (const [id, d] of Object.entries(JSON.parse(fs.readFileSync(cv, 'utf8')).seminars)) {
  if (!fs.existsSync(path.join(__dirname, 'banky', d.bank + '.json'))) chyba(`cvičení ${id}: banka ${d.bank} neexistuje`);
  if (!d.title || !d.date || !d.source || !d.sections.length) chyba(`cvičení ${id}: chybí title, date, source nebo sekce`);
  const ids = new Set();
  for (const s of d.sections) {
    if (!s.heading || !s.id || (!s.body && s.level !== 2)) chyba(`cvičení ${id}: sekce „${s.heading}“ bez nadpisu, id nebo těla`);
    if (ids.has(s.id)) chyba(`cvičení ${id}: duplicitní id ${s.id}`);
    ids.add(s.id);
    for (const [re, co] of [[/\$/, '$'], [/\\[A-Za-z]/, 'příkaz LaTeXu'], [/\[\[|\]\]/, 'wikilink'], [/!\[/, 'vložený soubor'], [/<\/?small>/, 'HTML <small>']])
      if (re.test(s.heading + s.body)) chyba(`cvičení ${id}: „${s.heading}“ obsahuje ${co}`);
  }
  if (!d.sections.some(s => s.body.includes('Doplněno z Claude'))) chyba(`cvičení ${id}: chybí označení „Doplněno z Claude“`);
  console.log(`cvičení ${id}: ${d.sections.length} sekcí`);
}
console.log(chyby ? `${chyby} chyb` : 'OK');
process.exit(chyby ? 1 : 0);
