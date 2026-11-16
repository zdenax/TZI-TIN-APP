// Sdílené formátování vzorců (zlomky, indexy, mocniny) pro novy.html a glosar.html.
function fmt(s) {
  s = String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\.\.\./g, '…');
  return fracs(s)
    .replace(/\(([^()<>]+?) nad ([^()<>]+?)\)/g, '<span class="binom"><span><span>$1</span><span>$2</span></span></span>')
    .replace(/_\(([^)]+)\)/g, '<sub>$1</sub>').replace(/_([A-Za-z0-9]+)/g, '<sub>$1</sub>')
    .replace(/\^\(([^)]+)\)/g, '<sup>$1</sup>').replace(/\^([A-Za-z0-9]+)/g, '<sup>$1</sup>')
    .replace(/[₀-₉]+/g, m => '<sub>' + [...m].map(c => '₀₁₂₃₄₅₆₇₈₉'.indexOf(c)).join('') + '</sub>')
    .replace(/-&gt;/g, '→').replace(/&lt;-/g, '←');
}

// „a / b“ jako zlomek nad sebou. Jen čísla, jednopísmenné proměnné, ! a závorky, ať „pravda (1) / nepravda (0)“ nebo A/∼ zůstanou textem.
const isMath = t => /^[\p{L}\d!()·…+−\-,^_ ]+$/u.test(t) && !/\p{L}{2}/u.test(t);
const unwrap = t => {
  if (t[0] !== '(') return t;
  for (let i = 0, d = 0; i < t.length; i++) { d += t[i] === '(' ? 1 : t[i] === ')' ? -1 : 0; if (!d) return i === t.length - 1 ? t.slice(1, -1) : t; }
  return t;
};
function fracs(s) {
  for (let i = s.indexOf('/'); i >= 0; i = s.indexOf('/', i + 1)) {
    const a = s[i - 1] === ' ' ? i - 1 : i, b = s[i + 1] === ' ' ? i + 2 : i + 1;
    let l = a, r = b, d = 0;
    for (; l > 0; l--) { // čitatel: doleva po mezeru, závorky celé, součin „5 · 4“ patří celý
      const c = s[l - 1];
      if (c === ')') d++;
      else if (c === '(') { if (!d) break; d--; }
      else if (!d && /[\s=,;]/.test(c)) { if (s.slice(l - 3, l) === ' · ') { l -= 2; continue; } break; }
    }
    while (l < a && '−+-'.includes(s[l])) l++; // znaménko zůstane před zlomkem
    for (d = 0; r < s.length; r++) { // jmenovatel: doprava po mezeru, závorky celé
      const c = s[r];
      if (c === '(') d++;
      else if (c === ')') { if (!d) break; d--; }
      else if (!d && /[\s=,;/.]/.test(c)) break;
    }
    const num = s.slice(l, a), den = s.slice(b, r);
    if (!num || !den || !isMath(num) || !isMath(den) || !/[\d!]/.test(num + den)) continue;
    const html = `<span class="frac"><span>${unwrap(num)}</span><span>${unwrap(den)}</span></span>`;
    s = s.slice(0, l) + html + s.slice(r);
    i = l + html.length - 1;
  }
  return s;
}

// Zadání příkladu: dlouhý souvislý text s přechodovou funkcí automatu nebo pravidly gramatiky se rozloží na
// nadpis, definici, tabulku a vlastní otázku. Jiné texty projdou jen přes fmt. Banky se nemění, jde o vykreslení.
function fmtZadani(text) {
  return zadaniAutomat(text) || zadaniGramatika(text) || fmt(text);
}

function zadaniHlava(pred) {
  const i = pred.indexOf(': ');
  return i > 0 && i < 60 ? [pred.slice(0, i), pred.slice(i + 2)] : ['', pred];
}

function zadaniAutomat(t) {
  const re = /δ\(([^,()]+), ([^,()]+)\) = ([^\s,.()]+)/g;
  const m = [...t.matchAll(re)];
  let n = 1; // souvislý úsek přechodů oddělených „, “
  while (n < m.length && t.slice(m[n - 1].index + m[n - 1][0].length, m[n].index) === ', ') n++;
  if (n < 4) return null;
  const konec = m[n - 1].index + m[n - 1][0].length;
  let [nadpis, def] = zadaniHlava(t.slice(0, m[0].index).replace(/[,\s]+$/, ''));
  let zbytek = t.slice(konec);
  const f = zbytek.match(/^,\s*(F = \{[^}]*\})\.\s*([\s\S]*)$/); // u dveří je F až za přechody
  if (f) { def += (def ? ', ' : '') + f[1]; zbytek = f[2]; } else zbytek = zbytek.replace(/^[.,]\s*/, '');
  const stavy = [], znaky = [], bunka = {};
  for (const x of m.slice(0, n)) {
    if (!stavy.includes(x[1])) stavy.push(x[1]);
    if (!znaky.includes(x[2])) znaky.push(x[2]);
    bunka[x[1] + '\u0000' + x[2]] = x[3];
  }
  const poc = (def.match(/počáteční stav ([^\s,]+)/) || [])[1];
  const kon = ((def.match(/F = \{([^}]*)\}/) || [])[1] || '').split(/,\s*/);
  const znak = s => (s === poc && kon.includes(s) ? '↔ ' : s === poc ? '→ ' : kon.includes(s) ? '← ' : '');
  const hlavicka = '<tr><th>δ</th>' + znaky.map(z => `<th>${fmt(z)}</th>`).join('') + '</tr>';
  const radky = stavy.map(s => `<tr><th>${znak(s)}${fmt(s)}</th>` +
    znaky.map(z => `<td>${fmt(bunka[s + '\u0000' + z] || '–')}</td>`).join('') + '</tr>').join('');
  return (nadpis ? `<div class="zad-t">${fmt(nadpis)}</div>` : '') +
    (def ? `<div class="zad-def">${fmt(def)}</div>` : '') +
    `<table class="zad-tab"><thead>${hlavicka}</thead><tbody>${radky}</tbody></table>` +
    (zbytek ? `<div class="zad-ot">${fmt(zbytek)}</div>` : '');
}

function zadaniGramatika(t) {
  const m = t.match(/^([^:]{1,40}): (.*?), pravidla (\(\d+\) [^.\n]+)\.\s*([\s\S]*)$/);
  if (!m) return null;
  const pravidla = m[3].split(/, (?=\(\d+\))/);
  if (pravidla.length < 3) return null;
  return `<div class="zad-t">${fmt(m[1])}</div><div class="zad-def">${fmt(m[2])}</div>` +
    `<div class="zad-prav">${pravidla.map(p => `<div>${fmt(p)}</div>`).join('')}</div>` +
    (m[4] ? `<div class="zad-ot">${fmt(m[4])}</div>` : '');
}
