// ── otázka ──
function evaluate(q) {
  if (isRecall(q)) {
    const v = $('ans-input').value.trim(), m = matchRecall(v, q.accept);
    return {userKeys: [v], correctKeys: [q.accept[0]], isCorrect: !!m, typo: m && m.typo ? m.variant : null};
  }
  if (isInput(q)) {
    const rawU = $('ans-input').value;
    const v = norm(rawU), c = norm(q.answer);
    const lU = WASM_CORE.writeStr(1024, String(rawU ?? '').normalize('NFC'));
    const lE = WASM_CORE.writeStr(3072, String(q.answer ?? '').normalize('NFC'));
    const ok = WASM_CORE.exp.evaluateInputBuffers(lU, lE) === 1;
    return {userKeys: [v], correctKeys: [c], isCorrect: ok};
  }
  const cs = new Set(q.correct);
  const allKeys = Object.keys(q.options || {});
  let selMask = 0, corMask = 0;
  allKeys.forEach((k, bit) => {
    if (selected.has(k)) selMask |= (1 << bit);
    if (cs.has(k)) corMask |= (1 << bit);
  });
  const isOk = WASM_CORE.exp.evaluateChoiceMask(selMask, corMask) === 1;
  return {userKeys: [...selected], correctKeys: [...cs], isCorrect: isOk};
}
function record(q) {
  if (isReveal(q)) return null; // bez vyhodnocení, do výsledků se nezapočítá
  const rec = Object.assign({id: q.id}, evaluate(q));
  const i = history.findIndex(h => h.id === q.id);
  if (i >= 0) history[i] = rec; else history.push(rec);
  return rec;
}
function hasAnswer() { return isReveal(queue[idx]) || (isInput(queue[idx]) ? $('ans-input').value.trim() !== '' : selected.size > 0); }
function syncAction() { $('btn-action').disabled = !hasAnswer(); }
function onInput() { if (!checked && !studyMode) syncAction(); }

function renderQ() {
  const q = queue[idx];
  checked = false; selected = new Set();
  const total = queue.length;
  const correct = history.filter(h => h.isCorrect).length;
  const pct = history.length ? Math.round(correct / history.length * 100) : 0;

  $('prog-label').textContent = `Otázka ${idx + 1} z ${total}`;
  if (!examMode) $('score-label').textContent = history.length ? `Úspěšnost: ${pct} %` : 'Úspěšnost –';
  $('pbar').style.width = `${(idx / total) * 100}%`;

  const src = sources.find(s => s.id === currentSource);
  const lec = q.id.split('-')[0];
  $('q-src').textContent = isRecall(q) ? `Doplňovačka · ${q.category} · otázka ${q.number}`
    : `${lec}. přednáška · otázka ${q.number}` + (isReveal(q) ? ' · zadání na rozbor' : isInput(q) ? ' · příklad na výsledek' : ' · teorie');
  const t = $('q-text'); t.innerHTML = fmt(q.text); t.className = 'question-text' + (q.type === 'input' ? ' calc' : '');
  const qh = $('q-hint');
  if (isRecall(q)) qh.innerHTML = esc(`Očekáváno: ${wordsLabel(q.words)}`) + (q.hint ? `. ${fmt(q.hint)}` : '');
  else if (isInput(q)) qh.innerHTML = q.hint ? fmt(q.hint) : '';
  else qh.textContent = q.correct.length > 1 ? '(Vyberte více správných odpovědí)' : '';
  $('feedback').textContent = ''; $('feedback').className = 'feedback';
  const sol = $('solution'); sol.style.display = 'none'; sol.textContent = '';

  const optsEl = $('opts'); optsEl.innerHTML = '';
  const inp = $('ans-input'); inp.value = ''; inp.disabled = false; inp.className = 'ans-input';
  inp.style.display = isInput(q) && !isReveal(q) ? 'block' : 'none';
  inp.setAttribute('autocapitalize', isRecall(q) ? 'off' : 'characters');
  if (!isInput(q)) {
    const keys = optOrder[q.id] || (optOrder[q.id] = shuffle(Object.keys(q.options)));
    const tpl = $('tpl-option');
    keys.forEach((letter, i) => {
      let div;
      if (tpl && 'content' in tpl) {
        const frag = tpl.content.cloneNode(true);
        div = frag.firstElementChild;
        div.id = 'opt-' + letter;
        div.querySelector('.letter').textContent = LETTERS[i];
        div.querySelector('.opt-text').innerHTML = fmt(q.options[letter]);
        div.addEventListener('click', () => toggleOpt(letter));
        optsEl.appendChild(frag);
      } else {
        div = document.createElement('div');
        div.className = 'opt'; div.id = 'opt-' + letter;
        div.innerHTML = `<span class="letter">${LETTERS[i]}</span><span class="opt-text">${fmt(q.options[letter])}</span>`;
        div.addEventListener('click', () => toggleOpt(letter));
        optsEl.appendChild(div);
      }
    });
  }

  $('btn-prev').disabled = (idx === 0) || suddenDeath || studyMode;
  $('btn-action').innerHTML = 'Potvrdit<span class="kh">Enter</span>';
  renderChain();
  $('btn-action').disabled = true;
  if (isReveal(q)) { $('btn-action').disabled = false; $('btn-action').innerHTML = 'Ukázat řešení<span class="kh">Enter</span>'; }

  if (studyMode) { renderStudy(q); return; }
  const rec = history.find(h => h.id === q.id);
  if (examMode) {
    if (rec) {
      if (isInput(q)) inp.value = rec.userKeys[0] || '';
      else { selected = new Set(rec.userKeys); rec.userKeys.forEach(l => $('opt-' + l)?.classList.add('selected')); }
    }
    $('btn-action').innerHTML = (idx < total - 1 ? 'Další' : 'Odeslat test') + '<span class="kh">Enter</span>';
    syncAction();
    if (isInput(q)) inp.focus();
    return;
  }
  if (rec && isReveal(q)) revealTask(q); else if (rec) restoreState(rec); else if (isInput(q)) inp.focus();
}

