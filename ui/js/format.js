const _escFmt = s => (typeof esc === 'function'
  ? esc(s)
  : String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c])));

function renderLatexExpr(tex, displayMode) {
  if (typeof katex !== 'undefined' && katex && typeof katex.renderToString === 'function') {
    const opts = { displayMode: !!displayMode, throwOnError: false };
    const isMathml = typeof document !== 'undefined' && document.documentElement && document.documentElement.dataset && document.documentElement.dataset.katexMode === 'mathml';
    if (isMathml) opts.output = 'mathml';
    try {
      let html = katex.renderToString(tex, opts);
      if (isMathml) {
        const bb = { N: 'ℕ', Z: 'ℤ', Q: 'ℚ', R: 'ℝ', C: 'ℂ' };
        html = html.replace(/<mi mathvariant="double-struck">([NZQRC])<\/mi>/g, (_, ch) => `<mtext class="math-bb">${bb[ch]}</mtext>`);
      }
      return html;
    } catch (e) {}
  }
  return `<span class="math-tex katex-fallback" data-display="${displayMode ? '1' : '0'}">${_escFmt(tex)}</span>`;
}

// Zápis z banky / glosáře (LaTeX $...$, $$...$$, \(...\), \[...\] + matematické výrazy) převede na KaTeX (HTML / MathML).
function toLatexMathStr(raw) {
  let t = String(raw || '').trim();
  const cmdPlaceholders = [];
  const holdCmd = c => { cmdPlaceholders.push(c); return `\x02CMD${cmdPlaceholders.length - 1}\x02`; };

  // Wrap Czech/multi-letter words inside braces (e.g. {vstup, odchod}, {zavřeno, otevřeno}) before escaping braces, then escape all { and }
  t = t.replace(/\{([^{}\n]{1,64})\}/g, (_, inner) => {
    const safeInner = inner.replace(/(^|[^\\A-Za-z0-9_])([A-Za-záčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]{2,})(?![A-Za-z0-9_])/g,
      (__, pre, w) => `${pre}${holdCmd(`\\text{${w}}`)}`);
    return `{${safeInner}}`;
  });
  t = t.replace(/\{/g, '\\{').replace(/\}/g, '\\}');

  // Sumy a součiny: Σ_(i=1)^n a_i, Π_(i=1)^n a_i
  t = t.replace(/[Σ∑]_\(([^)]+)\)\^\(([^)]+)\)/g, (_, lo, hi) => holdCmd(`\\sum_{${toLatexMathStr(lo)}}^{${toLatexMathStr(hi)}}`));
  t = t.replace(/[Σ∑]_\(([^)]+)\)\^([A-Za-z0-9]+)/g, (_, lo, hi) => holdCmd(`\\sum_{${toLatexMathStr(lo)}}^{${hi}}`));
  t = t.replace(/[Π∏]_\(([^)]+)\)\^\(([^)]+)\)/g, (_, lo, hi) => holdCmd(`\\prod_{${toLatexMathStr(lo)}}^{${toLatexMathStr(hi)}}`));
  t = t.replace(/[Π∏]_\(([^)]+)\)\^([A-Za-z0-9]+)/g, (_, lo, hi) => holdCmd(`\\prod_{${toLatexMathStr(lo)}}^{${hi}}`));

  // Kombinační čísla (n nad k) a odmocniny √(x)
  t = t.replace(/\(([A-Za-z0-9+\-−\s]+?)\s+nad\s+([A-Za-z0-9+\-−\s?]+?)\)/g, (_, a, b) => holdCmd(`\\binom{${toLatexMathStr(a)}}{${toLatexMathStr(b)}}`));
  t = t.replace(/√\(([^)]+)\)/g, (_, x) => holdCmd(`\\sqrt{${toLatexMathStr(x)}}`));
  t = t.replace(/√([A-Za-z0-9]+)/g, (_, x) => holdCmd(`\\sqrt{${x}}`));

  // Operátory, sady čísel, řecká písmena a Kleeneho hvězdička
  t = t.replace(/−/g, '-').replace(/·/g, ' \\cdot ').replace(/…|\.{3}/g, ' \\dots ');
  t = t.replace(/≤/g, ' \\le ').replace(/≥/g, ' \\ge ').replace(/≠/g, ' \\ne ').replace(/≈/g, ' \\approx ').replace(/≡/g, ' \\equiv ');
  t = t.replace(/⊆/g, ' \\subseteq ').replace(/⊂/g, ' \\subset ').replace(/⊇/g, ' \\supseteq ').replace(/⊃/g, ' \\supset ');
  t = t.replace(/∩/g, ' \\cap ').replace(/∪/g, ' \\cup ').replace(/∈/g, ' \\in ').replace(/∉/g, ' \\notin ').replace(/∅/g, ' \\emptyset ').replace(/∖/g, ' \\setminus ');
  t = t.replace(/∧/g, ' \\land ').replace(/∨/g, ' \\lor ').replace(/¬/g, ' \\neg ').replace(/⇒\*/g, ' \\Rightarrow^{*} ').replace(/⇒/g, ' \\Rightarrow ').replace(/⇔/g, ' \\Leftrightarrow ');
  t = t.replace(/→/g, ' \\to ').replace(/←/g, ' \\leftarrow ').replace(/↔/g, ' \\leftrightarrow ').replace(/↦/g, ' \\mapsto ').replace(/∼/g, ' \\sim ');
  t = t.replace(/∀/g, ' \\forall ').replace(/∃!/g, ' \\exists! ').replace(/∃/g, ' \\exists ');
  t = t.replace(/ℕ/g, ' \\mathbb{N} ').replace(/ℤ/g, ' \\mathbb{Z} ').replace(/ℚ/g, ' \\mathbb{Q} ').replace(/ℝ/g, ' \\mathbb{R} ').replace(/ℂ/g, ' \\mathbb{C} ').replace(/𝓛/g, ' \\mathcal{L} ');
  t = t.replace(/∑/g, ' \\sum ').replace(/∏/g, ' \\prod ').replace(/Σ/g, ' \\Sigma ').replace(/Π/g, ' \\Pi ').replace(/δ/g, ' \\delta ').replace(/ε/g, ' \\varepsilon ').replace(/λ/g, ' \\lambda ').replace(/π/g, ' \\pi ').replace(/α/g, ' \\alpha ').replace(/β/g, ' \\beta ').replace(/γ/g, ' \\gamma ').replace(/φ/g, ' \\varphi ');
  t = t.replace(/ᵢ/g, '_i').replace(/ⱼ/g, '_j').replace(/ₖ/g, '_k').replace(/ₙ/g, '_n').replace(/′/g, "'");
  t = t.replace(/[₀-₉]+/g, m => '_{' + [...m].map(c => '₀₁₂₃₄₅₆₇₈₉'.indexOf(c)).join('') + '}');
  t = t.replace(/[⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, m => '^{' + [...m].map(c => ({ '⁻': '-', '⁺': '+', '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9' }[c])).join('') + '}');
  t = t.replace(/\^\([∗*]\)/g, '^{*}').replace(/\^\(\+\)/g, '^{+}');
  t = t.replace(/_\(([^)]+)\)/g, '_{$1}').replace(/\^\(([^)]+)\)/g, '^{$1}');
  t = t.replace(/([A-Za-z]|\\Sigma)\*/g, '$1^{*}');
  t = t.replace(/\\Sigma \*/g, '\\Sigma^{*}');

  if (cmdPlaceholders.length) t = t.replace(/\x02CMD(\d+)\x02/g, (_, i) => cmdPlaceholders[Number(i)]);
  return t.replace(/\s+/g, ' ').trim();
}

