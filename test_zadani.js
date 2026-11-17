// Test vykreslení zadání (fmtZadani v ui/fmt.js): tabulka přechodů a pravidla gramatiky musí odpovídat původnímu textu.
// Spuštění: node test_zadani.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'ui/fmt.js'), 'utf8'), ctx);

const bez = h => h.replace(/<\/?sub>/g, m => (m === '</sub>' ? '' : '')).replace(/<[^>]+>/g, '|');
const subs = s => s.replace(/<sub>(\d+)<\/sub>/g, (_, d) => [...d].map(c => '₀₁₂₃₄₅₆₇₈₉'[c]).join(''));
const text = h => subs(h).replace(/<[^>]+>/g, '').replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');
let chyb = 0, tabulek = 0, gramatik = 0;
const chyba = (id, m) => { chyb++; console.log('CHYBA', id, m); };

for (const f of fs.readdirSync(path.join(__dirname, 'banky')).filter(x => x.endsWith('.json'))) {
  const qs = JSON.parse(fs.readFileSync(path.join(__dirname, 'banky', f), 'utf8')).questions;
  for (const q of qs) {
    const t = q.text;
    const trojice = [...t.matchAll(/δ\(([^,()]+), ([^,()]+)\) = ([^\s,.()]+)/g)];
    const h = ctx.fmtZadani(t);
    if (trojice.length >= 4) {
      if (!h.includes('zad-tab')) { chyba(q.id, 'tabulka se nevykreslila'); continue; }
      tabulek++;
      const radky = [...h.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(r => [...r[1].matchAll(/<t[dh]>([\s\S]*?)<\/t[dh]>/g)].map(c => text(c[1]).replace(/^[→←↔] /, '')));
      const hlav = radky[0].slice(1);
      for (const [, s, z, c] of trojice) {
        const r = radky.find(x => x[0] === s);
        if (!r || r[1 + hlav.indexOf(z)] !== c) chyba(q.id, `δ(${s}, ${z}) = ${c} není v tabulce správně`);
      }
      if (radky.length - 1 !== new Set(trojice.map(x => x[1])).size) chyba(q.id, 'počet řádků');
      // vlastní otázka (poslední věta) zůstala
      const otazka = t.slice(t.lastIndexOf('. ') + 2);
      if (!text(h).includes(otazka.slice(0, 20))) chyba(q.id, 'chybí otázka za tabulkou');
    } else if (/, pravidla \(1\)/.test(t) && (t.match(/^[^:]+: .*?, pravidla ((?:\(\d+\) [^,.]+(?:, )?)+)\./) || [, ''])[1].split(/, (?=\(\d+\))/).length >= 3) {
      // seznam o třech a více pravidlech (první seznam v textu; druhý, např. analytická verze, zůstane ve větě)
      if (!h.includes('zad-prav')) { chyba(q.id, 'pravidla se nevykreslila'); continue; }
      gramatik++;
      const prvni = t.match(/^[^:]+: .*?, pravidla ((?:\(\d+\) [^,.]+(?:, )?)+)\./)[1].split(/, (?=\(\d+\))/).length;
      if ((h.match(/<div>\(\d+\)/g) || []).length < prvni) chyba(q.id, 'chybí pravidlo');
      // pravidlo je krátké a otázka za seznamem je zvlášť (nesmí se slít s posledním pravidlem)
      for (const r of h.matchAll(/<div>(\(\d+\)[^<]*)<\/div>/g)) if (text(r[1]).length > 25) chyba(q.id, 'pravidlo je moc dlouhé: ' + text(r[1]));
      if (!h.includes('zad-ot')) chyba(q.id, 'chybí otázka za pravidly');
    } else if (h !== ctx.fmt(t)) chyba(q.id, 'text bez tabulky se změnil');
  }
}
console.log(`zadání: ${tabulek} tabulek přechodů, ${gramatik} seznamů pravidel, chyb ${chyb}`);
process.exit(chyb ? 1 : 0);
