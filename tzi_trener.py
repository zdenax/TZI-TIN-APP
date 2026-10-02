#!/usr/bin/env python3
"""TZI Trenér: kvíz na opakování přednášek z Teoretické informatiky (KI/TIN).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Spuštění:  python3 tzi_trener.py            # http://127.0.0.1:5051, otevře se prohlížeč
           python3 tzi_trener.py --lan      # navíc dostupné v místní síti (telefon)
Bez závislostí (jen standardní knihovna). Banky otázek jsou v banky/*.json, jedna na přednášku.
"""
import json
import os
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
BANKS = BASE / "banky"
PROGRESS_FILE = BASE / "progress.json"
PORT = 5051
ALL = "_all"
lock = threading.Lock()


def load_banks():
    """Vrátí {id: {title, date, lecture, questions}} seřazené podle čísla přednášky."""
    banks = {}
    for p in sorted(BANKS.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        banks[p.stem] = d
    return dict(sorted(banks.items(), key=lambda kv: kv[1].get("lecture", 0)))


def source_label(d):
    y, m, day = d["date"].split("-")
    return f'{d["lecture"]}. přednáška ({int(day)}. {int(m)}. {y}): {d["title"]}'


def list_sources():
    banks = load_banks()
    out = [{"id": k, "label": source_label(d), "count": len(d["questions"])} for k, d in banks.items()]
    if len(out) > 1:
        out.append({"id": ALL, "label": "Všechny přednášky dohromady",
                    "count": sum(s["count"] for s in out)})
    return out


def load_questions(source):
    banks = load_banks()
    if source == ALL:
        return [q for d in banks.values() for q in d["questions"]]
    return banks[source]["questions"]


def load_progress():
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"seen": {}, "sessions": {}}


def save_progress(data):
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