function fmt(s) {
  s = String(s);
  const mathBlocks = [];
  const pushMath = (tex, display = false) => {
    const idx = mathBlocks.length;
    mathBlocks.push(renderLatexExpr(tex, display));
    return `\x00MATH${idx}\x00`;
  };
  const subMath = (regex, mapFn = toLatexMathStr) => {
    s = s.replace(regex, m => {
      if (m.includes('\x00')) return m;
      const lead = (m.match(/^\s+/) || [''])[0];
      const trail = (m.match(/\s+$/) || [''])[0];
      const core = m.trim();
      if (!core) return m;
      return lead + pushMath(mapFn(core), false) + trail;
    });
  };
  const unwrapDen = d => {
    d = d.trim();
    while (d.startsWith('(') && d.endsWith(')')) {
      let depth = 0, coversAll = true;
      for (let i = 0; i < d.length - 1; i++) {
        if (d[i] === '(') depth++;
        else if (d[i] === ')') {
          depth--;
          if (depth === 0) { coversAll = false; break; }
        }
      }
      if (!coversAll || depth !== 1) break;
      d = d.slice(1, -1).trim();
    }
    return d;
  };
  const hasProseWord = t => /[áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]/.test(t) || /\b(?!nad\b)[A-Za-z]{2,}\b/.test(t.replace(/_[A-Za-z0-9]+/g, ''));

  if (s.includes('$') || s.includes('\\(') || s.includes('\\[')) {
    s = s.replace(/\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^\$\n]+?)\$/g, (m, d1, d2, i1, i2) => {
      const isDisplay = d1 !== undefined || d2 !== undefined;
      const tex = (d1 !== undefined ? d1 : d2 !== undefined ? d2 : i1 !== undefined ? i1 : i2).trim();
      return pushMath(tex, isDisplay);
    });
  }

  // Automatický převod čistých i vložených matematických výrazů do LaTeX/KaTeX (jen pokud je načtený reálný KaTeX s .version)
  if (typeof katex !== 'undefined' && katex && katex.version && mathBlocks.length === 0) {
    const trimmed = s.trim();
    // 1. Čistý zlomek (např. "n! / ((n-k)! · k!)", "n! / (n-k)!")
    const fracMatch = trimmed.match(/^([0-9A-Za-z()−\-+·…!\s_]+)\s*\/\s*([0-9A-Za-z()−\-+·…!\s_]+)$/);
    if (fracMatch && !hasProseWord(trimmed) && (trimmed.includes('!') || trimmed.includes('−') || trimmed.includes('·') || /^\d+\s*\/\s*\d+$/.test(trimmed))) {
      return renderLatexExpr(`\\frac{${toLatexMathStr(unwrapDen(fracMatch[1]))}}{${toLatexMathStr(unwrapDen(fracMatch[2]))}}`, false);
    }
    // 2. Čistá rovnice / výraz (např. "V_k(n) = n! / (n−k)!", "a = a_n·Z^n + ...", "(n+k−1 nad k)", "n^k")
    const eqFrac = trimmed.match(/^([A-Za-z0-9_()′'!]+)\s*=\s*([0-9A-Za-z()−\-+·…!\s_]+)\s*\/\s*([0-9A-Za-z()−\-+·…!\s_]+)$/);
    if (eqFrac && !hasProseWord(eqFrac[2] + ' ' + eqFrac[3])) {
      return renderLatexExpr(`${toLatexMathStr(eqFrac[1])} = \\frac{${toLatexMathStr(unwrapDen(eqFrac[2]))}}{${toLatexMathStr(unwrapDen(eqFrac[3]))}}`, false);
    }
    if (/^(?:[A-Za-z0-9_()′'!]+|[Σ∑Π∏]_\([^)]+\)\^[A-Za-z0-9]+|\|\{-?\d+\}\|)\s*=\s*[0-9A-Za-z()_\^−\-+·….\s!{}\[\]]+$/.test(trimmed) && !hasProseWord(trimmed)) {
      return renderLatexExpr(toLatexMathStr(trimmed), false);
    }
    if (/^\([A-Za-z0-9+\-−\s]+\s+nad\s+[A-Za-z0-9+\-−\s?]+\)$/.test(trimmed) || /^[A-Za-z0-9]\^[A-Za-z0-9]$/.test(trimmed)) {
      return renderLatexExpr(toLatexMathStr(trimmed), false);
    }

    // 3. Inline kombinační čísla, sumy, součiny, odmocniny a zlomky
    subMath(/(?:C\([A-Za-z0-9+\-−,\s]+\)\s*=\s*)?\([A-Za-z0-9+\-−\s]+?\s+nad\s+[A-Za-z0-9+\-−\s?]+?\)/g);
    subMath(/[Σ∑Π∏]_\([^)]+\)\^(?:\([^)]+\)|[A-Za-z0-9]+)(?:\s*[a-zA-Z]_[A-Za-z0-9ᵢⱼₖₙ]+)?/g);
    subMath(/√\([^)]+\)|√[0-9]+/g);
    subMath(/(?:\([0-9A-Za-z()+\-−·…_!]+\)|[0-9A-Za-z()−\-+·…_]+!)\s*\/\s*(?:\(\([0-9A-Za-z()−\-+·…!_\sᵢⱼₖₙ,]+\)\)!?|\([0-9A-Za-z()−\-+·…!_\sᵢⱼₖₙ,]+\)!?|[0-9A-Za-z_]+!)/g, expr => {
      const m = expr.match(/^([\s\S]+?)\s*\/\s*([\s\S]+)$/);
      return m ? `\\frac{${toLatexMathStr(unwrapDen(m[1]))}}{${toLatexMathStr(unwrapDen(m[2]))}}` : toLatexMathStr(expr);
    });
    subMath(/(^|[\s(,])(−?\d+\/\d+)(?=$|[\s.,;)])/g, m => {
      const p = m.trim().split('/');
      const sign = p[0].startsWith('−') || p[0].startsWith('-') ? '-' : '';
      return `${sign}\\frac{${p[0].replace(/^[−-]/, '')}}{${p[1]}}`;
    });

    // 4. Faktoriály a kombinační volání C(...), V_k(n), C_k(n), P(n)
    subMath(/(?:\([A-Za-z0-9+\-−]+\)!|[0-9A-Za-z]+!)\s*=\s*[A-Za-z0-9()+\-−·…!\s]+?(?=[.,;:]|\s+\([A-Za-z0-9+\-−\s]*[≤≥<>][A-Za-z0-9+\-−\s]*\)|\s+[áčďéěíňóřšťúůýžA-Za-z]{2,}|$)/g);
    subMath(/\b[CVP][′']?(?:_\([^)]+\)|_[A-Za-z0-9]+)?\([^)]+\)(?:\s*[+=]\s*[CVP][′']?(?:_\([^)]+\)|_[A-Za-z0-9]+)?\([^)]+\))*/g);
    subMath(/\([A-Za-z][−\-][A-Za-z](?:[−\-]1)?\)!|\([A-Za-z]\+1\)!|\b[0-9nkv]!/g);

    // 5. Množinové definice tvaru Q = {...}, L(G) = {...}, Π = {...}, Pot({a, b}) = {...}, A/{∼}, |{-5}| = 5
    subMath(/\|\{-?\d+\}\|\s*=\s*\d+/g);
    subMath(/(?:Pot\([^)]+\)|[LP]\([A-Za-z0-9]+\)|[A-Z]\/(?:\{∼\}|∼)|[A-ZΣΠδ](?:_[A-Za-z0-9]+)?)\s*=\s*\{(?:[^{}\n]|\{[^{}\n]*\}){1,96}\}/g);
    subMath(/\b[A-Z]\/(?:\{∼\}|∼)/g);
    subMath(/\bn\([A-Za-z0-9+\-−]+\)…\([A-Za-z0-9+\-−]+\)/g);

    // 6. Řetězce a vztahy (nerovnosti, množinové a logické operátory, přepisy u ⇒* z) — závorky a složené závorky vcelku
    const atom = String.raw`(?:[A-Za-z0-9ᵢⱼₖₙ₀-₉⁻⁺⁰-⁹′'ℕℤℚℝℂ∅¬∀∃!ΣΠδγλφαβV^*+−\-_…|]+|𝓛|\([0-9A-Za-z,ᵢⱼₖₙ₀-₉⁻⁺⁰-⁹′'∗*+\-−\s∪∩;ΠΣ]+\)(?:\^\([^)]+\))?|\{(?:[^{}\n]|\{[^{}\n]*\}){1,64}\})+`;
    subMath(new RegExp(`${atom}(?:\\s*(?:∃!|[≤≥≠≈≡∩∪⊆⊂⊇⊃∈∉∧∨⇒⇔→←↔↦∼=])(?:\\^\\([∗*+]\\)|\\*?)(?:\\s*¬)?\\s*${atom})+`, 'g'));
    subMath(/(?:¬\s*)+[A-Za-z]\s*⇒\s*(?:¬\s*)+[A-Za-z]|∀\s*[A-Za-z]\s*∈\s*[A-Za-zℝℕℤ](?:\s*;\s*[^,.;\n]+)?|∃!?\s*[A-Za-z]\s*∈\s*[A-Za-zℝℕℤ](?:\s*;\s*[^,.;\n]+)?/g);

    // 7. Samostatné množiny {1, 2, 3}, negace ¬ x, operátorové zápisy (Π ∪ Σ)^(+), Σ′^(+), identifikátory s indexy/exponenty a symboly
    subMath(/\{(?:[^{}\n]*?(?:[,;→∈⊆⊂∼…]|-?\d)[^{}\n]*?|[A-Za-zε∅∼]|aa)\}/g);
    subMath(/\([A-Za-zΣΠ∪∩,\s]+\)\^\([^)]+\)|Σ′\^\([∗*+]\)|Σ′/g);
    subMath(/¬\s*[A-Za-z]\b|(?:\([^)\n]+\)|[A-Za-zΣΠφ]|𝓛)_\([^)]+\)(?:\^\([^)]+\))?|(?:[A-Za-zΣΠ]|𝓛)_[A-Za-z0-9]+|[A-Za-zΣΠ]\^\([^)]+\)|[A-Za-z]\^[A-Za-z0-9]+|\b[Vqpu][₀-₉]+\b|\bV\*(?!\w)|[ℕℤℚℝℂ∅∑∏∀∃¬∧∨⇒⇔→←↔↦]|(?<![A-Za-z])[ΣΠδεγλφ](?![A-Za-z])/g);
  }

  s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  s = s
    .replace(/_\(([^)]+)\)/g, '<sub>$1</sub>').replace(/_([A-Za-z0-9]+)/g, '<sub>$1</sub>')
    .replace(/\^\(([^)]+)\)/g, '<sup>$1</sup>').replace(/\^([A-Za-z0-9]+)/g, '<sup>$1</sup>')
    .replace(/[₀-₉]+/g, m => '<sub>' + [...m].map(c => '₀₁₂₃₄₅₆₇₈₉'.indexOf(c)).join('') + '</sub>')
    .replace(/-&gt;/g, '→').replace(/&lt;-/g, '←').replace(/\.\.\./g, '…');
  if (mathBlocks.length > 0) {
    s = s.replace(/\x00MATH(\d+)\x00/g, (_, i) => mathBlocks[Number(i)]);
  }
  return s;
}


