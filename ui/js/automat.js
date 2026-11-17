try {
  const th = localStorage.getItem('tzi_theme');
  if (th === 'light' || th === 'dark' || th === 'amoled' || th === 'catppuccin' || th === 'auto') {
    document.documentElement.setAttribute('data-theme', th);
  }
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
const ico = d => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const parseSymbols = text => [...new Set([...String(text)].filter(c => !/[\s,;]/.test(c)))].slice(0, 32);
let task = null, given = false, tab = 'diagram', TABS = [], exTask = null, sim = { word: '', pos: 0 }, RP = null;
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
let editor = null;
const pos = id => editor ? editor.pos(id) : null;
const save = () => editor && lsSet(KEY(), JSON.stringify(editor.model));
function load(alphabet) {
  try {
    const m = safeParseJson(lsGet(KEY()));
    if (m && Array.isArray(m.states) && Array.isArray(m.trans)) return sanitizeModel(m, alphabet);
  } catch (e) { /* nový */ }
  return fresh(alphabet);
}

// ── geometrie hran (sdílená pro interaktivní plátno i náhledy) ───────────────
function edgeGeom(model, pendingEdge, t) {
  const find = id => model.states.find(s => s.id === id);
  const a = find(t.from), b = find(t.to);
  if (!a || !b) return { d: '', lx: 0, ly: 0 };
  if (t.from === t.to) {
    const down = a.y < 110;
    const sy = down ? a.y + R - 4 : a.y - R + 4;
    const cy = down ? a.y + R + 62 : a.y - R - 62;
    return { d: `M ${a.x - 16} ${sy} C ${a.x - 40} ${cy}, ${a.x + 40} ${cy}, ${a.x + 16} ${sy}`, lx: a.x, ly: down ? a.y + R + 46 : a.y - R - 46 };
  }
  const hasBack = t.from !== t.to && (model.trans.some(u => u.from === t.to && u.to === t.from) || (pendingEdge && pendingEdge.from === t.to && pendingEdge.to === t.from));
  const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len, nx = -uy, ny = ux;
  const bend = hasBack ? 34 : 0;
  const cx = (a.x + b.x) / 2 + nx * bend * 2, cy = (a.y + b.y) / 2 + ny * bend * 2;
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

// ── GoF OOP jádro diagramu (Memento, Command, State, Strategy, Facade) ─────────
class DiagramMemento {
  #snapshot;
  constructor(model) { this.#snapshot = DiagramMemento.clone(model); }
  getSnapshot() { return DiagramMemento.clone(this.#snapshot); }
  static clone(m) {
    return {
      alphabet: m.alphabet.slice(),
      states: m.states.map(s => ({ ...s })),
      start: m.start,
      accept: m.accept.slice(),
      trans: m.trans.map(t => ({ ...t, symbols: t.symbols.slice() }))
    };
  }
}

class HistoryManager {
  constructor(limit = 50) { this.limit = limit; this.undoStack = []; this.redoStack = []; }
  clear() { this.undoStack = []; this.redoStack = []; }
  get canUndo() { return this.undoStack.length > 0; }
  get canRedo() { return this.redoStack.length > 0; }
  push(memento) {
    this.undoStack.push(memento);
    if (this.undoStack.length > this.limit) this.undoStack.shift();
    this.redoStack = [];
  }
  undo(originator) {
    if (!this.canUndo) return false;
    this.redoStack.push(originator.createMemento());
    originator.restoreMemento(this.undoStack.pop());
    return true;
  }
  redo(originator) {
    if (!this.canRedo) return false;
    this.undoStack.push(originator.createMemento());
    originator.restoreMemento(this.redoStack.pop());
    return true;
  }
}

class DiagramCommand {
  execute() { return false; }
}
class MutationCommand extends DiagramCommand {
  constructor(fn) { super(); this.fn = fn; }
  execute(ed) { return this.fn(ed) !== false; }
}
class AddStateCommand extends DiagramCommand {
  constructor(x, y) { super(); this.x = x; this.y = y; }
  execute(ed) { return ed.insertStateAt(this.x, this.y); }
}
class PasteCommand extends DiagramCommand {
  execute(ed) { return ed.clipboard.pasteInto(ed); }
}
class DeleteSelectionCommand extends DiagramCommand {
  execute(ed) { return ed.removeSelected(); }
}
class FlipEdgeCommand extends DiagramCommand {
  constructor(index) { super(); this.index = index; }
  execute(ed) { return ed.reverseEdge(this.index); }
}

class Viewport {
  constructor() { this.vw = 800; this.vh = 520; this.x = 0; this.y = 0; this.zoom = 1; }
  viewBoxStr() {
    return `${this.x.toFixed(1)} ${this.y.toFixed(1)} ${(this.vw / this.zoom).toFixed(1)} ${(this.vh / this.zoom).toFixed(1)}`;
  }
  applyTo(svgEl, zoomLabel) {
    svgEl.setAttribute('viewBox', this.viewBoxStr());
    if (zoomLabel) zoomLabel.textContent = `${Math.round(this.zoom * 100)}%`;
  }
  fitContainer(wrapEl) {
    const r = wrapEl.getBoundingClientRect(); if (!r.width || !r.height) return false;
    const next = Math.max(480, Math.round(this.vh * r.width / r.height));
    const diff = next !== this.vw;
    this.vw = next;
    return diff;
  }
  panByPixels(dxPx, dyPx, rect) {
    if (!rect.width || !rect.height) return;
    const w = this.vw / this.zoom, h = this.vh / this.zoom;
    this.x = clamp(this.x - dxPx * (w / rect.width), -600, 1600);
    this.y = clamp(this.y - dyPx * (h / rect.height), -400, 700);
  }
  zoomBy(factor, cx, cy) {
    const prev = this.zoom, next = clamp(Math.round(prev * factor * 100) / 100, 0.4, 2.5);
    if (next === prev) return false;
    const w0 = this.vw / prev, h0 = this.vh / prev, w1 = this.vw / next, h1 = this.vh / next;
    const px = cx !== undefined ? cx : this.x + w0 / 2, py = cy !== undefined ? cy : this.y + h0 / 2;
    this.zoom = next;
    this.x = clamp(px - ((px - this.x) / w0) * w1, -600, 1600);
    this.y = clamp(py - ((py - this.y) / h0) * h1, -400, 700);
    return true;
  }
  reset() { this.x = 0; this.y = 0; this.zoom = 1; }
  fitStates(states) {
    if (!states.length) { this.reset(); return; }
    const xs = states.map(s => s.x), ys = states.map(s => s.y);
    const minX = Math.min(...xs) - 85, maxX = Math.max(...xs) + 85;
    const minY = Math.min(...ys) - 85, maxY = Math.max(...ys) + 150;
    const z = clamp(Math.min(this.vw / Math.max(240, maxX - minX), this.vh / Math.max(200, maxY - minY)), 0.45, 1.35);
    this.zoom = Math.round(z * 100) / 100;
    this.x = clamp((minX + maxX) / 2 - (this.vw / this.zoom) / 2, -600, 1600);
    this.y = clamp((minY + maxY) / 2 - (this.vh / this.zoom) * 0.46, -400, 700);
  }
  centerPoint() {
    return { x: Math.round(this.x + (this.vw / this.zoom) / 2), y: Math.round(this.y + (this.vh / this.zoom) * 0.42) };
  }
  toSvgPoint(svgEl, ev) {
    const p = svgEl.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY;
    const q = p.matrixTransform(svgEl.getScreenCTM().inverse());
    return { x: q.x, y: q.y };
  }
}

class SelectionModel {
  constructor() {
    this.states = new Set();
    this.edgeIndex = null;
    this.pendingEdge = null;
    this.linkFrom = null;
    this.renaming = null;
    this.error = '';
  }
  singleState() { return this.states.size === 1 ? [...this.states][0] : null; }
  hasAny() { return this.states.size > 0 || this.edgeIndex !== null || !!this.pendingEdge; }
  clear() { this.states.clear(); this.edgeIndex = null; this.pendingEdge = null; this.linkFrom = null; this.renaming = null; this.error = ''; }
  selectOnlyState(id) { this.states.clear(); this.states.add(id); this.edgeIndex = null; this.pendingEdge = null; this.renaming = null; this.error = ''; }
  selectEdge(idx) { this.states.clear(); this.linkFrom = null; this.pendingEdge = null; this.renaming = null; this.error = ''; this.edgeIndex = idx; }
  prune(model) {
    const has = id => model.states.some(s => s.id === id);
    for (const id of [...this.states]) if (!has(id)) this.states.delete(id);
    if (this.edgeIndex !== null && !model.trans[this.edgeIndex]) this.edgeIndex = null;
    if (this.renaming && !has(this.renaming)) this.renaming = null;
    if (this.linkFrom && !has(this.linkFrom)) this.linkFrom = null;
  }
}

class DiagramClipboard {
  constructor() { this.payload = null; }
  get hasData() { return !!(this.payload && this.payload.states.length); }
  copy(model, selection) {
    if (!selection.states.size) return false;
    this.payload = {
      states: model.states.filter(s => selection.states.has(s.id)).map(s => ({ id: s.id, x: s.x, y: s.y, acc: model.accept.includes(s.id) })),
      trans: model.trans.filter(t => selection.states.has(t.from) && selection.states.has(t.to)).map(t => ({ from: t.from, to: t.to, symbols: t.symbols.slice() }))
    };
    return true;
  }
  pasteInto(ed) {
    if (!this.hasData) return false;
    if (ed.model.states.length + this.payload.states.length > 64) { alert('Maximální počet stavů je 64.'); return false; }
    const used = new Set(), map = {};
    ed.selection.clear();
    for (const s of this.payload.states) {
      const nid = ed.nextStateId(used); used.add(nid); map[s.id] = nid;
      ed.model.states.push({ id: nid, x: clamp(s.x + 48, 44, 1956), y: clamp(s.y + 48, 40, 960) });
      if (s.acc) ed.model.accept.push(nid);
      ed.selection.states.add(nid);
    }
    for (const t of this.payload.trans) ed.model.trans.push({ from: map[t.from], to: map[t.to], symbols: t.symbols.slice() });
    this.payload.states.forEach(s => { s.x += 48; s.y += 48; });
    ed.setTool('select', true);
    return true;
  }
}

class SvgDiagramRenderer {
  renderInner(mid, interactive, model, selection, viewport, overlays) {
    const safeMid = esc(mid), find = id => model.states.find(s => s.id === id);
    let h = `<defs><marker id="${safeMid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" class="svg-arrow"/></marker>` +
      (interactive ? `<pattern id="grid-${safeMid}" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="12" cy="12" r="1" class="svg-grid-dot"/></pattern>` : '') +
      `</defs>` + (interactive ? `<rect x="-8000" y="-8000" width="16000" height="16000" fill="url(#grid-${safeMid})" pointer-events="none"/>` : '');
    if (interactive && !model.states.length && viewport) {
      const c = viewport.centerPoint();
      h += `<g class="empty-hint"><rect x="${c.x - 150}" y="${c.y - 28}" width="300" height="56" rx="12"/><text x="${c.x}" y="${c.y}">Dvakrát klepni nebo vyber Stav</text></g>`;
    }
    model.trans.forEach((t, i) => {
      const g = edgeGeom(model, interactive ? selection.pendingEdge : null, t), label = t.symbols.join(', '), w = Math.max(24, label.length * 10 + 10);
      h += `<g class="ed${interactive && selection.edgeIndex === i ? ' sel' : ''}" ${interactive ? `data-e="${i}"` : ''}><path d="${g.d}" marker-end="url(#${safeMid})"/>` +
        (interactive ? `<path d="${g.d}" class="svg-hit" marker-end=""/>` : '') +
        `<rect x="${g.lx - w / 2}" y="${g.ly - 11}" width="${w}" height="22" rx="6"/><text x="${g.lx}" y="${g.ly}">${esc(label)}</text></g>`;
    });
    if (interactive && selection.pendingEdge && find(selection.pendingEdge.from) && find(selection.pendingEdge.to)) {
      const g = edgeGeom(model, selection.pendingEdge, selection.pendingEdge);
      h += `<g class="ed pending"><path d="${g.d}" marker-end="url(#${safeMid})"/><rect x="${g.lx - 14}" y="${g.ly - 11}" width="28" height="22" rx="6"/><text x="${g.lx}" y="${g.ly}">?</text></g>`;
    }
    model.states.forEach(s => {
      if (model.start === s.id) h += `<line class="mark" x1="${s.x - R - 46}" y1="${s.y}" x2="${s.x - R - 2}" y2="${s.y}" marker-end="url(#${safeMid})"/>`;
      if (model.accept.includes(s.id)) h += `<line class="mark" x1="${s.x + R}" y1="${s.y}" x2="${s.x + R + 44}" y2="${s.y}" marker-end="url(#${safeMid})"/>`;
      const cls = `st${interactive && selection.states.has(s.id) ? ' sel' : ''}${interactive && selection.linkFrom === s.id ? ' src' : ''}${sim.cur === s.id ? ' cur' : ''}`;
      h += `<g class="${cls}" data-s="${esc(s.id)}">${interactive ? `<circle class="st-hit" cx="${s.x}" cy="${s.y}" r="${R + 14}"/>` : ''}<circle cx="${s.x}" cy="${s.y}" r="${R}"/><text x="${s.x}" y="${s.y}">${esc(S(s.id))}</text></g>`;
    });
    const sid = interactive ? selection.singleState() : null;
    if (interactive && sid && !selection.linkFrom && !overlays.hidePort) {
      const ss = find(sid);
      if (ss) {
        const px = ss.x + 26, py = ss.y < 76 ? ss.y + 26 : ss.y - 26;
        h += `<g class="svg-port" data-port="${esc(ss.id)}"><title>Táhni k dalšímu stavu</title><circle class="port-hit" cx="${px}" cy="${py}" r="22"/><circle class="port-dot" cx="${px}" cy="${py}" r="12"/><text x="${px}" y="${py}">→</text></g>`;
      }
    }
    if (interactive && overlays.rubber) {
      const rb = overlays.rubber;
      h += `<line class="rubber" x1="${rb.x1}" y1="${rb.y1}" x2="${rb.x2}" y2="${rb.y2}"/>`;
    }
    if (interactive && overlays.marquee) {
      const mq = overlays.marquee, mx = Math.min(mq.x1, mq.x2), my = Math.min(mq.y1, mq.y2);
      h += `<rect class="marquee" x="${mx}" y="${my}" width="${Math.abs(mq.x2 - mq.x1)}" height="${Math.abs(mq.y2 - mq.y1)}"/>`;
    }
    return h;
  }
}

function renderWordDiagram() { // diagram pod čtením slova (jen k prohlížení)
  if (!editor) return;
  const w = $('wBoard'), m = editor.model; if (!w) return;
  if (!m.states.length) { w.setAttribute('viewBox', '0 0 600 120'); w.innerHTML = '<text x="300" y="60" class="svg-empty-msg">Diagram je zatím prázdný. Nakresli ho v kroku Diagram.</text>'; return; }
  const xs = m.states.map(s => s.x), ys = m.states.map(s => s.y), pad = 95;
  const x0 = Math.min(...xs) - pad, y0 = Math.min(...ys) - pad - 30;
  w.setAttribute('viewBox', `${x0} ${y0} ${Math.max(360, Math.max(...xs) + pad - x0)} ${Math.max(240, Math.max(...ys) + pad - y0)}`);
  w.innerHTML = editor.renderer.renderInner('arrow2', false, m, editor.selection, null, {});
}

function renderLive() { // tabulka, strom a čtení slova z vlastního návrhu
  if (!$('lTable') || !editor) return;
  const m = editor.model, d = Auto.delta(m);
  let t = '<table><tr><th></th>' + m.alphabet.map(a => `<th>${esc(a)}</th>`).join('') + '</tr>';
  for (const s of m.states) {
    t += `<tr><th>${m.start === s.id ? '→ ' : ''}${m.accept.includes(s.id) ? '← ' : ''}${esc(S(s.id))}</th>`;
    for (const a of m.alphabet) { const c = (d[s.id] && d[s.id][a]) || []; t += `<td class="${!c.length ? 'miss' : c.length > 1 ? 'multi' : ''}">${c.length ? c.map(x => esc(S(x))).join(', ') : '–'}</td>`; }
    t += '</tr>';
  }
  $('lTable').innerHTML = m.states.length ? `<div class="table-wrap">${t}</table></div><p class="hint">Tabulka se plní sama z tvého automatu. → počáteční, ← přijímací, „–“ = chybí přechod.</p>` : '<span class="hint">Zatím žádný stav. V kroku Diagram přidej stavy.</span>';
  $('lTree').innerHTML = treeSvg(m);
  renderTrace();
}

function renderTrace() {
  const out = $('trace'); if (!out || !editor) return;
  const m = editor.model, r = Auto.run(m, sim.word);
  if (!sim.active) { out.textContent = ''; sim.cur = null; svgCur(); return; }
  const k = Math.min(sim.pos, r.steps.length);
  let txt = S(m.start || '?');
  for (let i = 0; i < k; i++) txt += ` –${r.steps[i].read}→ ${S(r.steps[i].to)}`;
  const done = k === sim.word.length || (r.stuck && k === r.steps.length), rest = [...sim.word].slice(k).join('');
  let verdict = '';
  if (r.stuck && k === r.steps.length && sim.pos > r.steps.length) verdict = `<br><b class="verdict-bad">Zaseknuto: ${esc(r.stuck)}</b>`;
  else if (done) verdict = `<br><b class="${r.accepted ? 'verdict-ok' : 'verdict-bad'}">${r.accepted ? 'Přijato ✓' : 'Nepřijato ✗'}</b> (skončil ve stavu ${esc(S(r.state || '?'))})`;
  out.innerHTML = `${esc(txt)}${rest ? `<br><span class="hint">zbývá: ${esc(rest)}</span>` : ''}${verdict}`;
  sim.cur = k === 0 ? m.start : r.steps[k - 1] ? r.steps[k - 1].to : r.state;
  svgCur();
}
function svgCur() { document.querySelectorAll('svg .st').forEach(g => g.classList.toggle('cur', g.dataset.s === sim.cur)); }

const changed = () => editor && editor.notifyChanged(true);

const hasFocusGroup = 'focusGroup' in HTMLElement.prototype;
const tbItems = bar => [...bar.querySelectorAll('button, select, input')].filter(el => !el.hidden && !el.closest('[hidden]'));
function syncRovingToolbar(bar, focusEl) {
  if (!bar) return;
  const items = tbItems(bar);
  if (!items.length || hasFocusGroup) { if (focusEl) focusEl.focus(); return; }
  const target = focusEl && items.includes(focusEl) ? focusEl : (items.find(el => el.tabIndex === 0) || items[0]);
  items.forEach(el => { el.tabIndex = el === target ? 0 : -1; });
  if (focusEl && items.includes(focusEl)) focusEl.focus();
}
function wireRovingToolbar(bar) {
  if (!bar || hasFocusGroup) return;
  syncRovingToolbar(bar);
  bar.addEventListener('focusin', ev => {
    const t = ev.target.closest('button, select, input');
    if (t && bar.contains(t)) tbItems(bar).forEach(el => { el.tabIndex = el === t ? 0 : -1; });
  });
  bar.addEventListener('keydown', ev => {
    if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
    const items = tbItems(bar), i = items.indexOf(ev.target);
    if (i < 0) return;
    const rtl = getComputedStyle(bar).direction === 'rtl';
    const next = ev.key === 'ArrowRight' ? (rtl ? -1 : 1) : ev.key === 'ArrowLeft' ? (rtl ? 1 : -1) : null;
    let dst = -1;
    if (next !== null) dst = (i + next + items.length) % items.length;
    else if (ev.key === 'Home') dst = 0;
    else if (ev.key === 'End') dst = items.length - 1;
    if (dst < 0) return;
    ev.preventDefault();
    items.forEach((el, idx) => { el.tabIndex = idx === dst ? 0 : -1; });
    items[dst].focus();
  });
}

// ── GoF State: nástroje plátna ───────────────────────────────────────────────
class CanvasTool {
  constructor(editorInstance, id) { this.editor = editorInstance; this.id = id; }
  get cursorClass() { return ''; }
  onActivate() { return true; }
  onDeactivate() {}
  onPointerDown() {}
  onPointerMove() {}
  onPointerUp() {}
  onDblClick() {}
  getOverlays() { return {}; }
  renderIdleBar() { return ''; }
}

class MoveTool extends CanvasTool {
  get cursorClass() { return 'mode-move'; }
  onDeactivate() { this.pan = null; this.editor.svg.classList.remove('panning'); }
  onPointerDown(hit, ev) {
    this.pan = { lastX: ev.clientX, lastY: ev.clientY };
    this.editor.capturePointer(ev.pointerId);
    this.editor.svg.classList.add('panning');
  }
  onPointerMove(ev) {
    if (!this.pan) return;
    this.editor.viewport.panByPixels(ev.clientX - this.pan.lastX, ev.clientY - this.pan.lastY, this.editor.wrap.getBoundingClientRect());
    this.pan.lastX = ev.clientX; this.pan.lastY = ev.clientY;
    this.editor.applyView();
  }
  onPointerUp() {
    if (!this.pan) return;
    this.pan = null;
    this.editor.svg.classList.remove('panning');
    this.editor.toolbar.render();
  }
  renderIdleBar() {
    return `<span class="selbar-title">Plátno</span>` +
      `<button type="button" class="btn icon-btn" id="ctxZoomOut" aria-label="Oddálit">${ico('<line x1="5" y1="12" x2="19" y2="12"/>')}</button>` +
      `<button type="button" class="btn zoom-pct" id="ctxZoomReset" title="Obnovit 100 %">${Math.round(this.editor.viewport.zoom * 100)}%</button>` +
      `<button type="button" class="btn icon-btn" id="ctxZoomIn" aria-label="Přiblížit">${ico('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>')}</button>` +
      `<button type="button" class="btn" id="ctxZoomFit" title="Přizpůsobit diagram do okna">Celý</button>` +
      `<span class="selbar-hint">Táhni plátnem</span>`;
  }
}

class SelectTool extends CanvasTool {
  onDeactivate() { this.drag = null; this.marquee = null; this.pendingClick = null; this.linkToFixed = null; }
  onPointerDown(hit, ev, p) {
    const ed = this.editor, sel = ed.selection;
    if (sel.linkFrom && hit.stateId) { this.linkToFixed = { from: sel.linkFrom, to: hit.stateId }; return; }
    if (sel.linkFrom && hit.edgeIndex === null) { this.pendingClick = { type: 'cancelLink', sx: ev.clientX, sy: ev.clientY }; return; }
    if (hit.stateId) {
      const id = hit.stateId, s = ed.pos(id); if (!s) return;
      const ids = (sel.states.has(id) && !ev.shiftKey) ? [...sel.states] : [id];
      const orig = {}; ids.forEach(gid => { const g = ed.pos(gid); if (g) orig[gid] = { x: g.x, y: g.y }; });
      this.drag = { id, shift: ev.shiftKey, ids, orig, ax: s.x, ay: s.y, dx: s.x - p.x, dy: s.y - p.y, sx: ev.clientX, sy: ev.clientY, moved: false, memento: ed.createMemento() };
      ed.capturePointer(ev.pointerId); return;
    }
    if (hit.edgeIndex !== null) { this.pendingClick = { type: 'edge', index: hit.edgeIndex, sx: ev.clientX, sy: ev.clientY }; return; }
    if (sel.pendingEdge) { this.pendingClick = { type: 'clearPending', sx: ev.clientX, sy: ev.clientY }; return; }
    this.marquee = { x1: p.x, y1: p.y, x2: p.x, y2: p.y, sx: ev.clientX, sy: ev.clientY, shift: ev.shiftKey, prev: new Set(sel.states), moved: false };
    ed.capturePointer(ev.pointerId);
  }
  onPointerMove(ev, p) {
    const ed = this.editor, sel = ed.selection;
    if (this.drag) {
      if (!this.drag.moved && Math.hypot(ev.clientX - this.drag.sx, ev.clientY - this.drag.sy) < 6) return;
      this.drag.moved = true;
      const ox = Math.round(p.x + this.drag.dx) - this.drag.ax, oy = Math.round(p.y + this.drag.dy) - this.drag.ay;
      for (const gid of this.drag.ids) {
        const g = ed.pos(gid), o = this.drag.orig[gid]; if (!g || !o) continue;
        g.x = clamp(o.x + ox, 44, 1956); g.y = clamp(o.y + oy, 40, 960);
      }
      ed.render(); return;
    }
    if (this.marquee) {
      if (!this.marquee.moved && Math.hypot(ev.clientX - this.marquee.sx, ev.clientY - this.marquee.sy) < 6) return;
      this.marquee.moved = true; this.marquee.x2 = p.x; this.marquee.y2 = p.y;
      const x0 = Math.min(this.marquee.x1, this.marquee.x2), x1 = Math.max(this.marquee.x1, this.marquee.x2);
      const y0 = Math.min(this.marquee.y1, this.marquee.y2), y1 = Math.max(this.marquee.y1, this.marquee.y2);
      sel.states = this.marquee.shift ? new Set(this.marquee.prev) : new Set();
      for (const s of ed.model.states) if (s.x + R >= x0 && s.x - R <= x1 && s.y + R >= y0 && s.y - R <= y1) sel.states.add(s.id);
      sel.edgeIndex = null; sel.pendingEdge = null; sel.renaming = null; sel.error = '';
      ed.render();
    }
  }
  onPointerUp(ev, canceled) {
    const ed = this.editor, sel = ed.selection;
    if (canceled) {
      if (this.drag && this.drag.moved) ed.restoreMemento(this.drag.memento);
      this.onDeactivate(); ed.render(); return;
    }
    if (this.linkToFixed) { const lk = this.linkToFixed; this.linkToFixed = null; ed.startConnection(lk.from, lk.to); return; }
    if (this.drag) {
      const d = this.drag; this.drag = null;
      sel.renaming = null; sel.error = ''; sel.edgeIndex = null; sel.pendingEdge = null;
      if (d.moved) { if (!sel.states.has(d.id)) sel.selectOnlyState(d.id); ed.history.push(d.memento); save(); }
      else if (d.shift) { if (sel.states.has(d.id)) sel.states.delete(d.id); else sel.states.add(d.id); }
      else sel.selectOnlyState(d.id);
      ed.render(); return;
    }
    if (this.marquee) {
      const mq = this.marquee; this.marquee = null;
      sel.renaming = null; sel.error = '';
      if (mq.moved) { sel.linkFrom = null; sel.edgeIndex = null; sel.pendingEdge = null; }
      else if (sel.hasAny()) sel.clear();
      ed.render(); return;
    }
    if (this.pendingClick) {
      const pc = this.pendingClick; this.pendingClick = null;
      if (Math.hypot(ev.clientX - pc.sx, ev.clientY - pc.sy) > 8) return;
      sel.renaming = null; sel.error = '';
      if (pc.type === 'edge') sel.selectEdge(pc.index);
      else if (pc.type === 'cancelLink') sel.linkFrom = null;
      else if (pc.type === 'clearPending') sel.pendingEdge = null;
      ed.render();
    }
  }
  onDblClick(hit, ev, p) {
    if (hit.stateId) {
      if (Date.now() - this.editor.lastAddedAt > 450) {
        this.editor.selection.selectOnlyState(hit.stateId);
        this.editor.openRename(hit.stateId);
      }
      return;
    }
    if (hit.edgeIndex === null) this.editor.execute(new AddStateCommand(p.x, p.y));
  }
  getOverlays() {
    return {
      hidePort: !!(this.drag && this.drag.moved) || !!this.marquee,
      marquee: this.marquee && this.marquee.moved ? this.marquee : null
    };
  }
  renderIdleBar() {
    const hasStates = this.editor.model.states.length > 0, canPaste = this.editor.clipboard.hasData;
    return `<span class="selbar-title">Výběr</span>` +
      `<button type="button" class="btn" id="selAll"${hasStates ? '' : ' disabled'}>Select all</button>` +
      `<button type="button" class="btn" id="selCopy" disabled>Copy</button>` +
      `<button type="button" class="btn" id="selPaste"${canPaste ? '' : ' disabled'}>Paste</button>` +
      `<button type="button" class="btn danger" id="selDel" disabled>Delete</button>`;
  }
}

class StateTool extends CanvasTool {
  get cursorClass() { return 'mode-state'; }
  onDeactivate() { this.pending = null; }
  onPointerDown(hit, ev, p) { this.pending = { hit, p, sx: ev.clientX, sy: ev.clientY }; }
  onPointerUp(ev, canceled) {
    const pd = this.pending; this.pending = null;
    if (canceled || !pd || Math.hypot(ev.clientX - pd.sx, ev.clientY - pd.sy) > 8) return;
    if (pd.hit.stateId) { this.editor.selection.selectOnlyState(pd.hit.stateId); this.editor.render(); }
    else this.editor.execute(new AddStateCommand(pd.p.x, pd.p.y));
  }
  onDblClick(hit, ev, p) {
    if (!hit.stateId && hit.edgeIndex === null) this.editor.execute(new AddStateCommand(p.x, p.y));
  }
  renderIdleBar() {
    return `<span class="selbar-hint">Klepni na plátno pro vložení stavu</span>` +
      `<button type="button" class="btn" id="addCenterState">+ Přidat stav</button>` +
      `<button type="button" class="btn" id="cancelTool">Hotovo</button>`;
  }
}

class EdgeTool extends CanvasTool {
  get cursorClass() { return 'mode-edge'; }
  onDeactivate() { this.linkDrag = null; this.emptyClick = null; }
  onActivate(prevSel) {
    if (!prevSel.linkFrom && prevSel.singleState()) {
      prevSel.linkFrom = prevSel.singleState();
      prevSel.states.clear(); prevSel.edgeIndex = null; prevSel.pendingEdge = null;
    }
    return true;
  }
  beginPortDrag(from, ev, p) {
    const s = this.editor.pos(from); if (!s) return;
    this.linkDrag = { from, x1: s.x, y1: s.y, x2: p.x, y2: p.y, sx: ev.clientX, sy: ev.clientY, moved: false };
    this.editor.capturePointer(ev.pointerId);
  }
  onPointerDown(hit, ev, p) {
    const sel = this.editor.selection;
    if (hit.stateId) {
      if (sel.linkFrom) { this.linkDrag = { from: sel.linkFrom, toFixed: hit.stateId }; return; }
      this.beginPortDrag(hit.stateId, ev, p); return;
    }
    this.emptyClick = { sx: ev.clientX, sy: ev.clientY };
  }
  onPointerMove(ev, p) {
    if (!this.linkDrag || this.linkDrag.toFixed) return;
    if (!this.linkDrag.moved && Math.hypot(ev.clientX - this.linkDrag.sx, ev.clientY - this.linkDrag.sy) < 6) return;
    this.linkDrag.moved = true; this.linkDrag.x2 = p.x; this.linkDrag.y2 = p.y;
    this.editor.render();
  }
  onPointerUp(ev, canceled) {
    const ed = this.editor, sel = ed.selection;
    if (canceled) { this.onDeactivate(); ed.render(); return; }
    if (this.linkDrag) {
      const ld = this.linkDrag; this.linkDrag = null;
      if (ld.toFixed) { ed.startConnection(ld.from, ld.toFixed); return; }
      if (ld.moved) {
        const p = ed.viewport.toSvgPoint(ed.svg, ev);
        const target = ed.model.states.find(s => Math.hypot(s.x - p.x, s.y - p.y) <= R + 14);
        if (target) ed.startConnection(ld.from, target.id);
        else ed.render();
        return;
      }
      sel.clear(); sel.linkFrom = ld.from; ed.render(); return;
    }
    if (this.emptyClick) {
      const ec = this.emptyClick; this.emptyClick = null;
      if (Math.hypot(ev.clientX - ec.sx, ev.clientY - ec.sy) <= 8) { sel.linkFrom = null; sel.pendingEdge = null; ed.render(); }
    }
  }
  getOverlays() {
    const moved = !!(this.linkDrag && this.linkDrag.moved);
    return { hidePort: moved, rubber: moved ? this.linkDrag : null };
  }
  renderIdleBar() {
    return `<span class="selbar-hint">Táhni mezi stavy nebo klepni na výchozí</span><button type="button" class="btn" id="cancelTool">Zrušit</button>`;
  }
}

class RoleTool extends CanvasTool {
  constructor(editorInstance, id, role, hint) { super(editorInstance, id); this.role = role; this.hint = hint; }
  onDeactivate() { this.pending = null; }
  onActivate(prevSel) {
    if (this.role === 'start' && prevSel.singleState()) { this.editor.applyRoleToState('start', prevSel.singleState()); return false; }
    if (this.role === 'acc' && prevSel.states.size > 0) { this.editor.toggleAcceptSet([...prevSel.states]); return false; }
    return true;
  }
  onPointerDown(hit, ev) { if (hit.stateId) this.pending = { id: hit.stateId, sx: ev.clientX, sy: ev.clientY }; }
  onPointerUp(ev, canceled) {
    const pd = this.pending; this.pending = null;
    if (!canceled && pd && Math.hypot(ev.clientX - pd.sx, ev.clientY - pd.sy) <= 8) this.editor.applyRoleToState(this.role, pd.id);
  }
  renderIdleBar() { return `<span class="selbar-hint">${this.hint}</span><button type="button" class="btn" id="cancelTool">Hotovo</button>`; }
}

class EraseTool extends CanvasTool {
  get cursorClass() { return 'mode-erase'; }
  onDeactivate() { this.pending = null; }
  onActivate(prevSel) {
    if (prevSel.hasAny()) { this.editor.execute(new DeleteSelectionCommand()); return false; }
    return true;
  }
  onPointerDown(hit, ev) {
    if (hit.stateId) this.pending = { type: 'state', id: hit.stateId, sx: ev.clientX, sy: ev.clientY };
    else if (hit.edgeIndex !== null) this.pending = { type: 'edge', idx: hit.edgeIndex, sx: ev.clientX, sy: ev.clientY };
  }
  onPointerUp(ev, canceled) {
    const pd = this.pending; this.pending = null;
    if (canceled || !pd || Math.hypot(ev.clientX - pd.sx, ev.clientY - pd.sy) > 8) return;
    if (pd.type === 'state') this.editor.removeState(pd.id);
    else this.editor.removeEdge(pd.idx);
  }
  renderIdleBar() { return `<span class="selbar-hint">Klepni na stav nebo šipku ke smazání</span><button type="button" class="btn" id="cancelTool">Hotovo</button>`; }
}

// ── GoF Strategy: kontextová podnabídka v #selBar ───────────────────────────
class ContextToolbar {
  constructor(editorInstance, barEl) {
    this.editor = editorInstance;
    this.bar = barEl;
    this.strategies = [
      {
        matches: ed => !!ed.selection.renaming,
        render: ed => {
          const s = ed.pos(ed.selection.renaming);
          return `<span class="selbar-title">Název ${esc(S(s.id))}</span>` +
            `<input type="text" id="renInput" class="selbar-rename" maxlength="8" value="${esc(s.id)}" autocomplete="off" aria-label="Nový název stavu">` +
            `<button type="button" class="btn primary" id="renSave">Uložit</button>` +
            `<button type="button" class="btn" id="renCancel">Zrušit</button>` +
            (ed.selection.error ? `<span class="status bad">${esc(ed.selection.error)}</span>` : '');
        }
      },
      {
        matches: ed => !!ed.selection.linkFrom,
        render: ed => `<span class="selbar-title">Šipka z ${esc(S(ed.selection.linkFrom))} → klepni na cíl</span><button type="button" class="btn" id="selCancelLink">Zrušit</button>`
      },
      {
        matches: ed => !!(ed.selection.pendingEdge || (ed.selection.edgeIndex !== null && ed.model.trans[ed.selection.edgeIndex])),
        render: ed => {
          const sel = ed.selection, edge = sel.pendingEdge || ed.model.trans[sel.edgeIndex], syms = sel.pendingEdge ? [] : edge.symbols;
          return `<span class="selbar-title">${esc(S(edge.from))} → ${esc(S(edge.to))}</span>` +
            ed.model.alphabet.map(a => `<button type="button" class="btn sym" data-sym="${esc(a)}" aria-pressed="${syms.includes(a)}">${esc(a)}</button>`).join('') +
            (ed.model.alphabet.length > 8 ? `<input type="text" id="edgeSymInput" class="selbar-rename" maxlength="32" value="${esc(syms.join(', '))}" autocomplete="off" aria-label="Znaky přechodu"><button type="button" class="btn" id="edgeSymApply">Použít</button>` : '') +
            (edge.from !== edge.to ? `<button type="button" class="btn" id="edgeFlip" title="Otočit směr šipky">${ico('<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>')}Otočit</button>` : '') +
            (sel.pendingEdge ? `<button type="button" class="btn" id="edgeDiscard">Zrušit</button>` : `<button type="button" class="btn danger" id="edgeDel">${ico('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>')}Smazat</button>`) +
            (sel.error ? `<span class="status bad">${esc(sel.error)}</span>` : '');
        }
      },
      {
        matches: ed => !!ed.selection.singleState(),
        render: ed => {
          const id = ed.selection.singleState();
          return `<span class="selbar-title">Stav ${esc(S(id))}</span>` +
            `<button type="button" class="btn" id="stStart" aria-pressed="${ed.model.start === id}" title="Počáteční stav (vstup)">${ico('<line x1="3" y1="12" x2="13" y2="12"/><polyline points="9 8 13 12 9 16"/><circle cx="17.5" cy="12" r="3.5"/>')}Start</button>` +
            `<button type="button" class="btn" id="stAcc" aria-pressed="${ed.model.accept.includes(id)}" title="Přijímací stav (výstup)">${ico('<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="5"/>')}End</button>` +
            `<button type="button" class="btn" id="stLink" title="Přidat přechod (šipka)">${ico('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="13 6 19 12 13 18"/>')}Step</button>` +
            `<button type="button" class="btn" id="stRen" title="Přejmenovat stav">${ico('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>')}Název</button>` +
            `<button type="button" class="btn" id="stCopy" title="Kopírovat (Ctrl+C)">${ico('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>')}Copy</button>` +
            `<button type="button" class="btn danger" id="stDel" title="Smazat (Delete)">${ico('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>')}Delete</button>`;
        }
      },
      {
        matches: ed => ed.selection.states.size > 1,
        render: ed => `<span class="selbar-title">Vybráno: ${ed.selection.states.size}</span>` +
          `<button type="button" class="btn" id="selAll">Select all</button>` +
          `<button type="button" class="btn" id="selCopy">Copy</button>` +
          `<button type="button" class="btn" id="selPaste"${ed.clipboard.hasData ? '' : ' disabled'}>Paste</button>` +
          `<button type="button" class="btn" id="selAccAll">End ±</button>` +
          `<button type="button" class="btn danger" id="selDel">Delete</button>` +
          `<button type="button" class="btn" id="selNone">Zrušit</button>`
      }
    ];
    this.bindEvents();
  }
  render() {
    const bar = this.bar; if (!bar) return;
    const act = document.activeElement, hadFocus = !!(act && bar.contains(act));
    const prevId = hadFocus ? act.id : '', prevSym = hadFocus && act.dataset ? act.dataset.sym : undefined;
    this.editor.selection.prune(this.editor.model);
    const strat = this.strategies.find(s => s.matches(this.editor));
    const html = strat ? strat.render(this.editor) : this.editor.activeTool.renderIdleBar();
    if (!html) { bar.hidden = true; bar.innerHTML = ''; return; }
    bar.innerHTML = html;
    bar.hidden = false;
    let focusTarget = null;
    if (hadFocus) {
      if (prevSym !== undefined) focusTarget = tbItems(bar).find(el => el.dataset.sym === prevSym) || null;
      else if (prevId) focusTarget = $(prevId);
    }
    syncRovingToolbar(bar, focusTarget);
  }
  bindEvents() {
    const ed = this.editor;
    const actions = {
      selCancelLink: () => { ed.selection.linkFrom = null; ed.setTool('select', true); },
      cancelTool: () => { ed.selection.linkFrom = null; ed.setTool('select', true); },
      edgeDiscard: () => { ed.selection.pendingEdge = null; ed.selection.error = ''; ed.render(); },
      edgeFlip: () => ed.execute(new FlipEdgeCommand(ed.selection.edgeIndex)),
      edgeDel: () => ed.selection.edgeIndex !== null && ed.removeEdge(ed.selection.edgeIndex),
      edgeSymApply: () => { const i = $('edgeSymInput'); if (i) ed.applyEdgeText(i.value); },
      renSave: () => { const i = $('renInput'); if (i && ed.selection.renaming) ed.applyRename(ed.selection.renaming, i.value); },
      renCancel: () => { ed.selection.renaming = null; ed.selection.error = ''; this.render(); },
      selAll: () => { ed.model.states.forEach(s => ed.selection.states.add(s.id)); ed.selection.edgeIndex = null; ed.selection.pendingEdge = null; ed.selection.renaming = null; ed.render(); },
      selNone: () => { ed.selection.clear(); ed.render(); },
      selCopy: () => ed.copySelection(),
      stCopy: () => ed.copySelection(),
      selPaste: () => ed.execute(new PasteCommand()),
      selDel: () => ed.execute(new DeleteSelectionCommand()),
      stDel: () => ed.execute(new DeleteSelectionCommand()),
      selAccAll: () => ed.toggleAcceptSet([...ed.selection.states]),
      addCenterState: () => { const pt = ed.freeSpot(); ed.execute(new AddStateCommand(pt.x, pt.y)); },
      ctxZoomOut: () => ed.zoomBy(0.8),
      ctxZoomIn: () => ed.zoomBy(1.25),
      ctxZoomReset: () => ed.resetZoom(),
      ctxZoomFit: () => ed.fitToStates(),
      stStart: () => { const id = ed.selection.singleState(); if (id) ed.applyRoleToState('start', id); },
      stAcc: () => { const id = ed.selection.singleState(); if (id) ed.applyRoleToState('acc', id); },
      stLink: () => { const id = ed.selection.singleState(); if (id) { ed.selection.linkFrom = id; ed.selection.states.clear(); ed.setTool('edge', true); } },
      stRen: () => { const id = ed.selection.singleState(); if (id) ed.openRename(id); }
    };
    this.bar.addEventListener('click', ev => {
      const b = ev.target.closest('button'); if (!b || b.disabled) return;
      if (b.dataset.sym !== undefined) { ed.toggleEdgeSymbol(b.dataset.sym); return; }
      if (actions[b.id]) actions[b.id]();
    });
    this.bar.addEventListener('keydown', ev => {
      if (ev.target.id === 'renInput' && ed.selection.renaming) {
        if (ev.key === 'Enter') ed.applyRename(ed.selection.renaming, ev.target.value);
        else if (ev.key === 'Escape') { ed.selection.renaming = null; ed.selection.error = ''; this.render(); }
      } else if (ev.target.id === 'edgeSymInput' && ev.key === 'Enter') {
        ed.applyEdgeText(ev.target.value);
      }
    });
  }
}

// ── GoF Facade + Originator + State Context: editor automatu ─────────────────
class DiagramEditor {
  constructor() {
    this.svg = svg;
    this.wrap = $('boardWrap');
    this.model = fresh(['0', '1']);
    this.viewport = new Viewport();
    this.history = new HistoryManager(50);
    this.selection = new SelectionModel();
    this.clipboard = new DiagramClipboard();
    this.renderer = new SvgDiagramRenderer();
    this.tools = {
      move: new MoveTool(this, 'move'),
      select: new SelectTool(this, 'select'),
      state: new StateTool(this, 'state'),
      start: new RoleTool(this, 'start', 'start', 'Klepni na počáteční stav'),
      acc: new RoleTool(this, 'acc', 'acc', 'Klepni na přijímací stav'),
      edge: new EdgeTool(this, 'edge'),
      erase: new EraseTool(this, 'erase')
    };
    this.activeTool = this.tools.select;
    this.toolbar = new ContextToolbar(this, $('selBar'));
    this.activePointerId = null;
    this.spacePan = false;
    this.panOverride = false;
    this.portOverride = false;
    this.lastAddedAt = 0;
    this.needsFit = false;
    this.bindEvents();
  }
  pos(id) { return this.model.states.find(s => s.id === id); }
  createMemento() { return new DiagramMemento(this.model); }
  restoreMemento(memento) { this.model = memento.getSnapshot(); this.selection.prune(this.model); }
  execute(cmd) {
    const before = this.createMemento();
    if (!cmd.execute(this)) return false;
    this.history.push(before);
    this.notifyChanged(true);
    return true;
  }
  undo() { if (this.history.undo(this)) { this.selection.clear(); this.notifyChanged(true); } }
  redo() { if (this.history.redo(this)) { this.selection.clear(); this.notifyChanged(true); } }
  notifyChanged(persist = true) {
    if (persist) save();
    sim.active = false; sim.cur = null;
    this.render();
  }
  persist() { save(); }
  applyView() { this.viewport.applyTo(this.svg, $('zoomReset')); }
  zoomBy(factor, cx, cy) { if (this.viewport.zoomBy(factor, cx, cy)) { this.applyView(); this.toolbar.render(); } }
  resetZoom() { this.viewport.reset(); this.applyView(); this.toolbar.render(); }
  fitToStates() { this.viewport.fitStates(this.model.states); this.applyView(); this.toolbar.render(); }
  nextStateId(used) { let i = 0; while (this.pos('q' + i) || (used && used.has('q' + i))) i++; return 'q' + i; }
  freeSpot() {
    const cols = Math.max(2, Math.floor((this.viewport.vw - 120) / 130));
    for (let i = 0; i < 64; i++) {
      const c = i % cols, r = Math.floor(i / cols);
      const x = 90 + c * 130 + (r % 2 ? 40 : 0), y = 90 + r * 110;
      if (x > this.viewport.vw - 50 || y > 470) break;
      if (!this.model.states.some(s => Math.hypot(s.x - x, s.y - y) < 76)) return { x, y };
    }
    const ctr = this.viewport.centerPoint();
    return { x: Math.round(ctr.x + (this.model.states.length * 37 % 140) - 70), y: Math.round(ctr.y + (this.model.states.length * 53 % 120) - 60) };
  }
  insertStateAt(x, y) {
    if (this.model.states.length >= 64) { alert('Maximální počet stavů je 64.'); return false; }
    const id = this.nextStateId();
    this.model.states.push({ id, x: clamp(Math.round(x), 44, 1956), y: clamp(Math.round(y), 40, 960) });
    if (!this.model.start) this.model.start = id;
    this.lastAddedAt = Date.now();
    this.selection.selectOnlyState(id);
    return true;
  }
  removeState(id) {
    return this.execute(new MutationCommand(ed => {
      if (!ed.pos(id)) return false;
      ed.model.states = ed.model.states.filter(s => s.id !== id);
      ed.model.trans = ed.model.trans.filter(t => t.from !== id && t.to !== id);
      ed.model.accept = ed.model.accept.filter(x => x !== id);
      if (ed.model.start === id) ed.model.start = null;
      ed.selection.clear();
    }));
  }
  removeEdge(idx) {
    return this.execute(new MutationCommand(ed => {
      if (!ed.model.trans[idx]) return false;
      ed.model.trans.splice(idx, 1);
      ed.selection.clear();
    }));
  }
  removeSelected() {
    const sel = this.selection;
    if (sel.states.size) {
      const dead = new Set(sel.states);
      this.model.states = this.model.states.filter(s => !dead.has(s.id));
      this.model.trans = this.model.trans.filter(t => !dead.has(t.from) && !dead.has(t.to));
      this.model.accept = this.model.accept.filter(x => !dead.has(x));
      if (dead.has(this.model.start)) this.model.start = null;
      sel.clear();
      return true;
    }
    if (sel.edgeIndex !== null && this.model.trans[sel.edgeIndex]) {
      this.model.trans.splice(sel.edgeIndex, 1);
      sel.clear();
      return true;
    }
    if (sel.pendingEdge) { sel.pendingEdge = null; this.render(); return false; }
    return false;
  }
  reverseEdge(idx) {
    const sel = this.selection;
    if (sel.pendingEdge) { sel.pendingEdge = { from: sel.pendingEdge.to, to: sel.pendingEdge.from }; this.render(); return false; }
    const e = this.model.trans[idx]; if (!e || e.from === e.to) return false;
    const rev = this.model.trans.findIndex((t, i) => i !== idx && t.from === e.to && t.to === e.from);
    if (rev >= 0) {
      this.model.trans[rev].symbols = [...new Set([...this.model.trans[rev].symbols, ...e.symbols])].sort();
      this.model.trans.splice(idx, 1);
      sel.edgeIndex = rev > idx ? rev - 1 : rev;
    } else {
      const tmp = e.from; e.from = e.to; e.to = tmp;
    }
    return true;
  }
  startConnection(from, to) {
    this.selection.clear();
    const idx = this.model.trans.findIndex(t => t.from === from && t.to === to);
    if (idx >= 0) this.selection.edgeIndex = idx;
    else this.selection.pendingEdge = { from, to };
    this.render();
  }
  toggleEdgeSymbol(sym) {
    if (!this.model.alphabet.includes(sym)) return;
    const sel = this.selection; sel.error = '';
    this.execute(new MutationCommand(ed => {
      if (sel.pendingEdge) {
        const { from, to } = sel.pendingEdge; sel.pendingEdge = null;
        const ex = ed.model.trans.findIndex(t => t.from === from && t.to === to);
        if (ex >= 0) {
          if (!ed.model.trans[ex].symbols.includes(sym)) ed.model.trans[ex].symbols = [...ed.model.trans[ex].symbols, sym].sort();
          sel.edgeIndex = ex;
        } else {
          ed.model.trans.push({ from, to, symbols: [sym] });
          sel.edgeIndex = ed.model.trans.length - 1;
        }
        return true;
      }
      if (sel.edgeIndex === null || !ed.model.trans[sel.edgeIndex]) return false;
      const t = ed.model.trans[sel.edgeIndex];
      if (t.symbols.includes(sym)) {
        if (t.symbols.length === 1) { sel.pendingEdge = { from: t.from, to: t.to }; ed.model.trans.splice(sel.edgeIndex, 1); sel.edgeIndex = null; return true; }
        t.symbols = t.symbols.filter(x => x !== sym);
      } else {
        t.symbols = [...t.symbols, sym].sort();
      }
      return true;
    }));
  }
  applyEdgeText(text) {
    const syms = parseSymbols(text), bad = syms.filter(a => !this.model.alphabet.includes(a));
    if (bad.length) { this.selection.error = `Mimo abecedu: ${bad.join(', ')}`; this.toolbar.render(); return; }
    this.selection.error = '';
    const sel = this.selection, edge = sel.pendingEdge || (sel.edgeIndex !== null ? this.model.trans[sel.edgeIndex] : null);
    if (!edge) return;
    this.execute(new MutationCommand(ed => {
      if (!syms.length) {
        if (sel.pendingEdge) { sel.pendingEdge = null; return false; }
        sel.pendingEdge = { from: edge.from, to: edge.to }; ed.model.trans.splice(sel.edgeIndex, 1); sel.edgeIndex = null; return true;
      }
      if (sel.pendingEdge) {
        const { from, to } = sel.pendingEdge; sel.pendingEdge = null;
        ed.model.trans.push({ from, to, symbols: syms.sort() }); sel.edgeIndex = ed.model.trans.length - 1;
      } else edge.symbols = syms.sort();
      return true;
    }));
  }
  applyRoleToState(role, id) {
    if (!this.pos(id)) return;
    this.execute(new MutationCommand(ed => {
      if (role === 'start') ed.model.start = ed.model.start === id ? null : id;
      else ed.model.accept = ed.model.accept.includes(id) ? ed.model.accept.filter(x => x !== id) : [...ed.model.accept, id];
      ed.selection.selectOnlyState(id);
    }));
  }
  toggleAcceptSet(ids) {
    if (!ids.length) return;
    this.execute(new MutationCommand(ed => {
      const allAcc = ids.every(id => ed.model.accept.includes(id));
      ed.model.accept = allAcc ? ed.model.accept.filter(x => !ids.includes(x)) : [...new Set([...ed.model.accept, ...ids])];
    }));
  }
  applyRename(id, nextName) {
    const s = this.pos(id); if (!s) return;
    const v = String(nextName).trim();
    if (v === id) { this.selection.renaming = null; this.selection.error = ''; this.toolbar.render(); return; }
    if (!/^[A-Za-z0-9_′']{1,8}$/.test(v) || RESERVED_IDS.has(v)) { this.selection.error = 'Název: 1–8 znaků (písmena, čísla, _).'; this.toolbar.render(); return; }
    if (this.pos(v)) { this.selection.error = `Stav ${v} už existuje.`; this.toolbar.render(); return; }
    this.execute(new MutationCommand(ed => {
      const tgt = ed.pos(id); tgt.id = v;
      ed.model.trans.forEach(t => { if (t.from === id) t.from = v; if (t.to === id) t.to = v; });
      ed.model.accept = ed.model.accept.map(x => x === id ? v : x);
      if (ed.model.start === id) ed.model.start = v;
      ed.selection.states.delete(id); ed.selection.states.add(v);
      ed.selection.renaming = null; ed.selection.error = '';
    }));
  }
  openRename(id) {
    if (!this.pos(id)) return;
    this.selection.renaming = id; this.selection.error = ''; this.toolbar.render();
    const inp = $('renInput'); if (inp) { inp.focus(); inp.select(); }
  }
  copySelection() { if (this.clipboard.copy(this.model, this.selection)) this.toolbar.render(); }
  setTool(nextId, skipActivate = false) {
    const nextTool = this.tools[nextId]; if (!nextTool) return;
    if (!skipActivate) {
      const ok = nextTool.onActivate(this.selection);
      if (ok === false) return;
    }
    this.activeTool.onDeactivate();
    this.activeTool = nextTool;
    if (nextId === 'move' || nextId === 'state') this.selection.clear();
    if (nextId !== 'edge') this.selection.linkFrom = null;
    this.selection.renaming = null; this.selection.error = '';
    if (!skipActivate) this.render();
  }
  hitTest(target) {
    const port = target.closest('[data-port]'), st = target.closest('[data-s]'), ed = target.closest('[data-e]');
    return { portFrom: port ? port.dataset.port : null, stateId: st ? st.dataset.s : null, edgeIndex: ed ? +ed.dataset.e : null };
  }
  capturePointer(pid) { this.activePointerId = pid; try { this.svg.setPointerCapture(pid); } catch (e) { /* nic */ } }
  releasePointer(pid) {
    if (this.activePointerId !== pid) return;
    try { this.svg.releasePointerCapture(pid); } catch (e) { /* nic */ }
    this.activePointerId = null;
  }
  fitBoard() {
    const changedWidth = this.viewport.fitContainer(this.wrap);
    this.applyView();
    if (changedWidth && tab === 'diagram' && !this.model.states.length) this.render();
  }
  onShowDiagram() {
    this.fitBoard();
    if (this.needsFit) { this.viewport.fitStates(this.model.states); this.needsFit = false; }
    this.render();
  }
  resetTask(model) {
    this.model = model;
    this.selection.clear();
    this.history.clear();
    this.activeTool = this.tools.select;
    this.needsFit = model.states.length > 0;
    if (!this.needsFit) { this.viewport.reset(); this.applyView(); }
  }
  render() {
    const chk = Auto.check(this.model);
    const id = this.activeTool.id;
    this.svg.classList.toggle('mode-move', id === 'move' || this.spacePan);
    this.svg.classList.toggle('mode-state', id === 'state');
    this.svg.classList.toggle('mode-edge', id === 'edge' || !!this.selection.linkFrom);
    this.svg.classList.toggle('mode-connect', id === 'edge' || !!this.selection.linkFrom);
    this.svg.classList.toggle('mode-erase', id === 'erase');
    document.querySelectorAll('#dock [data-tool]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tool === id)));
    if ($('undoBtn')) $('undoBtn').disabled = !this.history.canUndo;
    if ($('redoBtn')) $('redoBtn').disabled = !this.history.canRedo;
    this.applyView();
    const overlays = this.portOverride ? this.tools.edge.getOverlays() : this.activeTool.getOverlays();
    this.svg.innerHTML = this.renderer.renderInner('arrow', true, this.model, this.selection, this.viewport, overlays);
    this.toolbar.render();
    renderWordDiagram(); syncDelta();
    const st = $('dStatus');
    if (!this.model.states.length) { st.className = 'status'; st.textContent = ''; }
    else if (chk.ok) { st.className = 'status ok'; st.textContent = 'Deterministický a úplný automat'; }
    else { st.className = 'status ' + (chk.multi.length ? 'bad' : 'warn'); st.textContent = chk.problems.map(p => p.text).join(' '); }
    if (!given) renderLive();
  }
  bindEvents() {
    new ResizeObserver(() => this.fitBoard()).observe(this.wrap);
    wireRovingToolbar($('dock'));
    wireRovingToolbar($('selBar'));
    wireRovingToolbar(document.querySelector('.canvas-hud-top .hud-pill'));
    this.svg.addEventListener('pointerdown', ev => {
      const hit = this.hitTest(ev.target), p = this.viewport.toSvgPoint(this.svg, ev);
      if (ev.button === 1 || (ev.button === 0 && this.spacePan)) {
        ev.preventDefault(); this.panOverride = true; this.tools.move.onPointerDown(hit, ev, p); return;
      }
      if (ev.button > 0) return;
      if (hit.portFrom) { this.portOverride = true; this.tools.edge.beginPortDrag(hit.portFrom, ev, p); return; }
      this.activeTool.onPointerDown(hit, ev, p);
    });
    this.svg.addEventListener('pointermove', ev => {
      const p = this.viewport.toSvgPoint(this.svg, ev);
      if (this.panOverride) { this.tools.move.onPointerMove(ev, p); return; }
      if (this.portOverride) { this.tools.edge.onPointerMove(ev, p); return; }
      this.activeTool.onPointerMove(ev, p);
    });
    const finishPointer = (ev, canceled) => {
      this.releasePointer(ev.pointerId);
      if (this.panOverride) { this.panOverride = false; this.tools.move.onPointerUp(ev, canceled); return; }
      if (this.portOverride) { this.portOverride = false; this.tools.edge.onPointerUp(ev, canceled); return; }
      this.activeTool.onPointerUp(ev, canceled);
    };
    this.svg.addEventListener('pointerup', ev => finishPointer(ev, false));
    this.svg.addEventListener('pointercancel', ev => finishPointer(ev, true));
    this.svg.addEventListener('wheel', ev => {
      if (tab !== 'diagram' || (!ev.ctrlKey && !ev.metaKey)) return;
      ev.preventDefault();
      const p = this.viewport.toSvgPoint(this.svg, ev);
      this.zoomBy(ev.deltaY < 0 ? 1.12 : 0.89, p.x, p.y);
    }, { passive: false });
    this.svg.addEventListener('dblclick', ev => {
      const hit = this.hitTest(ev.target), p = this.viewport.toSvgPoint(this.svg, ev);
      this.activeTool.onDblClick(hit, ev, p);
    });
    document.addEventListener('keydown', ev => {
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(ev.target.tagName) || tab !== 'diagram') return;
      const mod = ev.ctrlKey || ev.metaKey;
      if (mod && ev.key.toLowerCase() === 'z') { ev.preventDefault(); if (ev.shiftKey) this.redo(); else this.undo(); return; }
      if (mod && ev.key.toLowerCase() === 'y') { ev.preventDefault(); this.redo(); return; }
      if (mod && ev.key.toLowerCase() === 'a') { ev.preventDefault(); this.setTool('select', true); this.model.states.forEach(s => this.selection.states.add(s.id)); this.selection.edgeIndex = null; this.selection.pendingEdge = null; this.render(); return; }
      if (mod && ev.key.toLowerCase() === 'c') { if (this.selection.states.size) { ev.preventDefault(); this.copySelection(); } return; }
      if (mod && ev.key.toLowerCase() === 'v') { if (this.clipboard.hasData) { ev.preventDefault(); this.execute(new PasteCommand()); } return; }
      if (ev.key === ' ') { ev.preventDefault(); if (!this.spacePan) { this.spacePan = true; this.render(); } return; }
      if (ev.key === 'Escape') { this.selection.clear(); this.setTool('select'); return; }
      if (ev.key === 'Delete' || ev.key === 'Backspace') { this.execute(new DeleteSelectionCommand()); return; }
      if (!mod && (this.selection.pendingEdge || (this.selection.edgeIndex !== null && this.model.trans[this.selection.edgeIndex])) && this.model.alphabet.includes(ev.key)) {
        ev.preventDefault(); this.toggleEdgeSymbol(ev.key); return;
      }
      if (!mod) {
        const k = ev.key.toLowerCase();
        const keyMap = { '1': 'move', m: 'move', '2': 'select', v: 'select', '3': 'state', s: 'state', '4': 'start', '5': 'acc', '6': 'edge', a: 'edge', '7': 'erase', x: 'erase' };
        if (keyMap[k]) { ev.preventDefault(); this.setTool(keyMap[k]); return; }
        if (k === '=' || k === '+') this.zoomBy(1.2);
        else if (k === '-') this.zoomBy(0.83);
        else if (k === '0') this.fitToStates();
      }
    });
    document.addEventListener('keyup', ev => {
      if (ev.key === ' ' && this.spacePan) { this.spacePan = false; if (tab === 'diagram') this.render(); }
    });
    $('dock').addEventListener('click', ev => {
      const b = ev.target.closest('[data-tool]'); if (b) this.setTool(b.dataset.tool);
    });
    $('undoBtn').onclick = () => this.undo();
    $('redoBtn').onclick = () => this.redo();
    $('zoomIn').onclick = () => this.zoomBy(1.25);
    $('zoomOut').onclick = () => this.zoomBy(0.8);
    $('zoomReset').onclick = () => this.resetZoom();
    $('zoomFit').onclick = () => this.fitToStates();
    $('clear').onclick = () => {
      if (this.model.states.length && !confirm('Smazat celý návrh?')) return;
      this.execute(new MutationCommand(ed => {
        ed.model = fresh(ed.model.alphabet); ed.selection.clear(); ed.viewport.reset();
        exTask = null; $('ex').value = ''; lsSet('tzi_automat_ex', ''); renderZad();
      }));
    };
    $('alpha').onchange = () => {
      const a = parseSymbols($('alpha').value);
      if (!a.length) { $('alpha').value = this.model.alphabet.join(', '); return; }
      this.execute(new MutationCommand(ed => {
        ed.model.alphabet = a;
        ed.model.trans = ed.model.trans.map(t => ({ ...t, symbols: t.symbols.filter(x => a.includes(x)) })).filter(t => t.symbols.length);
        $('alpha').value = a.join(', '); ed.selection.clear();
      }));
    };
  }
}

editor = new DiagramEditor();

function doGrade() {
  const g = Auto.grade(editor.model, task), outs = [...document.querySelectorAll('.gradeOut')];
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
  const n = t.ref.states.length, ox = (editor.viewport.vw - 800) / 2;
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
  if (editor.model.states.length && !confirm('Příklad přepíše tvůj návrh. Pokračovat?')) { $('ex').value = ''; return; }
  editor.execute(new MutationCommand(ed => {
    ed.model = exampleModel(t);
    ed.selection.clear();
    ed.viewport.fitStates(ed.model.states);
    $('alpha').value = ed.model.alphabet.join(', ');
    exTask = t; lsSet('tzi_automat_ex', t.id); renderZad();
  }));
};

// ── zadání vlevo, kroky nahoře ───────────────────────────────────────────────
const formatZadBody = t => (t.steps && t.text.includes('\n') ? `<pre>${esc(t.text)}</pre>` : `<p>${typeof fmt === 'function' ? fmt(t.text) : esc(t.text)}</p>`);
const zadOf = t => {
  const img = safeImgSrc(t.image);
  return (img ? `<img src="${esc(img)}" alt="Zadání úlohy">` : '') + formatZadBody(t);
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
    h += formatZadBody(task);
  }
  $('zadBody').innerHTML = h;
}
const doneOf = id => !task ? false : task.steps ? ({ delta: RP.done.delta, table: RP.done.table, diagram: RP.done.diagram, tree: RP.done.tree, word: RP.wordsOk >= 3 })[id] : id === 'diagram' && !!doneMap()[task.id];
let tabScrollObs = null;
function syncTabList(focusCurrent) {
  const tl = $('tabList'); if (!tl) return;
  const active = tl.querySelector('.tab[aria-selected="true"]');
  if (active) {
    try { active.scrollIntoView({ block: 'nearest', inline: 'nearest', container: 'nearest' }); }
    catch (e) { active.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
    if (focusCurrent) active.focus();
  }
  if (tabScrollObs) { tabScrollObs.disconnect(); tabScrollObs = null; }
  if (!CSS.supports('animation-timeline', 'scroll()') && tl.firstElementChild && tl.lastElementChild) {
    const first = tl.firstElementChild, last = tl.lastElementChild;
    tabScrollObs = new IntersectionObserver(entries => {
      for (const { target, intersectionRatio } of entries) {
        if (target === first) tl.classList.toggle('more-start', intersectionRatio < 1);
        if (target === last) tl.classList.toggle('more-end', intersectionRatio < 1);
      }
    }, { root: tl, threshold: 1, rootMargin: '1px' });
    tabScrollObs.observe(first); tabScrollObs.observe(last);
  }
}
function renderTabs(focusCurrent) {
  const openZad = !$('app').classList.contains('noZad');
  if (!$('tabList')) {
    $('tabs').innerHTML = '<div class="tablist" id="tabList" role="tablist" focusgroup="tablist nomemory" aria-label="Kroky úlohy">' +
      TABS.map(([id, label]) => `<button type="button" class="tab" id="tab-${esc(id)}" role="tab" data-t="${esc(id)}"><span class="tab-lbl">${esc(label)}</span><span class="ck" hidden><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg></span></button>`).join('') +
      `</div><button type="button" class="btn" id="zadToggle" aria-expanded="${openZad}" aria-controls="zad" title="Skrýt nebo ukázat zadání"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>Zadání</button>`;
    $('zadToggle').onclick = () => {
      const hiddenNow = $('app').classList.toggle('noZad');
      $('zadToggle').setAttribute('aria-expanded', String(!hiddenNow));
    };
  }
  const tl = $('tabList');
  if (tl) {
    tl.querySelectorAll('.tab').forEach(b => {
      const id = b.dataset.t, selTab = id === tab;
      b.setAttribute('aria-selected', String(selTab));
      b.toggleAttribute('focusgroupstart', selTab);
      if (!hasFocusGroup) b.tabIndex = selTab ? 0 : -1;
      const ck = b.querySelector('.ck'); if (ck) ck.hidden = !doneOf(id);
    });
  }
  const zt = $('zadToggle'); if (zt) zt.setAttribute('aria-expanded', String(openZad));
  syncTabList(focusCurrent);
}
$('tabs').addEventListener('click', ev => { const b = ev.target.closest('.tab'); if (b) showTab(b.dataset.t); });
$('tabs').addEventListener('focusin', ev => {
  const b = ev.target.closest('.tab');
  if (b && b.dataset.t !== tab) showTab(b.dataset.t, false);
});
$('tabs').addEventListener('keydown', ev => {
  if (hasFocusGroup) return;
  const tabEl = ev.target.closest('.tab'), tl = $('tabList');
  if (!tabEl || !tl || !tl.contains(tabEl)) return;
  const list = [...tl.querySelectorAll('.tab')], i = list.indexOf(tabEl);
  const rtl = getComputedStyle(tl).direction === 'rtl';
  let dst = -1;
  if (ev.key === 'ArrowRight') dst = (i + (rtl ? -1 : 1) + list.length) % list.length;
  else if (ev.key === 'ArrowLeft') dst = (i + (rtl ? 1 : -1) + list.length) % list.length;
  else if (ev.key === 'Home') dst = 0;
  else if (ev.key === 'End') dst = list.length - 1;
  if (dst < 0) return;
  ev.preventDefault();
  showTab(list[dst].dataset.t, true);
});
function showTab(id, focusCurrent) {
  tab = id;
  for (const [k] of [['delta'], ['table'], ['diagram'], ['tree'], ['word']]) $('p-' + k).hidden = k !== id;
  lsSet('tzi_automat_tab_' + (task ? task.id : 'volny'), id);
  renderTabs(focusCurrent);
  if (id === 'delta') {
    syncDelta();
    const t = $('dText');
    if (t && t.value === skeleton()) { t.focus(); t.setSelectionRange(5, 5); }
  } else if (id === 'diagram') { editor.onShowDiagram(); } else if (id === 'word') { if (given) sim.cur = null; renderWordDiagram(); }
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
const autoPos = (i, n) => { const vw = editor.viewport.vw, a = Math.PI + i * 2 * Math.PI / n; return { x: Math.round(vw / 2 + Math.min(250, vw / 2 - 70) * Math.cos(a)), y: Math.round(260 + 170 * Math.sin(a)) }; };
function specFromM() { // přechodová funkce z diagramu jako text
  const m = editor.model;
  if (!m.states.length) return '';
  const d = Auto.delta(m), l = [`Q = {${m.states.map(s => s.id).join(', ')}}`, `Σ = {${m.alphabet.join(', ')}}`];
  if (m.start) l.push(`počáteční stav ${m.start}`);
  l.push(`F = {${m.accept.join(', ')}}`);
  for (const s of m.states) for (const a of m.alphabet) for (const t of (d[s.id] && d[s.id][a]) || []) l.push(`δ(${s.id}, ${a}) = ${t}`);
  return l.join('\n');
}
const skeleton = () => `Q = {}\nΣ = {${editor.model.alphabet.join(', ')}}\npočáteční stav \nF = {}\nδ(, ) = `;
function syncDelta() { const t = $('dText'); if (t && document.activeElement !== t) t.value = editor.model.states.length ? specFromM() : skeleton(); }
function applySpec(text) {
  const sp = Auto.parseSpec(String(text).slice(0, 20000)), msg = $('dMsg'), m = editor.model;
  if (!text.trim()) { msg.innerHTML = ''; return; }
  if (sp.states.length) {
    const al = task ? task.alphabet : (sp.alphabet.length ? sp.alphabet : m.alphabet), old = Object.fromEntries(m.states.map(s => [s.id, s]));
    m.alphabet = al.slice();
    m.states = sp.states.slice(0, 64).map((s, i) => old[s.id] || { id: s.id, ...autoPos(i, Math.min(sp.states.length, 64)) });
    m.start = sp.start; m.accept = sp.accept.filter(a => m.states.some(s => s.id === a));
    m.trans = sp.trans.map(t => ({ ...t, symbols: t.symbols.filter(a => al.includes(a)) })).filter(t => t.symbols.length);
    if (!task) $('alpha').value = al.join(', ');
    editor.notifyChanged(true);
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
  const startWord = () => { sim = { word: $('word').value.replace(/\s/g, '').slice(0, 256), pos: 0, active: true, cur: editor.model.start }; };
  $('word').oninput = () => { startWord(); sim.active = false; renderTrace(); };
  $('step').onclick = () => { if (!sim.active || sim.word !== $('word').value.replace(/\s/g, '').slice(0, 256)) startWord(); sim.pos = Math.min(sim.pos + 1, sim.word.length + 1); renderTrace(); };
  $('whole').onclick = () => { startWord(); sim.pos = sim.word.length; renderTrace(); };
  $('reset').onclick = () => { startWord(); renderTrace(); };
  $('pane').oninput = null;
}

// ── výběr úlohy ──────────────────────────────────────────────────────────────
const sel = $('task');
function fillSelect() {
  const all = allTasks(), opt = t => `<option value="${esc(t.id)}">${t.custom ? '[vlastní] ' : ''}${esc(t.title)}</option>`;
  sel.innerHTML = `<optgroup label="Zadaný automat: δ, tabulka, diagram, strom, slovo">${all.filter(t => t.steps).map(opt).join('')}</optgroup>` +
    `<optgroup label="Navrhni automat podle popisu">${all.filter(t => !t.steps).map(opt).join('')}</optgroup><option value="">Volný návrh</option>`;
  $('ex').innerHTML = '<option value="">Vyber…</option>' + all.map(t => `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join('');
}
function setTask(id) {
  task = allTasks().find(t => t.id === id) || null; given = !!(task && task.steps);
  lsSet('tzi_automat_last', task ? task.id : ''); sel.value = task ? task.id : '';
  editor.resetTask(load(task ? task.alphabet.slice() : editor.model.alphabet));
  sim = { word: '', pos: 0 };
  $('alpha').value = editor.model.alphabet.join(', '); $('freeTools').hidden = !!task;
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