function renderChain() {
  const el = $('pchain');
  if (studyMode || queue.length > 45) { el.innerHTML = ''; return; }
  el.innerHTML = queue.map((q, i) => {
    const h = history.find(h => h.id === q.id);
    let c = '', ch = '·';
    if (h && examMode) { c = 'ans'; ch = '–'; }
    else if (h) { c = h.isCorrect ? 'ok' : 'bad'; ch = h.isCorrect ? '1' : '0'; }
    return `<i class="${c}${i === idx ? ' cur' : ''}"${i === idx ? ' aria-current="step"' : ''}>${ch}</i>`;
  }).join('');
}

function renderStudy(q) {
  $('prog-label').textContent = `Studium ${idx + 1} z ${queue.length}`;
  $('score-label').textContent = '';
  if (isInput(q)) {
    $('ans-input').value = isRecall(q) ? q.accept[0] : q.answer; $('ans-input').disabled = true; $('ans-input').classList.add('correct');
    showSolution(q);
  } else {
    const cs = new Set(q.correct);
    for (const l of Object.keys(q.options)) { const el = $('opt-' + l); if (cs.has(l)) el.classList.add('correct'); el.classList.add('disabled'); }
    showSolution(q);
  }
  $('feedback').textContent = 'Studijní režim: správná odpověď je zvýrazněna';
  $('feedback').className = 'feedback ok study';
  $('btn-action').innerHTML = (idx < queue.length - 1 ? 'Další' : 'Spustit test bez klíče') + '<span class="kh">Enter</span>';
  $('btn-action').disabled = false;
}

function showSolution(q) {
  const el = $('solution');
  const text = isRecall(q) ? `Odpověď: ${q.accept[0]}\nUznává se i: ${q.accept.slice(1).join(', ') || '–'}` + (q.explanation ? `\n\n${q.explanation}` : '')
    : isInput(q) ? q.solution : q.explanation;
  if (!text) return;
  el.className = 'solution' + (q.type === 'input' && !isReveal(q) ? '' : ' explain');
  el.innerHTML = fmt(text); el.style.display = 'block';
}

function toggleOpt(letter) {
  if (checked || studyMode) return;
  const q = queue[idx];
  if (isInput(q)) return;
  if (selected.has(letter)) { selected.delete(letter); $('opt-' + letter).classList.remove('selected'); }
  else {
    if (q.correct && q.correct.length === 1) {
      selected.forEach(l => $('opt-' + l)?.classList.remove('selected'));
      selected.clear();
    } else if (selected.size >= q.correct.length) {
      return;
    }
    selected.add(letter); $('opt-' + letter).classList.add('selected');
  }
  syncAction();
}

function handleAction() {
  if (studyMode) { studyNext(); return; }
  if (examMode) { examNext(); return; }
  if (!checked) confirmAnswer(); else if (isReveal(queue[idx])) gradeTask(true); else nextQ();
}

