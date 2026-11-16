try {
  const th = localStorage.getItem('tzi_theme');
  if (th === 'light' || th === 'dark') document.documentElement.setAttribute('data-theme', th);
} catch (e) {}

const svg = document.getElementById('board'), $ = id => document.getElementById(id);
const R = 28;
const RESERVED_IDS = new Set(['__proto__', 'constructor', 'prototype', 'toString', 'valueOf', 'hasOwnProperty']);
const sub = s => String(s).replace(/\d/g, d => '₀₁₂₃₄₅₆₇₈₉'[d]);
const S = id => String(id).replace(/\d+/g, sub);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));
const isSafeId = s => typeof s === 'string' && /^[A-Za-z0-9_′']{1,16}$/.test(s) && !RESERVED_IDS.has(s);
const safeImgSrc = src => {
  if (typeof src !== 'string') return null;
  if (src === '/automat-delta.jpg') return src;
  if (/^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]{1,2000000}$/.test(src)) return src;
  return null;
};
const safeParseJson = raw => {
  if (typeof raw !== 'string' || !raw || raw.length > 3_000_000) return null;
  return JSON.parse(raw, (k, v) => (k === '__proto__' || k === 'constructor' || k === 'prototype') ? undefined : v);
};

const fresh = alphabet => ({ alphabet, states: [], start: null, accept: [], trans: [] });
let M = fresh(['0', '1']), mode = 'move', selS = null, selE = null, task = null, given = false, tab = 'diagram', TABS = [];
let exTask = null, drag = null, rubber = null, sim = { word: '', pos: 0 }, VW = 800, RP = null;
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };

function sanitizeModel(raw, fallbackAlphabet) {
  const al = Array.isArray(raw && raw.alphabet)
    ? [...new Set(raw.alphabet.filter(a => typeof a === 'string' && [...a].length === 1))].slice(0, 32)
    : [];
  const alphabet = fallbackAlphabet ? fallbackAlphabet.slice() : (al.length ? al : ['0', '1']);
  const out = fresh(alphabet);
  if (!raw || typeof raw !== 'object') return out;
  const seenIds = new Set();
  if (Array.isArray(raw.states)) {
    for (const st of raw.states.slice(0, 64)) {
      if (!st || !isSafeId(st.id) || seenIds.has(st.id)) continue;
      seenIds.add(st.id);
      const x = Number.isFinite(st.x) ? Math.min(2000, Math.max(0, Math.round(st.x))) : 150;
      const y = Number.isFinite(st.y) ? Math.min(1000, Math.max(0, Math.round(st.y))) : 260;
      out.states.push({ id: st.id, x, y });
    }
  }
  out.start = isSafeId(raw.start) && seenIds.has(raw.start) ? raw.start : null;
  out.accept = Array.isArray(raw.accept) ? [...new Set(raw.accept.filter(id => isSafeId(id) && seenIds.has(id)))] : [];
  if (Array.isArray(raw.trans)) {
    for (const tr of raw.trans.slice(0, 512)) {
      if (!tr || !isSafeId(tr.from) || !isSafeId(tr.to) || !seenIds.has(tr.from) || !seenIds.has(tr.to)) continue;
      if (!Array.isArray(tr.symbols)) continue;
      const syms = [...new Set(tr.symbols.filter(a => typeof a === 'string' && alphabet.includes(a)))];
      if (syms.length) out.trans.push({ from: tr.from, to: tr.to, symbols: syms });
    }
  }
  return out;
}

// ── vlastní úlohy (uložené v prohlížeči) ─────────────────────────────────────
const CKEY = 'tzi_automat_tasks';
let custom = [];
try {
  const a = safeParseJson(lsGet(CKEY));
  if (Array.isArray(a)) {
    custom = a.slice(0, 30).filter(c => c && typeof c.id === 'string' && /^[A-Za-z0-9_-]{1,32}$/.test(c.id) &&
      typeof c.title === 'string' && typeof c.text === 'string' && Array.isArray(c.alphabet) && c.ref && typeof c.ref === 'object')
      .map(c => {
        const al = [...new Set(c.alphabet.filter(x => typeof x === 'string' && [...x].length === 1))].slice(0, 16);
        if (!al.length) return null;
        const ref = sanitizeModel(c.ref, al);
        if (!ref.states.length || !ref.start) return null;
        return Auto.makeGiven({
          id: c.id,
          title: c.title.slice(0, 120),
          text: c.text.slice(0, 20000),
          image: safeImgSrc(c.image),
          alphabet: al,
          ref: { start: ref.start, accept: ref.accept, states: ref.states.map(s => ({ id: s.id })), trans: ref.trans },
          words: Array.isArray(c.words) ? c.words.filter(w => typeof w === 'string' && w.length <= 64).slice(0, 16) : undefined,
          custom: true
        });
      }).filter(Boolean);
  }
} catch (e) { /* žádné */ }
const saveCustom = () => lsSet(CKEY, JSON.stringify(custom.map(t => ({
  id: t.id, title: t.title, text: t.text, image: safeImgSrc(t.image), alphabet: t.alphabet, ref: t.ref, words: t.words
}))));
const allTasks = () => [...Auto.TASKS, ...custom];
const doneMap = () => {
  try {
    const d = safeParseJson(lsGet('tzi_automat_done'));
    if (!d || typeof d !== 'object' || Array.isArray(d)) return {};
    const out = {};
    for (const [k, v] of Object.entries(d)) if (typeof v === 'boolean' && /^[A-Za-z0-9_-]{1,32}$/.test(k)) out[k] = v;
    return out;
  } catch (e) { return {}; }
};

// ── ukládání návrhu (pro každou úlohu zvlášť) ────────────────────────────────
const KEY = () => 'tzi_automat_' + (task ? task.id : 'volny');
const save = () => lsSet(KEY(), JSON.stringify(M));
function load(alphabet) {
  try {
    const m = safeParseJson(lsGet(KEY()));
    if (m && Array.isArray(m.states) && Array.isArray(m.trans)) return sanitizeModel(m, alphabet);
  } catch (e) { /* nový */ }
  return fresh(alphabet);
}

