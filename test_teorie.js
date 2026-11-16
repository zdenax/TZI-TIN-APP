// Kontrola teoretických otázek (choice = filtr „Teorie“): krátké zadání, žádná vypsaná δ-tabulka ani trasování.
// Výpočty na zadaných datech patří do příkladů (input). Spuštění: node test_teorie.js
const fs = require('fs');
const path = require('path');

const MAX_DELKA = 250;   // zadání teorie do ~2 vět
const MAX_DELTA = 4;     // víc zápisů δ(…) = vypsaná tabulka přechodů (automat z přednášky jich má 8)
const dir = path.join(__dirname, 'banky');
let chyby = 0, pocet = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort()) {
  for (const q of JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')).questions) {
    if (q.type !== 'choice') continue;
    pocet++;
    const nDelta = (q.text.match(/δ\(/g) || []).length;
    const stopa = [q.text, ...Object.values(q.options)].some(t => /\S → \S+ → \S/.test(t));  // posloupnost stavů = trasování
    if (q.text.length > MAX_DELKA || nDelta > MAX_DELTA || stopa) {
      console.log(`CHYBA ${q.id} (${f}): délka ${q.text.length}, δ(…) ${nDelta}×${stopa ? ', trasování' : ''}`);
      chyby++;
    }
  }
}
console.log(`teorie: ${pocet} otázek, chyb ${chyby}`);
process.exit(chyby ? 1 : 0);