function studyNext() {
  idx++;
  if (idx < queue.length) renderQ();
  else { studyMode = false; queue = shuffle(studyPicks); idx = 0; history = []; optOrder = {}; renderQ(); }
}

function examNext() {
  if (!hasAnswer()) return;
  record(queue[idx]);
  idx++;
  if (idx < queue.length) renderQ();
  else { clearExamTimer(); saveProgress(); showResults(); }
}

function toggleSolution(btn) {
  const el = $('solution'), hide = el.style.display !== 'none';
  el.style.display = hide ? 'none' : 'block';
  btn.textContent = hide ? 'Ukázat řešení' : 'Skrýt řešení';
}

function revealTask(q) {
  checked = true;
  showSolution(q);
  const rec = history.find(h => h.id === q.id);
  const mark = rec ? (rec.isCorrect ? 'Označeno: zvládl jsem. ' : 'Označeno: nezvládl jsem. ') : '';
  $('feedback').innerHTML = mark + '<button class="btn-end" onclick="toggleSolution(this)">Skrýt řešení</button> <button class="btn-end" onclick="gradeTask(false)">Nezvládl jsem</button>';
  $('btn-action').innerHTML = 'Zvládl jsem<span class="kh">Enter</span>';
  $('btn-action').focus();
}

// vlastní hodnocení člověka: Zvládl jsem = správně, Nezvládl jsem = špatně
// (u doplňovačky ruční oprava verdiktu, napsaná odpověď zůstane)
function gradeTask(ok) {
  const q = queue[idx];
  const i = history.findIndex(h => h.id === q.id);
  const rec = isRecall(q) && i >= 0 ? Object.assign({}, history[i], {isCorrect: ok, manual: true, typo: null})
    : {id: q.id, userKeys: [], correctKeys: [], isCorrect: ok};
  if (i >= 0) history[i] = rec; else history.push(rec);
  nextQ();
}

function confirmAnswer() {
  if (!hasAnswer()) return;
  checked = true;
  const q = queue[idx];
  if (isReveal(q)) { revealTask(q); return; }
  const rec = record(q);
  restoreState(rec);
  saveProgress();
  if (suddenDeath && !rec.isCorrect) {
    setTimeout(() => { alert(`Konec hry. Správná odpověď: ${isRecall(q) ? q.accept[0] : isInput(q) ? q.answer : letters(q, rec.correctKeys)}`); showResults(); }, 600);
  }
}

function restoreState(rec) {
  checked = true;
  const q = queue[idx];
  const fb = $('feedback');
  if (isInput(q)) {
    const inp = $('ans-input'); inp.value = rec.userKeys[0] || ''; inp.disabled = true;
    inp.classList.add(rec.isCorrect ? 'correct' : 'wrong');
    if (isRecall(q)) fb.innerHTML = (rec.manual ? esc(rec.isCorrect ? 'Uznáno ručně' : 'Ručně označeno jako špatně')
        : rec.typo ? `Správně, uznáno jako překlep (${esc(rec.typo)})` : rec.isCorrect ? 'Správně' : `Špatně. Správně: ${fmt(q.accept[0])}`) +
      ` <button class="btn-end" onclick="gradeTask(${!rec.isCorrect})">${rec.isCorrect ? 'Označit jako špatně' : 'Uznat jako správně'}</button>`;
    else fb.innerHTML = rec.isCorrect ? 'Správně' : `Špatně. Správně: ${fmt(q.answer)}`;
  } else {
    const cs = new Set(rec.correctKeys), us = new Set(rec.userKeys);
    for (const l of Object.keys(q.options)) {
      const el = $('opt-' + l); if (!el) continue;
      el.classList.remove('selected', 'correct', 'wrong', 'missed'); el.classList.add('disabled');
      if (us.has(l) && cs.has(l)) el.classList.add('correct');
      else if (us.has(l)) el.classList.add('wrong');
      else if (cs.has(l)) el.classList.add('missed');
    }
    fb.textContent = rec.isCorrect ? 'Správně' : `Špatně. Správně: ${letters(q, rec.correctKeys)}`;
  }
  fb.className = 'feedback ' + (rec.isCorrect ? 'ok' : 'bad');
  showSolution(q);
  const correct = history.filter(h => h.isCorrect).length;
  $('score-label').textContent = `Úspěšnost: ${Math.round(correct / history.length * 100)} %`;
  renderChain();
  const btn = $('btn-action');
  btn.innerHTML = (idx < queue.length - 1 ? 'Další' : 'Výsledky') + '<span class="kh">Enter</span>';
  btn.disabled = false;
  btn.focus();
}