// ── geometrie ────────────────────────────────────────────────────────────────
const pos = id => M.states.find(s => s.id === id);
function toSvg(ev) { const p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; const q = p.matrixTransform(svg.getScreenCTM().inverse()); return { x: q.x, y: q.y }; }
function toClient(x, y) { const p = svg.createSVGPoint(); p.x = x; p.y = y; return p.matrixTransform(svg.getScreenCTM()); }
function fitBoard() { // plátno má pevnou výšku 520 a šířku podle poměru stran okna
  const r = $('boardWrap').getBoundingClientRect(); if (!r.width || !r.height) return;
  VW = Math.max(600, Math.round(520 * r.width / r.height)); svg.setAttribute('viewBox', `0 0 ${VW} 520`);
}
new ResizeObserver(fitBoard).observe($('boardWrap'));
const hasBack = t => M.trans.some(u => u.from === t.to && u.to === t.from) && t.from !== t.to;
function edgeGeom(t) {
  const a = pos(t.from), b = pos(t.to);
  if (t.from === t.to) {
    return { d: `M ${a.x - 16} ${a.y - R + 4} C ${a.x - 40} ${a.y - R - 62}, ${a.x + 40} ${a.y - R - 62}, ${a.x + 16} ${a.y - R + 4}`, lx: a.x, ly: a.y - R - 46 };
  }
  const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len, nx = -uy, ny = ux;
  const bend = hasBack(t) ? 34 : 0;
  const cx = (a.x + b.x) / 2 + nx * bend * 2, cy = (a.y + b.y) / 2 + ny * bend * 2; // řídicí bod kvadratické křivky
  const end = (p, k) => { const vx = cx - p.x, vy = cy - p.y, l = Math.hypot(vx, vy) || 1; return { x: p.x + vx / l * k, y: p.y + vy / l * k }; };
  const s = end(a, R), e = end(b, R + 4);
  return { d: `M ${s.x} ${s.y} Q ${cx} ${cy} ${e.x} ${e.y}`, lx: (s.x + 2 * cx + e.x) / 4 + nx * 12, ly: (s.y + 2 * cy + e.y) / 4 + ny * 12 };
}

