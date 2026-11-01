// Sdílené formátování vzorců (zlomky, indexy, mocniny) pro novy.html a glosar.html.
function fmt(s) {
  s = String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\.\.\./g, '…');
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