function prevQ() {
  if (studyMode || idx === 0) return;
  if (examMode && hasAnswer()) record(queue[idx]);
  idx--; renderQ();
}
function nextQ() {
  idx++;
  if (idx < queue.length) {
    renderQ();
    saveProgress();
  } else {
    saveProgress();
    if (kothMode) {
      submitKothResults().then(() => showResults());
    } else {
      showResults();
    }
  }
}

function finishEarly() {
  if (!history.length) { if (confirm('Zatím žádné odpovědi. Vrátit se do menu?')) { clearExamTimer(); examMode = false; kothMode = false; backFromResults(); } return; }
  if (confirm('Ukončit sadu předčasně a uložit postup?')) {
    clearExamTimer();
    saveProgress();
    if (kothMode) {
      submitKothResults().then(() => showResults());
    } else {
      showResults();
    }
  }
}

function renderResults() {
  const n = history.length;
  const correct = history.filter(h => h.isCorrect).length;
  const pct = WASM_CORE.exp.calcPercentage(correct | 0, n | 0);
  const passed = pct >= 60;
  const sdEnd = suddenDeath && !examMode && pct < 100;
  let compGood = passed && !sdEnd;
  if (kothMode && kothLastResult) {
    const m = kothLastResult.mode || compMode || 'koth';
    if (m === 'ffa') {
      compGood = kothLastResult.rank === 1 || passed;
      $('res-title').textContent = kothLastResult.is_leader ? '🏆 Vedeš Free For All arénu!' : `🏟️ Free For All: #${kothLastResult.rank}. místo`;
    } else if (m === 'duel') {
      if (kothLastResult.resolved) {
        compGood = Boolean(kothLastResult.won_duel || kothLastResult.tied);
        $('res-title').textContent = kothLastResult.won_duel ? '⚔️ Vítězství v 1v1 souboji!' : kothLastResult.tied ? '🤝 Remíza v 1v1 souboji!' : '🛡️ Prohra v 1v1 souboji';
      } else {
        compGood = true;
        $('res-title').textContent = '⚔️ 1v1 výzva založena!';
      }
    } else {
      compGood = Boolean(kothLastResult.won_throne);
      $('res-title').textContent = kothLastResult.won_throne ? '👑 Jsi nový Král kopce!' : '🛡️ Král kopce ubránil trůn';
    }
  } else {
    $('res-title').textContent = examMode ? (passed ? 'Ostrý test splněn' : 'Ostrý test nesplněn')
      : sdEnd ? 'Konec hry' : suddenDeath ? 'Sada bez chyby' : 'Výsledky sady';
  }
  const p = $('res-pct'); p.innerHTML = pct + '<small>%</small>'; p.className = 'big-pct ' + (compGood ? 'good' : 'bad');
  if (kothMode && kothLastResult) {
    const m = kothLastResult.mode || compMode || 'koth';
    if (m === 'ffa') {
      $('res-detail').innerHTML = `<b>${kothLastResult.score} bodů (${correct} z ${n})</b>Umístění v aréně: #${kothLastResult.rank}`;
    } else if (m === 'duel') {
      $('res-detail').innerHTML = kothLastResult.resolved
        ? `<b>${kothLastResult.my_score} b. vs ${kothLastResult.opponent_score} b. (${esc(kothLastResult.opponent_username || 'Soupeř')})</b>`
        : `<b>${kothLastResult.my_score} bodů (${correct} z ${n})</b>Výzva #${kothLastResult.duel_id} čeká na soupeře`;
    } else {
      $('res-detail').innerHTML = `<b>${kothLastResult.challenger_score} bodů (${correct} z ${n})</b>${kothLastResult.won_throne ? 'Překonal jsi dosavadního krále!' : `Král drží ${kothLastResult.previous_king_score} b.`}`;
    }
  } else {
    $('res-detail').innerHTML = `<b>${correct} z ${n}</b>správně ze zodpovězených otázek`;
  }
  // řetězec 1/0 právě dokončené sady
  const rb = $('res-bits');
  rb.className = 'res-bits anim';
  rb.setAttribute('aria-label', `Průběh: ${correct} správně, ${n - correct} chybně`);
  rb.innerHTML = history.map((h, i) => {
    const last = sdEnd && i === n - 1;
    return `<span class="bit ${h.isCorrect ? 'ok' : 'bad'}${last ? ' stop' : ''}" style="animation-delay:${Math.min(i, 60) * 14}ms">${h.isCorrect ? '1' : '0'}</span>`;
  }).join('');
  const note = $('res-note'), mw = $('res-meter-wrap');
  mw.style.display = examMode ? 'block' : 'none';
  if (kothMode && kothLastResult) {
    const m = kothLastResult.mode || compMode || 'koth';
    if (m === 'ffa') {
      note.textContent = kothLastResult.is_leader
        ? `Skvělý výkon! Držíš 1. místo ve Free For All aréně se skóre ${kothLastResult.score} b.`
        : `Získal jsi ${kothLastResult.score} b. a jsi na #${kothLastResult.rank}. místě v aréně.`;
    } else if (m === 'duel') {
      note.textContent = kothLastResult.resolved
        ? (kothLastResult.won_duel ? `Porazil jsi hráče ${kothLastResult.opponent_username} (${kothLastResult.my_score} : ${kothLastResult.opponent_score} b.)!`
          : kothLastResult.tied ? `Souboj s hráčem ${kothLastResult.opponent_username} skončil remízou (${kothLastResult.my_score} b.).`
          : `Hráč ${kothLastResult.opponent_username} měl vyšší skóre (${kothLastResult.opponent_score} b. vs ${kothLastResult.my_score} b.).`)
        : `Tvoje 1v1 výzva byla uložena se skóre ${kothLastResult.my_score} b. Jakmile ji jiný hráč přijme, rozhodne se o vítězi!`;
    } else {
      note.textContent = kothLastResult.won_throne
        ? `Gratulace! Usadil ses na trůnu se skóre ${kothLastResult.challenger_score} b.`
        : `Na převzetí trůnu bylo potřeba překonat ${kothLastResult.previous_king_score} b. Zkus to znovu!`;
    }
  } else if (examMode) {
    const need = WASM_CORE.exp.calcExamNeeded(n | 0), diff = correct - need;
    $('res-meter').className = 'res-meter ' + (passed ? 'good' : 'bad');
    $('res-meter').firstChild.style.width = pct + '%';
    note.textContent = passed ? `Hranice 60 % je splněná, potřeba bylo ${need} správných.`
      : `Na hranici 60 % chybí ${-diff} ${-diff === 1 ? 'správná odpověď' : -diff < 5 ? 'správné odpovědi' : 'správných odpovědí'}, potřeba bylo ${need}.`;
  } else if (sdEnd) {
    note.textContent = `Hra skončila první chybou po ${correct} správných ${correct === 1 ? 'odpovědi' : 'odpovědích'}.`;
  } else if (suddenDeath) {
    note.textContent = 'Všechny otázky zvládnuté bez jediné chyby.';
  } else {
    note.textContent = n && correct === n ? 'Bez chyby.' : 'Správně je 1, chybně 0.';
  }
  const wrongIds = new Set(history.filter(h => !h.isCorrect).map(h => h.id));
  const wrongQ = FULL.concat(RECALL).filter(q => wrongIds.has(q.id));
  const wb = $('btn-wrong');
  if (wrongQ.length && !suddenDeath) { wb.style.display = 'block'; wb.textContent = `Procvičit jen chyby (${wrongQ.length})`; wb._wrongQ = wrongQ; }
  else wb.style.display = 'none';
  examMode = false;
  kothMode = false;
  compMode = null;
  activeDuelId = null;
}

function backFromResults() { if (fromChunks) showChunks(); else showMenu(); }
function restartSame() { beginSession([...queue], suddenDeath); }
function practiceWrong() { beginSession([...$('btn-wrong')._wrongQ], false); }

function clearSourceProgress() {
  openRevalidateModal('source');
}

document.addEventListener('keydown', e => {
  if ($('quiz').style.display === 'none') return;
  const inField = e.target.tagName === 'INPUT';
  if (e.key === 'Enter') { if (!$('btn-action').disabled) { e.preventDefault(); handleAction(); } }
  else if (inField) return;
  else if (e.key === 'ArrowRight') { if (!$('btn-action').disabled) handleAction(); }
  else if (e.key === 'ArrowLeft') { if (!$('btn-prev').disabled) prevQ(); }
  else { const k = e.key.toUpperCase(), key = /^[A-D]$/.test(k) && (optOrder[queue[idx]?.id] || [])[LETTERS.indexOf(k)]; if (key) toggleOpt(key); }
});
$('rand-count').addEventListener('keydown', e => { if (e.key === 'Enter') startRandom(); if (e.key === 'Escape') closeModal(); });

init();