// ── stavový strom jako obrázek (sdílí ho živý náhled i kontrola ve cvičení) ──
function treeSvg(m) {
  const tr = Auto.tree(m);
  if (!tr) return '<span class="hint">Strom potřebuje počáteční stav.</span>';
  const L = Auto.treeLayout(tr), DX = 86, DY = 96, r = 22, X = o => 64 + DX / 2 + o.x * DX, Y = o => 40 + o.y * DY;
  const W = 64 + L.leaves * DX + 30, H = 40 + L.depth * DY + 50;
  let e = '', n = '', lv = '';
  for (const o of L.nodes) {
    if (o.parent) {
      const x1 = X(o.parent), y1 = Y(o.parent), x2 = X(o), y2 = Y(o), l = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / l, uy = (y2 - y1) / l;
      const mx = x1 + (x2 - x1) * .45, my = y1 + (y2 - y1) * .45;
      e += `<g class="tr-e"><line x1="${x1 + ux * r}" y1="${y1 + uy * r}" x2="${x2 - ux * (r + 4)}" y2="${y2 - uy * (r + 4)}" marker-end="url(#tarrow)"/><rect x="${mx - 11}" y="${my - 11}" width="22" height="22" rx="6"/><text x="${mx}" y="${my}">${esc(o.n.sym)}</text></g>`;
    }
    const acc = m.accept.includes(o.n.state);
    n += `<g class="tr-n${o.n.seen ? ' seen' : ''}"><circle cx="${X(o)}" cy="${Y(o)}" r="${r}"/><text x="${X(o)}" y="${Y(o)}">${esc(S(o.n.state))}</text>` +
      (acc ? `<line class="tr-acc" x1="${X(o) + r}" y1="${Y(o)}" x2="${X(o) + r + 20}" y2="${Y(o)}" marker-end="url(#tarrow)"/>` : '') + '</g>';
  }
  for (let i = 0; i <= L.depth; i++) lv += `<text class="tr-l" x="8" y="${40 + i * DY + 4}">úr. ${i}</text>`;
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Stavový strom"><defs><marker id="tarrow" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="11" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" class="svg-arrow"/></marker></defs>${lv}${e}${n}</svg>` +
    '<p class="hint mt-xs">← šipka ven = přijímací stav · čárkovaně a šedě = stav, který už ve stromu někde rozvinutý je (dál se nerozvíjí)</p>';
}

// ── vykreslení plátna a živých náhledů ───────────────────────────────────────
function diagramInner(mid, withRubber) { // obsah SVG s diagramem; stejný pro plátno i pro náhled pod čtením slova (mid = id šipky)
  const safeMid = esc(mid);
  let h = `<defs><marker id="${safeMid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" class="svg-arrow"/></marker></defs>`;
  M.trans.forEach((t, i) => {
    const g = edgeGeom(t), label = t.symbols.join(', '), w = Math.max(24, label.length * 10 + 10);
    h += `<g class="ed${withRubber && selE === i ? ' sel' : ''}" ${withRubber ? `data-e="${i}"` : ''}><path d="${g.d}" marker-end="url(#${safeMid})"/>` +
      (withRubber ? `<path d="${g.d}" class="svg-hit" marker-end=""/>` : '') +
      `<rect x="${g.lx - w / 2}" y="${g.ly - 11}" width="${w}" height="22" rx="6"/><text x="${g.lx}" y="${g.ly}">${esc(label)}</text></g>`;
  });
  M.states.forEach(s => {
    if (M.start === s.id) h += `<line class="mark" x1="${s.x - R - 46}" y1="${s.y}" x2="${s.x - R - 2}" y2="${s.y}" marker-end="url(#${safeMid})"/>`;
    if (M.accept.includes(s.id)) h += `<line class="mark" x1="${s.x + R}" y1="${s.y}" x2="${s.x + R + 44}" y2="${s.y}" marker-end="url(#${safeMid})"/>`;
    h += `<g class="st${withRubber && selS === s.id ? ' sel' : ''}${sim.cur === s.id ? ' cur' : ''}" data-s="${esc(s.id)}"><circle cx="${s.x}" cy="${s.y}" r="${R}"/><text x="${s.x}" y="${s.y}">${esc(S(s.id))}</text></g>`;
  });
  if (withRubber && rubber) h += `<line class="rubber" x1="${rubber.x1}" y1="${rubber.y1}" x2="${rubber.x2}" y2="${rubber.y2}"/>`;
  return h;
}
function renderWordDiagram() { // diagram pod čtením slova (jen k prohlížení)
  const w = $('wBoard'); if (!w) return;
  if (!M.states.length) { w.setAttribute('viewBox', '0 0 600 120'); w.innerHTML = '<text x="300" y="60" class="svg-empty-msg">Diagram je zatím prázdný. Nakresli ho v kroku Diagram.</text>'; return; }
  const xs = M.states.map(s => s.x), ys = M.states.map(s => s.y), pad = 95;
  const x0 = Math.min(...xs) - pad, y0 = Math.min(...ys) - pad - 30;
  w.setAttribute('viewBox', `${x0} ${y0} ${Math.max(360, Math.max(...xs) + pad - x0)} ${Math.max(240, Math.max(...ys) + pad - y0)}`);
  w.innerHTML = diagramInner('arrow2', false);
}
function render() {
  const chk = Auto.check(M);
  svg.innerHTML = diagramInner('arrow', true);
  renderWordDiagram(); syncDelta();
  const st = $('dStatus');
  if (!M.states.length) { st.className = 'status'; st.textContent = ''; }
  else if (chk.ok) { st.className = 'status ok'; st.textContent = 'Deterministický a úplný automat.'; }
  else { st.className = 'status ' + (chk.multi.length ? 'bad' : 'warn'); st.textContent = chk.problems.map(p => p.text).join(' '); }
  const key = M.states.map(x => x.id).join(','); // výběr stavů pro „+ Šipka“ se přepisuje, jen když se změnil seznam stavů
  if ($('aFrom').dataset.key !== key) {
    const keep = [$('aFrom').value, $('aTo').value], opts = M.states.map(x => `<option value="${esc(x.id)}">${esc(S(x.id))}</option>`).join('');
    [$('aFrom'), $('aTo')].forEach((el, i) => { el.innerHTML = opts; el.dataset.key = key; if (M.states.some(x => x.id === keep[i])) el.value = keep[i]; });
  }
  if (!given) renderLive();
}

function renderLive() { // tabulka, strom a čtení slova z vlastního návrhu (úlohy „podle popisu“ a volný návrh)
  if (!$('lTable')) return;
  const d = Auto.delta(M);
  let t = '<table><tr><th></th>' + M.alphabet.map(a => `<th>${esc(a)}</th>`).join('') + '</tr>';
  for (const s of M.states) {
    t += `<tr><th>${M.start === s.id ? '→ ' : ''}${M.accept.includes(s.id) ? '← ' : ''}${esc(S(s.id))}</th>`;
    for (const a of M.alphabet) { const c = (d[s.id] && d[s.id][a]) || []; t += `<td class="${!c.length ? 'miss' : c.length > 1 ? 'multi' : ''}">${c.length ? c.map(x => esc(S(x))).join(', ') : '–'}</td>`; }
    t += '</tr>';
  }
  $('lTable').innerHTML = M.states.length ? `<div class="table-wrap">${t}</table></div><p class="hint">Tabulka se plní sama z tvého automatu. → počáteční, ← přijímací, „–“ = chybí přechod.</p>` : '<span class="hint">Zatím žádný stav. V kroku Diagram přidej stavy.</span>';
  $('lTree').innerHTML = treeSvg(M);
  renderTrace();
}

function renderTrace() {
  const out = $('trace'); if (!out) return;
  const r = Auto.run(M, sim.word);
  if (!sim.active) { out.textContent = ''; sim.cur = null; svgCur(); return; }
  const k = Math.min(sim.pos, r.steps.length);
  let txt = S(M.start || '?');
  for (let i = 0; i < k; i++) txt += ` –${r.steps[i].read}→ ${S(r.steps[i].to)}`;
  const done = k === sim.word.length || (r.stuck && k === r.steps.length), rest = [...sim.word].slice(k).join('');
  let verdict = '';
  if (r.stuck && k === r.steps.length && sim.pos > r.steps.length) verdict = `<br><b class="verdict-bad">Zaseknuto: ${esc(r.stuck)}</b>`;
  else if (done) verdict = `<br><b class="${r.accepted ? 'verdict-ok' : 'verdict-bad'}">${r.accepted ? 'Přijato ✓' : 'Nepřijato ✗'}</b> (skončil ve stavu ${esc(S(r.state || '?'))})`;
  out.innerHTML = `${esc(txt)}${rest ? `<br><span class="hint">zbývá: ${esc(rest)}</span>` : ''}${verdict}`;
  sim.cur = k === 0 ? M.start : r.steps[k - 1] ? r.steps[k - 1].to : r.state;
  svgCur();
}
function svgCur() { document.querySelectorAll('svg .st').forEach(g => g.classList.toggle('cur', g.dataset.s === sim.cur)); }
function changed() { save(); sim.active = false; sim.cur = null; render(); }

// ── akce na plátně ───────────────────────────────────────────────────────────
function nextId() { let i = 0; while (pos('q' + i)) i++; return 'q' + i; }
function addState(x, y) {
  if (M.states.length >= 64) { alert('Maximální počet stavů je 64.'); return; }
  const id = nextId();
  M.states.push({ id, x: Math.round(x), y: Math.round(y) });
  if (!M.start) M.start = id;
  selS = id; selE = null; changed();
}
function removeState(id) {
  M.states = M.states.filter(s => s.id !== id); M.trans = M.trans.filter(t => t.from !== id && t.to !== id);
  M.accept = M.accept.filter(x => x !== id); if (M.start === id) M.start = null;
  if (selS === id) selS = null; changed();
}
function removeEdge(i) { M.trans.splice(i, 1); selE = null; changed(); }
function parseSymbols(text) { return [...new Set([...String(text)].filter(c => !/[\s,;]/.test(c)))].slice(0, 32); }
function setSymbols(from, to, text, replaceIndex) {
  const syms = parseSymbols(text), bad = syms.filter(a => !M.alphabet.includes(a));
  if (bad.length) { alert(`Znak ${bad.join(', ')} není v abecedě {${M.alphabet.join(', ')}}.`); return; }
  if (replaceIndex !== undefined) M.trans.splice(replaceIndex, 1);
  if (syms.length) {
    const ex = M.trans.find(t => t.from === from && t.to === to);
    if (ex) ex.symbols = [...new Set([...ex.symbols, ...syms])].sort(); else M.trans.push({ from, to, symbols: syms.sort() });
  }
  selE = null; changed();
}
function ask(x, y, initial, cb) {
  document.querySelectorAll('.floating').forEach(n => n.remove());
  const c = toClient(x, y), inp = document.createElement('input');
  inp.className = 'floating'; inp.type = 'text'; inp.value = initial; inp.autocomplete = 'off'; inp.maxLength = 64;
  inp.style.left = Math.max(4, c.x - 60) + 'px'; inp.style.top = Math.max(4, c.y - 16) + 'px';
  let done = false;
  const finish = ok => { if (done) return; done = true; const v = inp.value; inp.remove(); if (ok) cb(v); };
  inp.onkeydown = e => { if (e.key === 'Enter') finish(true); else if (e.key === 'Escape') finish(false); };
  inp.onblur = () => finish(true);
  document.body.appendChild(inp); inp.focus(); inp.select();
}
function renameState(id) {
  const s = pos(id); if (!s) return;
  ask(s.x, s.y, id, v => {
    v = v.trim();
    if (v === id) return;
    if (!/^[A-Za-z0-9_′']{1,8}$/.test(v) || RESERVED_IDS.has(v)) { alert('Název stavu: 1 až 8 znaků (písmena, čísla, _).'); return; }
    if (pos(v)) { alert(`Stav ${v} už existuje.`); return; }
    s.id = v; M.trans.forEach(t => { if (t.from === id) t.from = v; if (t.to === id) t.to = v; });
    M.accept = M.accept.map(x => x === id ? v : x); if (M.start === id) M.start = v; if (selS === id) selS = v; changed();
  });
}

// ── ukazatel (myš, dotyk i pero) ─────────────────────────────────────────────
svg.addEventListener('pointerdown', ev => {
  const st = ev.target.closest('[data-s]'), ed = ev.target.closest('[data-e]'), p = toSvg(ev);
  if (st) {
    const id = st.dataset.s;
    if (mode === 'erase') return removeState(id);
    if (mode === 'start') { M.start = M.start === id ? null : id; return changed(); }
    if (mode === 'acc') { M.accept = M.accept.includes(id) ? M.accept.filter(x => x !== id) : [...M.accept, id]; return changed(); }
    if (mode === 'edge') { const s = pos(id); if (!s) return; rubber = { from: id, x1: s.x, y1: s.y, x2: p.x, y2: p.y }; svg.setPointerCapture(ev.pointerId); return; }
    selS = id; selE = null;
    const s = pos(id); if (!s) return;
    drag = { id, dx: s.x - p.x, dy: s.y - p.y, moved: false };
    svg.setPointerCapture(ev.pointerId); render(); return;
  }
  if (ed) {
    const i = +ed.dataset.e;
    if (mode === 'erase') return removeEdge(i);
    selE = i; selS = null; render(); return;
  }
  if (mode === 'state') return addState(p.x, p.y);
  selS = null; selE = null; render();
});
svg.addEventListener('pointermove', ev => {
  const p = toSvg(ev);
  if (drag) { const s = pos(drag.id); if (!s) return; s.x = Math.min(VW - 30, Math.max(30, Math.round(p.x + drag.dx))); s.y = Math.min(490, Math.max(30, Math.round(p.y + drag.dy))); drag.moved = true; render(); }
  else if (rubber) { rubber.x2 = p.x; rubber.y2 = p.y; render(); }
});
svg.addEventListener('pointerup', ev => {
  if (drag) { if (drag.moved) save(); drag = null; return; }
  if (rubber) {
    const from = rubber.from, p = toSvg(ev), b = M.states.find(s => Math.hypot(s.x - p.x, s.y - p.y) <= R + 8);
    rubber = null; render();
    if (b) ask(b.x, b.y - R - 20, '', v => setSymbols(from, b.id, v));
  }
});
svg.addEventListener('dblclick', ev => {
  const at = document.elementFromPoint(ev.clientX, ev.clientY), st = at && at.closest('[data-s]'), ed = at && at.closest('[data-e]');
  if (st) return renameState(st.dataset.s);
  if (ed) { const i = +ed.dataset.e, t = M.trans[i]; if (!t) return; const g = edgeGeom(t); return ask(g.lx, g.ly, t.symbols.join(', '), v => setSymbols(t.from, t.to, v, i)); }
  const p = toSvg(ev); addState(p.x, p.y);
});
document.addEventListener('keydown', ev => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(ev.target.tagName) || tab !== 'diagram') return;
  if (ev.key === 'Delete' || ev.key === 'Backspace') { if (selS) removeState(selS); else if (selE !== null) removeEdge(selE); }
});

// ── ovládání plátna ──────────────────────────────────────────────────────────
function setMode(m) {
  mode = m; rubber = null;
  document.querySelectorAll('#tools button[data-mode]').forEach(x => x.setAttribute('aria-pressed', x.dataset.mode === m));
  svg.style.cursor = { move: 'default', state: 'copy', edge: 'crosshair', erase: 'not-allowed', start: 'pointer', acc: 'pointer' }[m];
}
$('tools').addEventListener('click', ev => { const b = ev.target.closest('button[data-mode]'); if (b) setMode(b.dataset.mode); });
$('aAdd').onclick = () => {
  if (!M.states.length) { alert('Nejdřív přidej stavy (+ Stav).'); return; }
  if (!parseSymbols($('aSym').value).length) { alert('Napiš znak (nebo znaky) přechodu, např. 0 nebo 0, 1.'); return; }
  setSymbols($('aFrom').value, $('aTo').value, $('aSym').value); $('aSym').value = '';
};
$('aSym').onkeydown = ev => { if (ev.key === 'Enter') $('aAdd').click(); };
$('clear').onclick = () => { if (!M.states.length || confirm('Smazat celý návrh?')) { M = fresh(M.alphabet); selS = selE = null; exTask = null; $('ex').value = ''; lsSet('tzi_automat_ex', ''); renderZad(); changed(); } };
$('alpha').onchange = () => {
  const a = parseSymbols($('alpha').value);
  if (!a.length) { $('alpha').value = M.alphabet.join(', '); return; }
  M.alphabet = a; M.trans = M.trans.map(t => ({ ...t, symbols: t.symbols.filter(x => a.includes(x)) })).filter(t => t.symbols.length);
  $('alpha').value = a.join(', '); changed();
};
function doGrade() {
  const g = Auto.grade(M, task), outs = [...document.querySelectorAll('.gradeOut')];
  const setOut = h => { outs.forEach(o => { o.innerHTML = h; }); };
  if (g.ok) {
    setOut('<div class="result ok">✓ Správně. Tvůj automat přijímá přesně správná slova (porovnáno na všech možných slovech, ne jen na pár).</div>');
    if (given) { RP.done.diagram = true; rsave(); } else { const dm = doneMap(); dm[task.id] = true; lsSet('tzi_automat_done', JSON.stringify(dm)); }
    renderTabs(); return;
  }
  if (given) { RP.done.diagram = false; rsave(); renderTabs(); }
  if (g.kind === 'invalid') { setOut('<div class="result bad">Nejdřív oprav automat:<br>' + g.problems.map(p => esc(p.text)).join('<br>') + '</div>'); return; }
  const w = g.word === '' ? 'prázdné slovo' : `slovo „${esc(g.word)}“`;
  setOut(`<div class="result bad">Ještě ne. Na ${w} se liší: tvůj automat ho ${g.mine ? 'přijímá' : 'nepřijímá'}, ale má ho ${g.expected ? 'přijímat' : 'nepřijímat'}. <button class="btn tryWord">Přečíst toto slovo</button></div>`);
  document.querySelectorAll('.tryWord').forEach(b => { b.onclick = () => { showTab('word'); if (!given) { $('word').value = g.word; $('whole').click(); } }; });
}
$('grade').onclick = doGrade;

// ── hotový příklad do volného návrhu ─────────────────────────────────────────
const LECTURE_XY = { q0: [150, 260], q1: [400, 150], q2: [400, 370], q3: [650, 260] };
function exampleModel(t) {
  const n = t.ref.states.length, ox = (VW - 800) / 2;
  const states = t.ref.states.map((s, i) => {
    const a = Math.PI + i * 2 * Math.PI / n;
    const xy = LECTURE_XY[s.id] || [Math.round(400 + 250 * Math.cos(a)), Math.round(260 + 170 * Math.sin(a))];
    return { id: s.id, x: Math.round(xy[0] + ox), y: xy[1] };
  });
  const trans = [];
  for (const u of t.ref.trans) {
    const ex = trans.find(x => x.from === u.from && x.to === u.to);
    if (ex) ex.symbols.push(...u.symbols); else trans.push({ from: u.from, to: u.to, symbols: [...u.symbols] });
  }
  return { alphabet: t.alphabet.slice(), states, start: t.ref.start, accept: t.ref.accept.slice(), trans };
}
$('ex').onchange = () => {
  const t = allTasks().find(x => x.id === $('ex').value);
  if (!t) return;
  if (M.states.length && !confirm('Příklad přepíše tvůj návrh. Pokračovat?')) { $('ex').value = ''; return; }
  M = exampleModel(t); selS = selE = null; changed(); $('alpha').value = M.alphabet.join(', ');
  exTask = t; lsSet('tzi_automat_ex', t.id); renderZad();
};

// ── zadání vlevo, kroky nahoře ───────────────────────────────────────────────
const zadOf = t => {
  const img = safeImgSrc(t.image);
  return (img ? `<img src="${esc(img)}" alt="Zadání úlohy">` : '') + (t.steps ? `<pre>${esc(t.text)}</pre>` : `<p>${esc(t.text)}</p>`);
};
function renderZad() {
  let h;
  if (!task) {
    h = '<h2>Volný návrh</h2><p class="hint">Kresli, co chceš. Úlohu s kontrolou vybereš nahoře. Tabulka, strom i čtení slova se řídí tvým diagramem.</p>';
    if (exTask) h += `<hr class="zad-sep"><h2>Zadání příkladu: ${esc(exTask.title)}</h2>` + zadOf(exTask);
  } else {
    h = `<h2>${esc(task.title)}</h2>`;
    const img = safeImgSrc(task.image);
    if (img) h += `<img src="${esc(img)}" alt="Zadání úlohy">`;
    h += task.steps ? `<pre>${esc(task.text)}</pre>` : `<p>${esc(task.text)}</p>`;
  }
  $('zadBody').innerHTML = h;
}
const doneOf = id => !task ? false : task.steps ? ({ delta: RP.done.delta, table: RP.done.table, diagram: RP.done.diagram, tree: RP.done.tree, word: RP.wordsOk >= 3 })[id] : id === 'diagram' && !!doneMap()[task.id];
function renderTabs() {
  $('tabs').innerHTML = '<span class="row" role="tablist" aria-label="Kroky úlohy">' +
    TABS.map(([id, label]) => `<button class="tab" role="tab" data-t="${esc(id)}" aria-selected="${id === tab}">${esc(label)}${doneOf(id) ? '<span class="ck">✓</span>' : ''}</button>`).join('') +
    '</span><span class="sp"></span><button class="btn" id="zadToggle" title="Skrýt nebo ukázat zadání vlevo">Zadání ◧</button>';
  $('zadToggle').onclick = () => $('app').classList.toggle('noZad');
}
$('tabs').addEventListener('click', ev => { const b = ev.target.closest('.tab'); if (b) showTab(b.dataset.t); });
function showTab(id) {
  tab = id;
  for (const [k] of [['delta'], ['table'], ['diagram'], ['tree'], ['word']]) $('p-' + k).hidden = k !== id;
  lsSet('tzi_automat_tab_' + (task ? task.id : 'volny'), id);
  renderTabs();
  if (id === 'delta') {
    syncDelta();
    const t = $('dText');
    if (t && t.value === skeleton()) { t.focus(); t.setSelectionRange(5, 5); }
  } else if (id === 'diagram') { fitBoard(); render(); } else if (id === 'word') { if (given) sim.cur = null; renderWordDiagram(); }
  $('pane').scrollTop = 0;
}

// ── úloha „zadaný automat“: δ → tabulka → diagram → strom → čtení slova ──────
const RKEY = () => 'tzi_automat_repr_' + task.id;
const rsave = () => { if (task && task.steps) lsSet(RKEY(), JSON.stringify(RP)); };
const paint = (el, ok) => { el.classList.toggle('good', ok === true); el.classList.toggle('bad', ok === false); };

function sanitizeRP(raw, ids, al, nWords) {
  const out = { delta: {}, table: {}, marks: {}, levels: [], done: {}, wi: 0, run: { states: [], verdict: null }, wordsOk: 0 };
  if (!raw || typeof raw !== 'object') return out;
  const copyMap = (src, allowBool) => {
    const res = {};
    if (!src || typeof src !== 'object') return res;
    for (const q of ids) {
      if (!src[q] || typeof src[q] !== 'object') continue;
      res[q] = {};
      if (allowBool) {
        if (typeof src[q].start === 'boolean') res[q].start = src[q].start;
        if (typeof src[q].accept === 'boolean') res[q].accept = src[q].accept;
      } else {
        for (const a of al) if (typeof src[q][a] === 'string') res[q][a] = src[q][a].slice(0, 32);
      }
    }
    return res;
  };
  out.delta = copyMap(raw.delta, false);
  out.table = copyMap(raw.table, false);
  out.marks = copyMap(raw.marks, true);
  if (Array.isArray(raw.levels)) out.levels = raw.levels.slice(0, 32).map(x => typeof x === 'string' ? x.slice(0, 512) : '');
  if (raw.done && typeof raw.done === 'object') {
    for (const k of ['delta', 'table', 'diagram', 'tree']) if (typeof raw.done[k] === 'boolean') out.done[k] = raw.done[k];
  }
  if (Number.isInteger(raw.wi) && raw.wi >= 0 && nWords > 0) out.wi = raw.wi % nWords;
  if (raw.run && typeof raw.run === 'object') {
    out.run = {
      states: Array.isArray(raw.run.states) ? raw.run.states.slice(0, 64).map(x => typeof x === 'string' ? x.slice(0, 32) : '') : [],
      verdict: typeof raw.run.verdict === 'boolean' ? raw.run.verdict : null
    };
  }
  if (Number.isInteger(raw.wordsOk) && raw.wordsOk >= 0) out.wordsOk = Math.min(raw.wordsOk, 10000);
  return out;
}

function buildGiven() {
  const ref = task.ref, al = task.alphabet, ids = ref.states.map(s => s.id), rm = { ...ref, alphabet: al }, nLevels = Auto.treeLevels(rm).length;
  let parsedRP = null;
  try {
    const raw = lsGet(RKEY()) || (task.id === 'repr' ? lsGet('tzi_automat_repr') : null);
    if (raw) parsedRP = safeParseJson(raw);
  } catch (e) { parsedRP = null; }
  RP = sanitizeRP(parsedRP, ids, al, task.words.length);
  const cellIn = (kind, q, a) => `<input type="text" class="cell" maxlength="32" data-${kind}="${esc(q)}|${esc(a)}" value="${esc((RP[kind === 'd' ? 'delta' : 'table'][q] || {})[a] || '')}" autocomplete="off" aria-label="δ(${esc(q)}, ${esc(a)})">`;
  let h = '<h2>1. Přechodová funkce δ</h2><p class="hint">Podle zadání vlevo napiš, kam automat přejde, např. <code>q2</code>.</p><div class="dgrid">';
  for (const q of ids) for (const a of al) h += `<label>δ(${esc(S(q))}, ${esc(a)}) = ${cellIn('d', q, a)}</label>`;
  $('p-delta').innerHTML = h + '</div><div class="row"><button class="btn primary" id="rD">Zkontrolovat δ</button><span id="rDo"></span></div>';
  const dgrid = $('p-delta').querySelector('.dgrid');
  if (dgrid) dgrid.style.gridTemplateColumns = `repeat(${al.length},auto)`;
  h = '<h2>2. Tabulka přechodů</h2><p class="hint">Vyplň buňky. Zaškrtni → u počátečního a ← u přijímacích stavů.</p><div class="table-wrap"><table><tr><th>→</th><th>←</th><th></th>' + al.map(a => `<th>${esc(a)}</th>`).join('') + '</tr>';
  for (const q of ids) h += `<tr><td><input type="checkbox" data-m="${esc(q)}|start" ${(RP.marks[q] || {}).start ? 'checked' : ''}></td><td><input type="checkbox" data-m="${esc(q)}|accept" ${(RP.marks[q] || {}).accept ? 'checked' : ''}></td><th>${esc(S(q))}</th>` + al.map(a => `<td>${cellIn('t', q, a)}</td>`).join('') + '</tr>';
  $('p-table').innerHTML = h + '</table></div><div class="row"><button class="btn primary" id="rTb">Zkontrolovat tabulku</button><span id="rTo"></span></div>';
  h = '<h2>4. Stavový strom</h2><p class="hint">Po úrovních shora dolů, stavy zleva doprava oddělené mezerou (znaky na hranách nepiš). Stav, který už je ve stromu rozvinutý, se dál nerozvíjí. Po správné odpovědi se strom nakreslí.</p>';
  for (let i = 0; i < nLevels; i++) h += `<div class="row"><label class="lv-label">Úroveň ${i}</label><input type="text" class="lv" maxlength="512" data-l="${i}" value="${esc(RP.levels[i] || '')}" autocomplete="off" placeholder="např. q0 q1"></div>`;
  $('p-tree').innerHTML = h + '<div class="row"><button class="btn primary" id="rSb">Zkontrolovat strom</button><span id="rSo"></span></div><div id="rSt" class="treebox" hidden></div>';
  $('p-word').innerHTML = '<h2>5. Čtení slova</h2><div id="rWbody"></div><svg id="wBoard" aria-label="Diagram"></svg>';
  const showTree = () => { $('rSt').hidden = !RP.done.tree; if (RP.done.tree) $('rSt').innerHTML = treeSvg(rm); };
  const word = () => task.words[RP.wi];
  function drawWord() {
    const w = word();
    let x = `<p class="hint">Slovo <b class="trace">${esc(w)}</b>: začni ve stavu ${esc(S(ref.start))}, dopiš stav po přečtení každého znaku a rozhodni, jestli automat slovo přijme.</p><div class="row trace">${esc(S(ref.start))}`;
    [...w].forEach((c, i) => { x += ` –${esc(c)}→ <input type="text" class="cell" maxlength="32" data-w="${i}" value="${esc(RP.run.states[i] || '')}" autocomplete="off" aria-label="stav po ${i + 1}. znaku">`; });
    x += `</div><div class="row"><label><input type="radio" name="verdict" data-v="1" ${RP.run.verdict === true ? 'checked' : ''}> Přijato</label><label><input type="radio" name="verdict" data-v="0" ${RP.run.verdict === false ? 'checked' : ''}> Nepřijato</label></div>`;
    x += `<div class="row"><button class="btn primary" id="rWb">Zkontrolovat slovo</button><button class="btn" id="rWn">Další slovo</button><span id="rWo"></span></div><p class="hint">Správně zvládnutých slov: ${RP.wordsOk} (✓ u kroku od 3)</p>`;
    $('rWbody').innerHTML = x;
    $('rWb').onclick = () => {
      const r = Auto.gradeRun(RP.run.states, RP.run.verdict, ref, w);
      $('rWbody').querySelectorAll('input[data-w]').forEach(i => paint(i, !r.wrong.includes(+i.dataset.w)));
      const o = $('rWo');
      if (r.ok) { RP.wordsOk++; o.className = 'done'; o.textContent = ` ✓ Správně, slovo ${r.accepted ? 'je přijato' : 'není přijato'}.`; }
      else { o.className = 'status bad'; o.textContent = r.wrong.length ? ` ✗ chybné stavy: ${r.wrong.map(i => i + 1 + '.').join(', ')} znak` : r.verdictOk ? '' : (RP.run.verdict === null ? ' ✗ Vyber, jestli je slovo přijato.' : ' ✗ Stavy sedí, ale verdikt ne: přijímací je jen stav ze F, kde slovo skončilo.'); }
      rsave(); renderTabs();
    };
    $('rWn').onclick = () => { RP.wi = (RP.wi + 1) % task.words.length; RP.run = { states: [], verdict: null }; rsave(); drawWord(); };
  }
  const mark = (kind, wrong, out, okMsg) => {
    $('pane').querySelectorAll(`input[data-${kind}]`).forEach(i => { const [q, a] = i.dataset[kind].split('|'); paint(i, !wrong.some(w => w.q === q && w.a === a)); });
    out.className = wrong.length ? 'status bad' : 'done'; out.textContent = wrong.length ? ` ✗ chybných buněk: ${wrong.length}` : okMsg;
  };
  $('pane').oninput = ev => {
    if (!(task && task.steps)) return;
    const t = ev.target, [q, k] = (t.dataset.d || t.dataset.t || t.dataset.m || '').split('|');
    if (t.dataset.w) { RP.run.states[+t.dataset.w] = t.value; paint(t, null); rsave(); sim.cur = Auto.parseStates(t.value)[0] || null; svgCur(); return; }
    if (t.dataset.v) { RP.run.verdict = t.dataset.v === '1'; rsave(); return; }
    if (t.dataset.d && isSafeId(q)) (RP.delta[q] = RP.delta[q] || {})[k] = t.value;
    else if (t.dataset.t && isSafeId(q)) (RP.table[q] = RP.table[q] || {})[k] = t.value;
    else if (t.dataset.m && isSafeId(q)) (RP.marks[q] = RP.marks[q] || {})[k] = t.checked;
    else if (t.dataset.l) RP.levels[+t.dataset.l] = t.value;
    else return;
    paint(t, null); rsave();
  };
  $('rD').onclick = () => { const w = Auto.gradeDelta(RP.delta, ref, al); mark('d', w, $('rDo'), ' ✓ δ sedí.'); RP.done.delta = !w.length; rsave(); renderTabs(); };
  $('rTb').onclick = () => {
    const r = Auto.gradeTable(RP.table, RP.marks, ref, al);
    mark('t', r.wrong, $('rTo'), r.badMarks.length ? '' : ' ✓ Tabulka sedí.');
    if (r.badMarks.length) { $('rTo').className = 'status bad'; $('rTo').textContent += ` ✗ chybná značka → nebo ← u: ${r.badMarks.join(', ')}`; }
    RP.done.table = r.ok; rsave(); renderTabs();
  };
  $('rSb').onclick = () => {
    const r = Auto.gradeLevels(RP.levels, rm);
    $('pane').querySelectorAll('input[data-l]').forEach(i => paint(i, !r.wrong.includes(+i.dataset.l)));
    $('rSo').className = r.ok ? 'done' : 'status bad'; $('rSo').textContent = r.ok ? ' ✓ Strom sedí.' : ` ✗ chybné úrovně: ${r.wrong.join(', ')}`;
    RP.done.tree = r.ok; showTree(); rsave(); renderTabs();
  };
  drawWord(); showTree();
}

// ── úlohy „podle popisu“ a volný návrh: živé náhledy z vlastního diagramu ────
const autoPos = (i, n) => { const a = Math.PI + i * 2 * Math.PI / n; return { x: Math.round(VW / 2 + Math.min(250, VW / 2 - 70) * Math.cos(a)), y: Math.round(260 + 170 * Math.sin(a)) }; };
function specFromM() { // přechodová funkce z diagramu jako text
  if (!M.states.length) return '';
  const d = Auto.delta(M), l = [`Q = {${M.states.map(s => s.id).join(', ')}}`, `Σ = {${M.alphabet.join(', ')}}`];
  if (M.start) l.push(`počáteční stav ${M.start}`);
  l.push(`F = {${M.accept.join(', ')}}`);
  for (const s of M.states) for (const a of M.alphabet) for (const t of (d[s.id] && d[s.id][a]) || []) l.push(`δ(${s.id}, ${a}) = ${t}`);
  return l.join('\n');
}
const skeleton = () => `Q = {}\nΣ = {${M.alphabet.join(', ')}}\npočáteční stav \nF = {}\nδ(, ) = `;
function syncDelta() { const t = $('dText'); if (t && document.activeElement !== t) t.value = M.states.length ? specFromM() : skeleton(); }
function applySpec(text) {
  const sp = Auto.parseSpec(String(text).slice(0, 20000)), msg = $('dMsg');
  if (!text.trim()) { msg.innerHTML = ''; return; }
  if (sp.states.length) {
    const al = task ? task.alphabet : (sp.alphabet.length ? sp.alphabet : M.alphabet), old = Object.fromEntries(M.states.map(s => [s.id, s]));
    M.alphabet = al.slice();
    M.states = sp.states.slice(0, 64).map((s, i) => old[s.id] || { id: s.id, ...autoPos(i, Math.min(sp.states.length, 64)) });
    M.start = sp.start; M.accept = sp.accept.filter(a => M.states.some(s => s.id === a));
    M.trans = sp.trans.map(t => ({ ...t, symbols: t.symbols.filter(a => al.includes(a)) })).filter(t => t.symbols.length);
    if (!task) $('alpha').value = al.join(', ');
    save(); sim.active = false; sim.cur = null; render();
  }
  msg.innerHTML = sp.ok ? '<p class="done">✓ Úplná přechodová funkce, tabulka, diagram i strom se podle ní vykreslily.</p>' : sp.problems.map(x => `<p class="status warn">${esc(x)}</p>`).join('');
}
function buildLive() {
  RP = null;
  $('p-delta').innerHTML = '<h2>1. Přechodová funkce δ</h2><p class="hint">Navrhni ji sám podle zadání vlevo: napiš stavy Q, abecedu Σ, počáteční stav, F a přechody <code>δ(q0, 0) = q1</code>, každý na jeden řádek. Tabulka, diagram a strom se podle toho udělají samy. Stejně tak se tu ukáže δ z diagramu, který nakreslíš.</p>' +
    '<textarea id="dText" rows="14" maxlength="20000" spellcheck="false"></textarea><div id="dMsg"></div>' +
    '<div class="row"><button class="btn" id="dAdd" title="Přidá řádek δ( , ) = a nastaví kurzor do závorky">+ přechod δ( , ) =</button><button class="btn primary" id="dGrade">Zkontrolovat automat</button></div><div class="gradeOut"></div>';
  $('dText').oninput = () => applySpec($('dText').value);
  $('dGrade').onclick = doGrade; $('dGrade').hidden = !task;
  $('dAdd').onclick = () => {
    const t = $('dText'); t.focus();
    if (!/δ\(, \) =\s*$/.test(t.value)) t.value = t.value.replace(/\s*$/, '') + '\nδ(, ) = ';
    const c = t.value.lastIndexOf('δ(, )') + 2; t.setSelectionRange(c, c);
  };
  syncDelta();
  $('p-table').innerHTML = '<h2>2. Tabulka přechodů</h2><div id="lTable"></div>';
  $('p-tree').innerHTML = '<h2>4. Stavový strom</h2><div id="lTree" class="treebox"></div>';
  $('p-word').innerHTML = '<h2>5. Čtení slova</h2><div class="row"><input type="text" id="word" maxlength="256" placeholder="např. 1011010" size="16" autocomplete="off"><button class="btn" id="step">Krok</button><button class="btn" id="whole">Celé</button><button class="btn" id="reset">Znovu</button></div><div id="trace" class="trace"></div><p class="hint">Slovo čte tvůj diagram, aktuální stav je zvýrazněný.</p><svg id="wBoard" aria-label="Diagram"></svg>';
  const startWord = () => { sim = { word: $('word').value.replace(/\s/g, '').slice(0, 256), pos: 0, active: true, cur: M.start }; };
  $('word').oninput = () => { startWord(); sim.active = false; renderTrace(); };
  $('step').onclick = () => { if (!sim.active || sim.word !== $('word').value.replace(/\s/g, '').slice(0, 256)) startWord(); sim.pos = Math.min(sim.pos + 1, sim.word.length + 1); renderTrace(); };
  $('whole').onclick = () => { startWord(); sim.pos = sim.word.length; renderTrace(); };
  $('reset').onclick = () => { startWord(); renderTrace(); };
  $('pane').oninput = null;
}

// ── výběr úlohy ──────────────────────────────────────────────────────────────
const sel = $('task');
function fillSelect() {
  const all = allTasks(), opt = t => `<option value="${esc(t.id)}">${t.custom ? '★ ' : ''}${esc(t.title)}</option>`;
  sel.innerHTML = `<optgroup label="Zadaný automat: δ, tabulka, diagram, strom, slovo">${all.filter(t => t.steps).map(opt).join('')}</optgroup>` +
    `<optgroup label="Navrhni automat podle popisu">${all.filter(t => !t.steps).map(opt).join('')}</optgroup><option value="">Volný návrh</option>`;
  $('ex').innerHTML = '<option value="">Vyber…</option>' + all.map(t => `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join('');
}
function setTask(id) {
  task = allTasks().find(t => t.id === id) || null; given = !!(task && task.steps);
  lsSet('tzi_automat_last', task ? task.id : ''); sel.value = task ? task.id : '';
  M = load(task ? task.alphabet.slice() : M.alphabet);
  selS = selE = null; sim = { word: '', pos: 0 }; setMode('move');
  $('alpha').value = M.alphabet.join(', '); $('freeTools').hidden = !!task;
  exTask = task ? null : allTasks().find(t => t.id === lsGet('tzi_automat_ex')) || null; $('ex').value = exTask ? exTask.id : '';
  $('grade').hidden = !task; document.querySelectorAll('.gradeOut').forEach(o => { o.innerHTML = ''; }); $('delTask').hidden = !(task && task.custom);
  if (given) buildGiven(); else buildLive();
  TABS = [['delta', '1. δ'], ['table', '2. Tabulka'], ['diagram', '3. Diagram'], ['tree', '4. Strom'], ['word', '5. Čtení slova']];
  renderZad();
  const t = lsGet('tzi_automat_tab_' + (task ? task.id : 'volny'));
  showTab(TABS.some(x => x[0] === t) ? t : TABS[0][0]);
}
sel.onchange = () => setTask(sel.value);
$('delTask').onclick = () => {
  if (!(task && task.custom) || !confirm(`Smazat úlohu „${task.title}“ i s rozpracovaným řešením?`)) return;
  for (const k of ['tzi_automat_' + task.id, 'tzi_automat_repr_' + task.id, 'tzi_automat_tab_' + task.id]) try { localStorage.removeItem(k); } catch (e) { /* nic */ }
  custom = custom.filter(t => t.id !== task.id); saveCustom(); fillSelect(); setTask(Auto.TASKS[0].id);
};