HTML = r"""
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TZI Trenér</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f4f6f9; color: #1f2937; min-height: 100vh; }
  #app { max-width: 900px; margin: 0 auto; padding: 24px 20px; }

  #menu { display: flex; flex-direction: column; align-items: center; gap: 12px; padding-top: 40px; }
  #menu h1 { font-size: 2.2rem; color: #3b82f6; margin-bottom: 4px; }
  #menu .sub { color: #6b7280; font-size: 1rem; margin-bottom: 8px; text-align: center; }
  .source-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; width: 100%; max-width: 520px; }
  .source-row label { color: #374151; font-weight: 600; white-space: nowrap; }
  .source-row select { flex: 1; min-width: 0; padding: 8px 12px; border-radius: 8px; border: 2px solid #d1d5db; font-size: 1rem; cursor: pointer; background: white; }
  .progress-summary { background: white; border-radius: 10px; padding: 10px 20px; font-size: .9rem;
    color: #374151; box-shadow: 0 1px 4px rgba(0,0,0,.1); margin-bottom: 4px; text-align: center; }
  .ps-good { color: #16a34a; font-weight: 700; }
  .ps-bad  { color: #dc2626; font-weight: 700; }
  .ps-new  { color: #6b7280; }
  .menu-btn {
    width: 320px; padding: 14px; font-size: 1.05rem; border: none;
    border-radius: 10px; background: white; cursor: pointer;
    box-shadow: 0 1px 4px rgba(0,0,0,.12); transition: transform .1s, box-shadow .1s;
  }
  .menu-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.15); }
  .menu-btn.danger  { background: #111827; color: #ef4444; }
  .menu-btn.quit    { background: #fef2f2; color: #ef4444; }
  .menu-btn.resume  { background: #eff6ff; color: #1d4ed8; border: 2px solid #93c5fd; }
  .menu-btn.unseen  { background: #f0fdf4; color: #166534; }
  .menu-btn.wrongs  { background: #fff7ed; color: #9a3412; }
  .menu-btn:disabled { opacity: .4; cursor: default; }
  .menu-sep { width: 320px; border: none; border-top: 1px solid #e5e7eb; margin: 4px 0; }
  .type-row { display: flex; gap: 6px; }
  .type-row button { padding: 6px 12px; border: 2px solid #d1d5db; border-radius: 99px; background: white; cursor: pointer; font-size: .85rem; }
  .type-row button.on { border-color: #3b82f6; background: #dbeafe; color: #1d4ed8; font-weight: 600; }

  #chunks { display: none; padding-top: 24px; }
  #chunks h1 { font-size: 1.6rem; color: #3b82f6; text-align: center; margin-bottom: 16px; }
  .chunk-list { display: flex; flex-direction: column; gap: 10px; max-width: 420px; margin: 0 auto; }
  .chunk-btn {
    display: flex; justify-content: space-between; align-items: center; gap: 8px;
    background: white; border: none; border-radius: 10px; padding: 14px 18px;
    cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,.12); font-size: 1rem; text-align: left;
  }
  .chunk-btn:hover { box-shadow: 0 4px 12px rgba(0,0,0,.15); }
  .chunk-name { font-weight: 700; }
  .chunk-stats { font-size: .85rem; white-space: nowrap; }
  .chunk-stats span { margin-left: 8px; }
  .chunk-back { display: block; margin: 20px auto 0; padding: 10px 20px; border: none; border-radius: 8px; background: #e5e7eb; cursor: pointer; }
  .chunk-size-row { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 16px; font-size: .9rem; }
  .chunk-size-row input { width: 70px; padding: 6px 8px; border-radius: 8px; border: 2px solid #d1d5db; font-size: 1rem; text-align: center; }
  .chunk-size-row button { padding: 7px 14px; border: none; border-radius: 8px; cursor: pointer; background: #3b82f6; color: white; font-weight: 600; }

  #chunk-detail { display: none; padding-top: 24px; }
  #chunk-detail h1 { font-size: 1.4rem; color: #3b82f6; text-align: center; margin-bottom: 16px; }
  .chunk-detail-wrap { max-width: 480px; margin: 0 auto; }
  .chunk-detail-btns { display: flex; gap: 8px; justify-content: center; margin-bottom: 18px; flex-wrap: wrap; }
  .chunk-detail-btns button { padding: 8px 14px; border: none; border-radius: 8px; cursor: pointer; font-size: .85rem; background: white; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
  .cd-section { margin-bottom: 14px; }
  .cd-section h3 { font-size: .9rem; margin: 0 0 6px; }
  .cd-section.good h3 { color: #16a34a; }
  .cd-section.bad h3 { color: #dc2626; }
  .cd-section.new h3 { color: #6b7280; }
  .cd-qlist { display: flex; flex-wrap: wrap; gap: 6px; }
  .cd-qlist span { background: white; border-radius: 6px; padding: 3px 8px; font-size: .8rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .cd-qlist .q-pill { border: none; cursor: pointer; font: inherit; background: white; border-radius: 6px; padding: 3px 8px; font-size: .8rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .cd-qlist .q-pill:hover { background: #dbeafe; }

  .overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 100; align-items: center; justify-content: center; }
  .overlay.show { display: flex; }
  .modal { background: white; padding: 32px; border-radius: 14px; min-width: 320px; text-align: center; }
  .modal h2 { margin-bottom: 20px; }
  .modal input[type=number] { width: 120px; font-size: 1.3rem; text-align: center; padding: 8px; border: 2px solid #d1d5db; border-radius: 8px; }
  .modal-btns { display: flex; gap: 12px; justify-content: center; margin-top: 20px; }
  .modal-btns button { padding: 10px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
  .btn-ok { background: #3b82f6; color: white; }
  .btn-cancel { background: #e5e7eb; }

  #quiz { display: none; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px; }
  .header .prog  { color: #6b7280; font-size: .95rem; font-weight: 600; }
  .header .score { font-weight: 700; color: #3b82f6; }
  .progress-bar { height: 8px; background: #e5e7eb; border-radius: 99px; margin-bottom: 24px; }
  .progress-bar .fill { height: 100%; background: #3b82f6; border-radius: 99px; transition: width .3s; }
  .sudden-banner { background: #111827; color: #ef4444; text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 16px; font-weight: 700; }
  .question-box { background: white; border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
  .question-box .hint { font-size: .85rem; color: #9ca3af; margin-top: 6px; }
  .qsrc { font-size: .8rem; color: #9ca3af; margin-bottom: 6px; }
  .question-text { font-size: 1.15rem; font-weight: 700; line-height: 1.5; overflow-wrap: anywhere; }
  sub, sup { font-size: .72em; line-height: 0; }
  .question-text.calc { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 1.5rem; }
  .options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
  .opt {
    display: flex; align-items: flex-start; gap: 14px;
    background: white; border: 2px solid #e5e7eb; border-radius: 10px;
    padding: 14px 18px; cursor: pointer; transition: border-color .15s, background .15s;
    font-size: 1rem; line-height: 1.4; user-select: none;
  }
  .opt:hover:not(.disabled) { border-color: #93c5fd; background: #eff6ff; }
  .opt.selected { border-color: #3b82f6; background: #dbeafe; }
  .opt.correct  { border-color: #22c55e; background: #dcfce7; }
  .opt.wrong    { border-color: #ef4444; background: #fee2e2; }
  .opt.missed   { border-color: #f59e0b; background: #fef9c3; }
  .opt.disabled { cursor: default; }
  .opt .letter { font-weight: 800; color: #3b82f6; min-width: 20px; }
  .opt.correct .letter { color: #16a34a; }
  .opt.wrong .letter { color: #dc2626; }
  .opt.missed .letter { color: #d97706; }
  .ans-input { width: 100%; font: 1.4rem ui-monospace, Menlo, Consolas, monospace; padding: 12px 16px; border: 2px solid #d1d5db; border-radius: 10px; margin-bottom: 20px; background: white; }
  .ans-input:focus { outline: none; border-color: #3b82f6; }
  .ans-input.correct { border-color: #22c55e; background: #dcfce7; }
  .ans-input.wrong { border-color: #ef4444; background: #fee2e2; }
  .feedback { font-size: 1.05rem; font-weight: 700; min-height: 28px; margin-bottom: 12px; overflow-wrap: anywhere; }
  .feedback.ok  { color: #22c55e; }
  .feedback.bad { color: #ef4444; }
  .solution { background: white; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.1);
    white-space: pre-wrap; font: .95rem/1.5 ui-monospace, Menlo, Consolas, monospace; overflow-x: auto; display: none; }
  .solution.explain { font-family: 'Segoe UI', system-ui, sans-serif; font-size: 1rem; }
  .nav { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .nav button { padding: 12px 24px; border: none; border-radius: 9px; cursor: pointer; font-size: 1rem; font-weight: 600; }
  .nav button:disabled { opacity: .35; cursor: default; }
  .btn-prev { background: #e5e7eb; color: #374151; }
  .btn-end { background: #fff3cd; color: #856404; font-size: .9rem; }
  .btn-next { background: #3b82f6; color: white; }

  #results { display: none; text-align: center; padding-top: 40px; }
  #results h1 { font-size: 2rem; margin-bottom: 8px; }
  .big-pct { font-size: 5rem; font-weight: 900; margin: 12px 0; }
  .big-pct.good { color: #22c55e; }
  .big-pct.bad { color: #ef4444; }
  .res-detail { color: #6b7280; margin-bottom: 30px; }
  .res-btns { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .res-btns button { width: 300px; padding: 13px; border: none; border-radius: 10px; cursor: pointer; font-size: 1rem; font-weight: 600; background: white; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
  .res-btns .primary { background: #3b82f6; color: white; }
  .res-btns .warning-btn { background: #ffebee; }

  @media (max-width: 600px) {
    #app { padding: 12px; }
    #menu { padding-top: 20px; gap: 10px; }
    #menu h1 { font-size: 1.6rem; }
    .menu-btn, .menu-sep { width: 100%; }
    .source-row { flex-wrap: wrap; }
    .modal { min-width: unset; width: 90vw; padding: 24px 16px; }
    .question-box { padding: 16px; }
    .question-text { font-size: 1rem; }
    .question-text.calc { font-size: 1.2rem; }
    .opt { padding: 12px 14px; gap: 10px; font-size: .95rem; }
    .nav { flex-wrap: wrap; }
    .nav button { flex: 1 1 auto; padding: 12px 10px; font-size: .9rem; }
    .btn-end { flex-basis: 100%; order: 3; }
    .big-pct { font-size: 3.5rem; }
    .res-btns button { width: 100%; }
  }
</style>
</head>
<body>
<div id="app">

  <div id="menu">
    <h1>TZI Trenér</h1>
    <p class="sub" id="total-label">Načítám...</p>

    <div class="source-row">
      <label for="source-sel">Přednáška:</label>
      <select id="source-sel" onchange="onSourceChange()"></select>
    </div>
    <div class="type-row" id="type-row">
      <button data-t="all" class="on" onclick="setType('all')">vše</button>
      <button data-t="choice" onclick="setType('choice')">teorie (A/B/C)</button>
      <button data-t="input" onclick="setType('input')">příklady (výsledek)</button>
    </div>

    <div class="progress-summary" id="prog-summary"></div>

    <button class="menu-btn resume" id="btn-resume" onclick="resumeSession()" style="display:none">▶ Pokračovat od otázky <span id="resume-label"></span></button>
    <button class="menu-btn" onclick="showChunks()">📦 Po <span id="menu-chunk-size">10</span> (postupně)</button>
    <button class="menu-btn" onclick="startAll()">🚀 Vše popořadě</button>
    <button class="menu-btn unseen" id="btn-unseen" onclick="startUnseen()">🆕 Jen neprozkoumané (<span id="unseen-count">?</span>)</button>
    <button class="menu-btn wrongs" id="btn-wrongs" onclick="startWrongs()">⚠️ Jen chybné (<span id="wrongs-count">?</span>)</button>
    <button class="menu-btn" id="btn-correct" onclick="startCorrect()">✅ Zopakovat správné (<span id="correct-count">?</span>)</button>
    <button class="menu-btn" onclick="showRandomModal('random')">🎲 Náhodný výběr</button>
    <button class="menu-btn" onclick="showRandomModal('study')">📖 Studuj pak testuj</button>
    <button class="menu-btn danger" onclick="startExam()">🎯 Ostrý test (<span id="exam-n">15</span> ot. / <span id="exam-min">30</span> min)</button>
    <button class="menu-btn danger" onclick="startSuddenDeath()">💀 Sudden Death (náhodné)</button>
    <hr class="menu-sep">
    <button class="menu-btn" onclick="clearSourceProgress()" style="font-size:.9rem;color:#6b7280">🗑 Smazat progress této přednášky</button>
    <button class="menu-btn quit" onclick="shutdown()">❌ Ukončit server</button>
  </div>

  <div id="chunks">
    <h1>📦 Otázky po <span id="chunks-size-label">10</span></h1>
    <div class="chunk-size-row">
      <label for="chunk-size-input">Velikost úseku:</label>
      <input type="number" id="chunk-size-input" min="1" step="1">
      <button onclick="applyChunkSize()">Použít</button>
    </div>
    <div class="chunk-list" id="chunk-list"></div>
    <button class="chunk-back" onclick="showMenu()">← Zpět do menu</button>
  </div>

  <div id="chunk-detail">
    <h1 id="chunk-detail-title"></h1>
    <div class="chunk-detail-wrap">
      <div class="chunk-detail-btns">
        <button onclick="startChunkSubset('all')">🚀 Vše</button>
        <button onclick="startChunkSubset(undefined)">🆕 Neznámé</button>
        <button onclick="startChunkSubset('wrong')">⚠️ Chybné</button>
        <button onclick="startChunkSubset('correct')">✅ Správné</button>
        <button onclick="startChunkStudy()">📖 Studuj pak testuj</button>
      </div>
      <div class="cd-section good"><h3>✅ Správné</h3><div class="cd-qlist" id="cd-good"></div></div>
      <div class="cd-section bad"><h3>✗ Chybné</h3><div class="cd-qlist" id="cd-bad"></div></div>
      <div class="cd-section new"><h3>— Neznámé</h3><div class="cd-qlist" id="cd-new"></div></div>
    </div>
    <button class="chunk-back" onclick="showChunks()">← Zpět na bloky</button>
  </div>

  <div class="overlay" id="random-modal">
    <div class="modal">
      <h2>Kolik otázek?</h2>
      <input type="number" id="rand-count" min="1" value="10">
      <div class="modal-btns">
        <button class="btn-cancel" onclick="closeModal()">Zrušit</button>
        <button class="btn-ok" onclick="startRandom()">Spustit</button>
      </div>
    </div>
  </div>

  <div id="quiz">
    <div id="sudden-banner" class="sudden-banner" style="display:none">💀 SUDDEN DEATH: jedna chyba = konec!</div>
    <div class="header">
      <span class="prog" id="prog-label"></span>
      <span class="score" id="score-label"></span>
    </div>
    <div class="progress-bar"><div class="fill" id="pbar"></div></div>
    <div class="question-box">
      <div class="qsrc" id="q-src"></div>
      <div class="question-text" id="q-text"></div>
      <div class="hint" id="q-hint"></div>
    </div>
    <div class="options" id="opts"></div>
    <input type="text" class="ans-input" id="ans-input" autocomplete="off" autocapitalize="characters" spellcheck="false" style="display:none" oninput="onInput()">
    <div class="feedback" id="feedback"></div>
    <div class="solution" id="solution"></div>
    <div class="nav">
      <button class="btn-prev" id="btn-prev" onclick="prevQ()">← Předchozí</button>
      <button class="btn-end" onclick="finishEarly()">🏳 Ukončit předčasně</button>
      <button class="btn-next" id="btn-action" onclick="handleAction()">✔ Potvrdit (Enter)</button>
    </div>
  </div>

  <div id="results">
    <h1 id="res-title"></h1>
    <div class="big-pct" id="res-pct"></div>
    <div class="res-detail" id="res-detail"></div>
    <div class="res-btns">
      <button class="primary" onclick="restartSame()">🔄 Restartovat stejný výběr</button>
      <button id="btn-wrong" onclick="practiceWrong()" style="display:none" class="warning-btn"></button>
      <button onclick="backFromResults()">🏠 Hlavní menu</button>
    </div>
  </div>

</div>
<script>
let FULL = [];        // všechny otázky zdroje
let ALL = [];         // po filtru typu
let currentSource = '';
let sources = [];
let progress = {};    // {qid: "correct"|"wrong"}
let session = null;
let typeFilter = 'all';

let queue = [], idx = 0, history = [], checked = false, suddenDeath = false;
let selected = new Set(), modalMode = 'random', studyMode = false, studyPicks = [];
let examMode = false, examTimer = null, examEndTime = 0;

const $ = id => document.getElementById(id);
const show = id => {
  for (const s of ['menu','chunks','chunk-detail','quiz','results']) $(s).style.display = (s === id) ? (s === 'menu' ? 'flex' : 'block') : 'none';
};
const norm = s => { s = (s || '').toUpperCase().replace(/[\s_]/g, ''); return s.replace(/^0+(?=.)/, ''); };
const isInput = q => q.type === 'input';
const shuffle = a => [...a].sort(() => Math.random() - .5);
// Zápis z banky (a_n, Z^n, a_(n-1), ->) převede na HTML s dolními/horními indexy a šipkami.
function fmt(s) {
  s = String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return s
    .replace(/_\(([^)]+)\)/g, '<sub>$1</sub>').replace(/_([A-Za-z0-9]+)/g, '<sub>$1</sub>')
    .replace(/\^\(([^)]+)\)/g, '<sup>$1</sup>').replace(/\^([A-Za-z0-9]+)/g, '<sup>$1</sup>')
    .replace(/[₀-₉]+/g, m => '<sub>' + [...m].map(c => '₀₁₂₃₄₅₆₇₈₉'.indexOf(c)).join('') + '</sub>')
    .replace(/-&gt;/g, '→').replace(/&lt;-/g, '←').replace(/\.\.\./g, '…');
}

async function init() {
  const r = await fetch('/api/sources');
  const data = await r.json();
  sources = data.sources;
  currentSource = data.default;
  $('source-sel').innerHTML = sources.map(s =>
    `<option value="${s.id}" ${s.id === currentSource ? 'selected' : ''}>${s.label} (${s.count})</option>`).join('');
  await loadSource(currentSource);
}

async function onSourceChange() { currentSource = $('source-sel').value; await loadSource(currentSource); }

async function loadSource(source) {
  const [qr, pr] = await Promise.all([
    fetch(`/api/questions?source=${encodeURIComponent(source)}`),
    fetch(`/api/progress?source=${encodeURIComponent(source)}`)
  ]);
  FULL = await qr.json();
  const pd = await pr.json();
  progress = pd.seen || {};
  session = pd.session || null;
  applyFilter();
}

function setType(t) {
  typeFilter = t;
  document.querySelectorAll('#type-row button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  applyFilter();
}

function applyFilter() {
  ALL = typeFilter === 'all' ? FULL : FULL.filter(q => q.type === typeFilter);
  $('rand-count').max = ALL.length;
  $('rand-count').value = Math.min(10, ALL.length);
  updateMenuStats();
}

function updateMenuStats() {
  const total = ALL.length;
  const good = ALL.filter(q => progress[q.id] === 'correct').length;
  const bad = ALL.filter(q => progress[q.id] === 'wrong').length;
  const unseen = total - good - bad;
  $('total-label').textContent = `Otázek ve výběru: ${total}`;
  $('prog-summary').innerHTML =
    `<span class="ps-good">✓ ${good} správně</span> &nbsp;·&nbsp; ` +
    `<span class="ps-bad">✗ ${bad} chybně</span> &nbsp;·&nbsp; ` +
    `<span class="ps-new">— ${unseen} nových</span>`;
  $('unseen-count').textContent = unseen;
  $('wrongs-count').textContent = bad;
  $('correct-count').textContent = good;
  $('btn-unseen').disabled = unseen === 0;
  $('btn-wrongs').disabled = bad === 0;
  $('btn-correct').disabled = good === 0;
  const n = Math.min(15, total);
  $('exam-n').textContent = n;
  $('exam-min').textContent = Math.max(5, Math.round(n * 2));
  if (session && session.idx < session.queue_ids.length) {
    const q = FULL.find(x => x.id === session.queue_ids[session.idx]);
    $('resume-label').textContent = q ? q.number : '';
    $('btn-resume').style.display = q ? 'block' : 'none';
  } else $('btn-resume').style.display = 'none';
}

async function saveProgress() {
  const m = {};
  for (const h of history) m[h.id] = h.isCorrect ? 'correct' : 'wrong';
  const newProgress = Object.assign({}, progress, m);
  const newSession = (idx < queue.length && !examMode) ? {queue_ids: queue.map(q => q.id), idx, sudden_death: suddenDeath, history} : null;
  await fetch(`/api/progress?source=${encodeURIComponent(currentSource)}`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({seen: newProgress, session: newSession})
  });
  progress = newProgress; session = newSession;
}

let fromChunks = false;
function showMenu() { updateMenuStats(); show('menu'); }
function showResults() { show('results'); renderResults(); }

// ── bloky ──
let CHUNK_SIZE = parseInt(localStorage.getItem('tzi_chunk_size'), 10) || 10;
function syncChunkSizeUI() {
  $('menu-chunk-size').textContent = CHUNK_SIZE;
  $('chunks-size-label').textContent = CHUNK_SIZE;
  $('chunk-size-input').value = CHUNK_SIZE;
}
function applyChunkSize() {
  const n = parseInt($('chunk-size-input').value, 10);
  if (!n || n < 1) return;
  CHUNK_SIZE = n; localStorage.setItem('tzi_chunk_size', String(n));
  syncChunkSizeUI(); renderChunks();
}
function showChunks() { fromChunks = false; syncChunkSizeUI(); renderChunks(); show('chunks'); }
function getChunks() { const out = []; for (let i = 0; i < ALL.length; i += CHUNK_SIZE) out.push(ALL.slice(i, i + CHUNK_SIZE)); return out; }
function renderChunks() {
  const list = $('chunk-list'); list.innerHTML = '';
  getChunks().forEach((qs, i) => {
    const done = qs.filter(q => progress[q.id] === 'correct').length;
    const wrong = qs.filter(q => progress[q.id] === 'wrong').length;
    const btn = document.createElement('button');
    btn.className = 'chunk-btn';
    btn.innerHTML = `<span class="chunk-name">Blok ${i + 1} (${i * CHUNK_SIZE + 1}–${i * CHUNK_SIZE + qs.length})</span>` +
      `<span class="chunk-stats"><span class="ps-new">— ${qs.length - done - wrong}</span><span class="ps-bad">✗ ${wrong}</span><span class="ps-good">✓ ${done}</span></span>`;
    btn.onclick = () => showChunkDetail(qs, i);
    list.appendChild(btn);
  });
}
let currentChunk = [];
function showChunkDetail(qs, i) {
  currentChunk = qs;
  $('chunk-detail-title').textContent = `Blok ${i + 1} (${i * CHUNK_SIZE + 1}–${i * CHUNK_SIZE + qs.length})`;
  const pills = (el, list) => $(el).innerHTML = list.map(q => `<button class="q-pill" onclick="startChunkQuestion('${q.id}')">${q.number}${isInput(q) ? ' ✎' : ''}</button>`).join('') || '<span>—</span>';
  pills('cd-good', qs.filter(q => progress[q.id] === 'correct'));
  pills('cd-bad', qs.filter(q => progress[q.id] === 'wrong'));
  pills('cd-new', qs.filter(q => !progress[q.id]));
  show('chunk-detail');
}
function startChunkQuestion(id) { const q = currentChunk.find(q => q.id === id); if (q) { fromChunks = true; beginSession([q], false); } }
function startChunkSubset(status) {
  let qs;
  if (status === 'all') qs = currentChunk;
  else if (status === undefined) qs = currentChunk.filter(q => !progress[q.id]);
  else qs = currentChunk.filter(q => progress[q.id] === status);
  if (!qs.length) return;
  fromChunks = true; beginSession([...qs], false);
}
function startChunkStudy() {
  const pool = currentChunk.filter(q => !progress[q.id] || progress[q.id] === 'wrong');
  if (!pool.length) return;
  fromChunks = true; showRandomModal('chunk-study', pool);
}

// ── režimy ──
function startAll() { beginSession([...ALL], false); }
function startUnseen() { beginSession(ALL.filter(q => !progress[q.id]), false); }
function startWrongs() { beginSession(ALL.filter(q => progress[q.id] === 'wrong'), false); }
function startCorrect() { beginSession(ALL.filter(q => progress[q.id] === 'correct'), false); }

function resumeSession() {
  if (!session) return;
  const idMap = Object.fromEntries(FULL.map(q => [q.id, q]));
  queue = session.queue_ids.map(id => idMap[id]).filter(Boolean);
  idx = session.idx; history = session.history || []; suddenDeath = session.sudden_death || false;
  studyMode = false; examMode = false; fromChunks = false;
  $('sudden-banner').style.display = suddenDeath ? 'block' : 'none';
  show('quiz'); renderQ();
}

let modalPool = null;
function showRandomModal(mode, pool) {
  modalMode = mode || 'random';
  if (modalMode === 'study' && !pool) pool = ALL.filter(q => !progress[q.id] || progress[q.id] === 'wrong');
  modalPool = pool || null;
  $('random-modal').querySelector('h2').textContent = (modalMode === 'study' || modalMode === 'chunk-study') ? 'Kolik otázek nastudovat?' : 'Kolik otázek?';
  const maxN = modalPool ? modalPool.length : ALL.length;
  const input = $('rand-count'); input.max = maxN; input.value = Math.min(10, maxN);
  $('random-modal').classList.add('show');
  setTimeout(() => input.focus(), 50);
}
function closeModal() { $('random-modal').classList.remove('show'); }
function startRandom() {
  const maxN = modalPool ? modalPool.length : ALL.length;
  const n = Math.min(Math.max(1, parseInt($('rand-count').value) || 1), maxN);
  closeModal();
  if (modalMode === 'study' || modalMode === 'chunk-study') startStudy(shuffle(modalPool || ALL).slice(0, n));
  else beginSession(shuffle(ALL).slice(0, n), false);
}
function startStudy(qs) {
  if (!qs.length) return;
  studyPicks = [...qs]; studyMode = true; examMode = false;
  queue = [...qs]; idx = 0; history = []; suddenDeath = false;
  $('sudden-banner').style.display = 'none';
  show('quiz'); renderQ();
}
function startSuddenDeath() { beginSession(shuffle(ALL), true); }

function startExam() {
  const n = Math.min(15, ALL.length);
  if (!n) return;
  examMode = true; studyMode = false;
  queue = shuffle(ALL).slice(0, n); idx = 0; history = []; suddenDeath = false;
  $('sudden-banner').style.display = 'none';
  show('quiz');
  startExamTimer(Math.max(5, n * 2) * 60);
  renderQ();
}
function startExamTimer(sec) { clearExamTimer(); examEndTime = Date.now() + sec * 1000; updateExamTimer(); examTimer = setInterval(updateExamTimer, 1000); }
function clearExamTimer() { if (examTimer) clearInterval(examTimer); examTimer = null; }
function updateExamTimer() {
  const remain = Math.max(0, Math.round((examEndTime - Date.now()) / 1000));
  $('score-label').textContent = `⏱ ${String(Math.floor(remain / 60)).padStart(2, '0')}:${String(remain % 60).padStart(2, '0')}`;
  if (remain <= 0) { clearExamTimer(); saveProgress(); showResults(); }
}

function beginSession(qs, sd) {
  if (!qs.length) return;
  queue = qs; idx = 0; history = []; suddenDeath = sd; studyMode = false; examMode = false;
  $('sudden-banner').style.display = sd ? 'block' : 'none';
  show('quiz'); renderQ();
}

// ── otázka ──
function evaluate(q) {
  if (isInput(q)) {
    const v = norm($('ans-input').value);
    return {userKeys: [v], correctKeys: [norm(q.answer)], isCorrect: v === norm(q.answer)};
  }
  const cs = new Set(q.correct);
  return {userKeys: [...selected], correctKeys: [...cs],
    isCorrect: selected.size === cs.size && [...selected].every(k => cs.has(k))};
}
function record(q) {
  const rec = Object.assign({id: q.id}, evaluate(q));
  const i = history.findIndex(h => h.id === q.id);
  if (i >= 0) history[i] = rec; else history.push(rec);
  return rec;
}
function hasAnswer() { return isInput(queue[idx]) ? $('ans-input').value.trim() !== '' : selected.size > 0; }
function syncAction() { $('btn-action').disabled = !hasAnswer(); }
function onInput() { if (!checked && !studyMode) syncAction(); }

function renderQ() {
  const q = queue[idx];
  checked = false; selected = new Set();
  const total = queue.length;
  const correct = history.filter(h => h.isCorrect).length;
  const pct = history.length ? Math.round(correct / history.length * 100) : 0;

  $('prog-label').textContent = `Otázka ${idx + 1} / ${total}`;
  if (!examMode) $('score-label').textContent = history.length ? `Úspěšnost: ${pct} %` : 'Úspěšnost: – %';
  $('pbar').style.width = `${(idx / total) * 100}%`;

  const src = sources.find(s => s.id === currentSource);
  const lec = q.id.split('-')[0];
  $('q-src').textContent = `${lec}. přednáška · otázka ${q.number}` + (isInput(q) ? ' · příklad na výsledek' : ' · teorie');
  const t = $('q-text'); t.innerHTML = fmt(q.text); t.className = 'question-text' + (isInput(q) ? ' calc' : '');
  $('q-hint').textContent = isInput(q) ? (q.hint || '') : (q.correct.length > 1 ? '(Vyberte více správných odpovědí)' : '');
  $('feedback').textContent = ''; $('feedback').className = 'feedback';
  const sol = $('solution'); sol.style.display = 'none'; sol.textContent = '';

  const optsEl = $('opts'); optsEl.innerHTML = '';
  const inp = $('ans-input'); inp.value = ''; inp.disabled = false; inp.className = 'ans-input';
  inp.style.display = isInput(q) ? 'block' : 'none';
  if (!isInput(q)) {
    for (const [letter, text] of Object.entries(q.options)) {
      const div = document.createElement('div');
      div.className = 'opt'; div.id = 'opt-' + letter;
      div.innerHTML = `<span class="letter">${letter}</span><span>${fmt(text)}</span>`;
      div.addEventListener('click', () => toggleOpt(letter));
      optsEl.appendChild(div);
    }
  }

  $('btn-prev').disabled = (idx === 0) || suddenDeath || studyMode;
  $('btn-action').textContent = '✔ Potvrdit (Enter)';
  $('btn-action').disabled = true;

  if (studyMode) { renderStudy(q); return; }
  const rec = history.find(h => h.id === q.id);
  if (examMode) {
    if (rec) {
      if (isInput(q)) inp.value = rec.userKeys[0] || '';
      else { selected = new Set(rec.userKeys); rec.userKeys.forEach(l => $('opt-' + l)?.classList.add('selected')); }
    }
    $('btn-action').textContent = idx < total - 1 ? 'Další →  (Enter)' : '📊 Odeslat test (Enter)';
    syncAction();
    if (isInput(q)) inp.focus();
    return;
  }
  if (rec) restoreState(rec); else if (isInput(q)) inp.focus();
}

function renderStudy(q) {
  $('prog-label').textContent = `📖 Studium ${idx + 1} / ${queue.length}`;
  $('score-label').textContent = '';
  if (isInput(q)) {
    $('ans-input').value = q.answer; $('ans-input').disabled = true; $('ans-input').classList.add('correct');
    showSolution(q);
  } else {
    const cs = new Set(q.correct);
    for (const l of Object.keys(q.options)) { const el = $('opt-' + l); if (cs.has(l)) el.classList.add('correct'); el.classList.add('disabled'); }
    showSolution(q);
  }
  $('feedback').textContent = '📖 Studijní režim: správná odpověď je zvýrazněna';
  $('feedback').className = 'feedback ok';
  $('btn-action').textContent = idx < queue.length - 1 ? '📖 Další (studium) →' : '▶ Spustit test bez klíče';
  $('btn-action').disabled = false;
}

function showSolution(q) {
  const el = $('solution');
  const text = isInput(q) ? q.solution : q.explanation;
  if (!text) return;
  el.className = 'solution' + (isInput(q) ? '' : ' explain');
  el.innerHTML = fmt(text); el.style.display = 'block';
}

function toggleOpt(letter) {
  if (checked || studyMode) return;
  const q = queue[idx];
  if (isInput(q)) return;
  if (selected.has(letter)) { selected.delete(letter); $('opt-' + letter).classList.remove('selected'); }
  else {
    if (selected.size >= q.correct.length) return;
    selected.add(letter); $('opt-' + letter).classList.add('selected');
  }
  syncAction();
}

function handleAction() {
  if (studyMode) { studyNext(); return; }
  if (examMode) { examNext(); return; }
  if (!checked) confirmAnswer(); else nextQ();
}

function studyNext() {
  idx++;
  if (idx < queue.length) renderQ();
  else { studyMode = false; queue = shuffle(studyPicks); idx = 0; history = []; renderQ(); }
}

function examNext() {
  if (!hasAnswer()) return;
  record(queue[idx]);
  idx++;
  if (idx < queue.length) renderQ();
  else { clearExamTimer(); saveProgress(); showResults(); }
}

function confirmAnswer() {
  if (!hasAnswer()) return;
  checked = true;
  const q = queue[idx];
  const rec = record(q);
  restoreState(rec);
  saveProgress();
  if (suddenDeath && !rec.isCorrect) {
    setTimeout(() => { alert(`☠️ GAME OVER!\nSprávně bylo: ${isInput(q) ? q.answer : rec.correctKeys.join(', ')}`); showResults(); }, 600);
  }
}

function restoreState(rec) {
  checked = true;
  const q = queue[idx];
  const fb = $('feedback');
  if (isInput(q)) {
    const inp = $('ans-input'); inp.value = rec.userKeys[0] || ''; inp.disabled = true;
    inp.classList.add(rec.isCorrect ? 'correct' : 'wrong');
    fb.textContent = rec.isCorrect ? '✅  Správně!' : `❌  Špatně!   Správně: ${q.answer}`;
  } else {
    const cs = new Set(rec.correctKeys), us = new Set(rec.userKeys);
    for (const l of Object.keys(q.options)) {
      const el = $('opt-' + l); if (!el) continue;
      el.classList.remove('selected', 'correct', 'wrong', 'missed'); el.classList.add('disabled');
      if (us.has(l) && cs.has(l)) el.classList.add('correct');
      else if (us.has(l)) el.classList.add('wrong');
      else if (cs.has(l)) el.classList.add('missed');
    }
    fb.textContent = rec.isCorrect ? '✅  Správně!' : `❌  Špatně!   Správně: ${rec.correctKeys.join(', ')}`;
  }
  fb.className = 'feedback ' + (rec.isCorrect ? 'ok' : 'bad');
  showSolution(q);
  const correct = history.filter(h => h.isCorrect).length;
  $('score-label').textContent = `Úspěšnost: ${Math.round(correct / history.length * 100)} %`;
  const btn = $('btn-action');
  btn.textContent = idx < queue.length - 1 ? 'Další →  (Enter)' : '📊 Výsledky (Enter)';
  btn.disabled = false;
  btn.focus();
}

function prevQ() {
  if (studyMode || idx === 0) return;
  if (examMode && hasAnswer()) record(queue[idx]);
  idx--; renderQ();
}
function nextQ() { idx++; if (idx < queue.length) { renderQ(); saveProgress(); } else { saveProgress(); showResults(); } }

function finishEarly() {
  if (!history.length) { if (confirm('Žádné odpovědi. Zpět do menu?')) { clearExamTimer(); examMode = false; backFromResults(); } return; }
  if (confirm('Ukončit předčasně a uložit progress?')) { clearExamTimer(); saveProgress(); showResults(); }
}

function renderResults() {
  const correct = history.filter(h => h.isCorrect).length;
  const pct = Math.round(correct / Math.max(history.length, 1) * 100);
  $('res-title').textContent = examMode ? (pct >= 60 ? '✅ Ostrý test SPLNĚN' : '❌ Ostrý test NESPLNĚN')
    : (suddenDeath && pct < 100 ? '☠️ GAME OVER ☠️' : 'Výsledky testu');
  const p = $('res-pct'); p.textContent = pct + ' %'; p.className = 'big-pct ' + (pct >= 60 ? 'good' : 'bad');
  $('res-detail').textContent = `Správně ${correct} z ${history.length} zodpovězených` + (examMode ? ' · orientační hranice 60 %' : '');
  const wrongIds = new Set(history.filter(h => !h.isCorrect).map(h => h.id));
  const wrongQ = FULL.filter(q => wrongIds.has(q.id));
  const wb = $('btn-wrong');
  if (wrongQ.length && !suddenDeath) { wb.style.display = 'block'; wb.textContent = `⚠️ Procvičit jen chyby (${wrongQ.length})`; wb._wrongQ = wrongQ; }
  else wb.style.display = 'none';
  examMode = false;
}

function backFromResults() { if (fromChunks) showChunks(); else showMenu(); }
function restartSame() { beginSession([...queue], suddenDeath); }
function practiceWrong() { beginSession([...$('btn-wrong')._wrongQ], false); }

async function clearSourceProgress() {
  if (!confirm('Smazat progress pro vybranou přednášku?')) return;
  const ids = new Set(FULL.map(q => q.id));
  const keep = Object.fromEntries(Object.entries(progress).filter(([k]) => !ids.has(k)));
  await fetch(`/api/progress?source=${encodeURIComponent(currentSource)}`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({seen: keep, session: null})
  });
  progress = keep; session = null; updateMenuStats();
}

document.addEventListener('keydown', e => {
  if ($('quiz').style.display === 'none') return;
  const inField = e.target.tagName === 'INPUT';
  if (e.key === 'Enter') { if (!$('btn-action').disabled) { e.preventDefault(); handleAction(); } }
  else if (inField) return;
  else if (e.key === 'ArrowRight') { if (!$('btn-action').disabled) handleAction(); }
  else if (e.key === 'ArrowLeft') { if (!$('btn-prev').disabled) prevQ(); }
  else { const k = e.key.toUpperCase(); if (/^[A-D]$/.test(k)) toggleOpt(k); }
});
$('rand-count').addEventListener('keydown', e => { if (e.key === 'Enter') startRandom(); if (e.key === 'Escape') closeModal(); });

async function shutdown() {
  if (!confirm('Ukončit TZI Trenér server?')) return;
  document.body.innerHTML = '<div style="text-align:center;padding:80px;font-family:sans-serif"><h2>Server zastaven.</h2><p style="color:#6b7280">Zavři tuto záložku.</p></div>';
  try { await fetch('/shutdown', {method: 'POST'}); } catch {}
}

init();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        source = q.get("source", [""])[0]
        if u.path == "/":
            return self._send(200, HTML, "text/html; charset=utf-8")
        if u.path == "/api/sources":
            srcs = list_sources()
            real = [s for s in srcs if s["id"] != ALL]
            default = real[-1]["id"] if real else ""
            return self._json({"sources": srcs, "default": default})
        if u.path == "/api/questions":
            try:
                return self._json(load_questions(source))
            except (KeyError, OSError, ValueError) as e:
                return self._json({"error": str(e)}, 404)
        if u.path == "/api/progress":
            with lock:
                d = load_progress()
            return self._json({"seen": d.get("seen", {}), "session": d.get("sessions", {}).get(source)})
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/progress":
            source = parse_qs(u.query).get("source", [""])[0]
            n = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json({"error": "bad json"}, 400)
            with lock:
                d = load_progress()
                d["seen"] = payload.get("seen", {})
                d.setdefault("sessions", {})[source] = payload.get("session")
                save_progress(d)
            return self._json({"ok": True})
        if u.path == "/shutdown":
            self._send(200, "bye", "text/plain")
            threading.Timer(0.2, lambda: os._exit(0)).start()
            return
        self._send(404, "not found", "text/plain")

    def log_message(self, *args):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    if not list(BANKS.glob("*.json")):
        raise SystemExit(f"V {BANKS} nejsou žádné banky otázek. Spusť: python3 build_bank.py")
    lan = "--lan" in sys.argv
    host = "0.0.0.0" if lan else "127.0.0.1"
    for port in range(PORT, PORT + 20):
        try:
            httpd = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit(f"Nenašel jsem volný port ({PORT}-{PORT + 19}).")
    url = f"http://127.0.0.1:{port}"
    print(f"TZI Trenér → {url}")
    if lan:
        print(f"V síti (telefon):   http://{lan_ip()}:{port}")
    print("Ukončíš ho tlačítkem v menu nebo přes Ctrl+C.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKonec.")


if __name__ == "__main__":
    main()