// ── nová úloha ───────────────────────────────────────────────────────────────
const dlg = $('newDlg'); let nImg = null;
function previewSpec() {
  const sp = Auto.parseSpec(String($('nSpec').value).slice(0, 20000));
  let h = '';
  if (sp.states.length) h += `<p class="hint">Rozpoznáno: stavy ${sp.states.map(s => esc(S(s.id))).join(', ')} · Σ = {${sp.alphabet.map(esc).join(', ')}} · počáteční ${esc(S(sp.start || '?'))} · F = {${sp.accept.map(x => esc(S(x))).join(', ')}} · přechodů ${sp.trans.reduce((n, t) => n + t.symbols.length, 0)}</p>`;
  h += sp.ok ? '<p class="done">✓ Úplný deterministický automat, můžeš uložit.</p>' : sp.problems.map(p => `<p class="status bad">${esc(p)}</p>`).join('');
  $('nPrev').innerHTML = h; $('nSave').disabled = !sp.ok;
}
function readImg(file) {
  if (!file || !file.type.startsWith('image/') || file.size > 10 * 1024 * 1024) return;
  const img = new Image();
  const objUrl = URL.createObjectURL(file);
  img.onload = () => {
    URL.revokeObjectURL(objUrl);
    if (!img.width || !img.height) return;
    const k = Math.min(1, 1400 / img.width), c = document.createElement('canvas');
    c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    nImg = safeImgSrc(c.toDataURL('image/jpeg', .82));
    $('nImgState').textContent = nImg ? 'Obrázek přidán ✓' : 'Obrázek je příliš velký.';
  };
  img.onerror = () => URL.revokeObjectURL(objUrl);
  img.src = objUrl;
}
$('newTask').onclick = () => { $('nTitle').value = ''; $('nSpec').value = ''; $('nImg').value = ''; $('nImgState').textContent = ''; nImg = null; previewSpec(); dlg.showModal(); $('nSpec').focus(); };
$('nSpec').oninput = previewSpec;
$('nSpec').addEventListener('paste', ev => { const f = [...(ev.clipboardData ? ev.clipboardData.files : [])].find(x => x.type.startsWith('image/')); if (f) { ev.preventDefault(); readImg(f); } });
$('nImg').onchange = () => readImg($('nImg').files[0]);
$('nCancel').onclick = () => dlg.close();
$('nSave').onclick = () => {
  if (custom.length >= 30) { alert('Maximální počet vlastních úloh je 30.'); return; }
  const sp = Auto.parseSpec(String($('nSpec').value).slice(0, 20000)); if (!sp.ok) return;
  const t = Auto.makeGiven({
    id: 'u' + Date.now().toString(36),
    title: $('nTitle').value.trim().slice(0, 120) || `Moje úloha ${custom.length + 1}`,
    custom: true,
    alphabet: sp.alphabet,
    ref: { start: sp.start, accept: sp.accept, states: sp.states, trans: sp.trans },
    text: $('nSpec').value.trim().slice(0, 20000),
    image: safeImgSrc(nImg)
  });
  custom.push(t);
  if (!saveCustom()) { custom.pop(); alert('Úlohu se nepodařilo uložit (plné úložiště prohlížeče?). Zkus to bez obrázku.'); return; }
  fillSelect(); dlg.close(); setTask(t.id);
};

fillSelect();
const last = lsGet('tzi_automat_last');
setTask(last !== null && (last === '' || allTasks().some(t => t.id === last)) ? last : 'repr');
