async function refreshUserStats() {
  updateNetStatus();
  if (!isOnline()) return;
  let data = null;
  try {
    const res = await fetch('/api/me');
    if (!res.ok) throw new Error('Not OK');
    data = await res.json();
    serverUnreachable = false;
    updateNetStatus();
  } catch (e) {
    serverUnreachable = true;
    updateNetStatus();
    return;
  }
  try {
    currentUserData = data;
    const xp = currentUserData.points || 0;
    const rk = getRankInfo(xp);
    const lvlEl = document.getElementById('u-lvl');
    if (lvlEl) lvlEl.textContent = String(rk.lvl);
    const titleEl = document.getElementById('u-rank-title');
    if (titleEl) titleEl.textContent = rk.title;
    const xpFill = document.getElementById('xp-bar-fill');
    if (xpFill) xpFill.style.width = `${rk.pct}%`;
    const xpEl = document.getElementById('u-xp');
    if (xpEl) xpEl.textContent = String(xp);
    const bestEl = document.getElementById('u-best-streak');
    if (bestEl) bestEl.textContent = String(currentUserData.best_streak || 0);

    if (currentUserData.role === 'trial') {
      document.getElementById('u-badge').textContent = 'Trial Guest';
      document.getElementById('u-score').textContent = 'Trial';
      document.getElementById('u-streak').textContent = '0';
    } else {
      document.getElementById('u-badge').textContent = currentUserData.username;
      document.getElementById('u-score').textContent = `${currentUserData.rank}. of ${currentUserData.total_users} (${xp} XP)`;
      document.getElementById('u-streak').textContent = String(currentUserData.streak || 0);
      renderDailyProgressUI(currentUserData);
    }
    if (currentUserData.role === 'admin') {
      const al = document.getElementById('admin-link');
      if (al) al.style.display = 'inline-flex';
    }
  } catch (e) {}
  refreshDailyProgress();
  refreshKothStatus();
}

// Initial theme load
(function initTheme() {
  const saved = localStorage.getItem('tzi_theme') || 'catppuccin';
  applyUserTheme(saved);
  if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
      const sw = document.getElementById('theme-switcher');
      if (sw) sw.value = saved;
    });
  }
})();

async function init() {
  updateNetStatus();
  refreshUserStats();
  syncOfflineQueue();
  prefetchBanksForOffline();

  try {
    const r = await fetch('/api/sources');
    const data = await r.json();
    sources = data.sources || [];
    currentSource = data.default || (sources[0] ? sources[0].id : '');
  } catch(e) {
    sources = [];
  }
  RECALL = await fetch('/api/recall').then(r => r.ok ? r.json() : []).catch(() => []);
  renderLectures();
  await loadSource(currentSource);
}

async function selectSource(id) { currentSource = id; renderLectures(); await loadSource(id); }

function updateTeorieLink() {
  const gl = document.getElementById('teorie-link');
  if (gl) gl.href = '/teorie?source=' + encodeURIComponent(currentSource || '_all');
}

// "3. přednáška (15. 10. 2026): Téma" → {n, date, title}; "Všechny dohromady" dostane Σ
function parseSource(s) {
  const m = /^(\d+)\. přednáška \((.+?)\): (.*)$/.exec(s.label);
  return m ? {n: m[1], date: m[2], title: m[3]} : {n: 'Σ', date: '', title: s.label};
}
const recallCats = () => [...new Set(RECALL.map(q => q.category))];
function selectRecallCat(i) { recallCat = i < 0 ? '' : recallCats()[i]; renderLectures(); applyFilter(); }
function renderLectures() {
  updateTeorieLink();
  const rc = typeFilter === 'recall';
  $('h-lec').textContent = rc ? 'Kategorie' : 'Přednáška';
  if (rc) { // doplňovačka: místo přednášek kategorie
    const row = (i, n, name, count, on) => `<li><button class="lec" onclick="selectRecallCat(${i})" aria-pressed="${on}">` +
      `<span class="n">${n}</span><span class="t">${esc(name)}</span><span class="d">${count}</span></button></li>`;
    $('lectures').innerHTML = recallCats().map((c, i) => row(i, i + 1, c, RECALL.filter(q => q.category === c).length, c === recallCat)).join('')
      + row(-1, 'Σ', 'Všechny kategorie', RECALL.length, !recallCat);
    return;
  }
  $('lectures').innerHTML = sources.map(s => {
    const p = parseSource(s);
    return `<li><button class="lec" onclick="selectSource('${esc(s.id)}')" aria-pressed="${s.id === currentSource}">` +
      `<span class="n">${esc(p.n)}</span><span class="t">${esc(p.title)}</span><span class="d">${esc(p.date)}</span></button></li>`;
  }).join('');
}

async function loadSource(source) {
  if (!source) return;
  try {
    const qr = await fetch(`/api/questions?source=${encodeURIComponent(source)}`);
    if (qr.ok) FULL = await qr.json();
  } catch (e) {}

  try {
    const pr = await fetch(`/api/progress?source=${encodeURIComponent(source)}`);
    if (pr.ok) {
      const pd = await pr.json();
      progress = pd.seen || {};
      session = pd.session || null;
    } else {
      throw new Error('Offline');
    }
  } catch (e) {
    try {
      const local = JSON.parse(localStorage.getItem('tzi_local_progress_' + source) || '{}');
      progress = local.seen || progress || {};
      session = local.session || null;
    } catch(err) {}
  }
  applyFilter();
}

function setType(t) {
  typeFilter = t;
  document.querySelectorAll('#type-row button').forEach(b => b.setAttribute('aria-pressed', b.dataset.t === t));
  renderLectures();
  applyFilter();
}

function applyFilter() {
  ALL = typeFilter === 'recall' ? RECALL.filter(q => !recallCat || q.category === recallCat) : typeFilter === 'all' ? FULL : FULL.filter(q => q.type === typeFilter); // doplňovačka: napříč přednáškami, místo přednášky se vybírá kategorie
  $('rand-count').max = ALL.length;
  $('rand-count').value = Math.min(10, ALL.length);
  updateMenuStats(true);
}

function updateMenuStats(animate) {
  const total = ALL.length;
  const good = ALL.filter(q => progress[q.id] === 'correct').length;
  const bad = ALL.filter(q => progress[q.id] === 'wrong').length;
  const unseen = total - good - bad;
  const blocks = Math.ceil(total / CHUNK_SIZE);
  $('bits-sum').textContent = `${total} ${plural(total, 'otázka', 'otázky', 'otázek')} v ${blocks} ${plural(blocks, 'bloku', 'blocích', 'blocích')}`;
  $('unseen-count').textContent = unseen;
  $('wrongs-count').textContent = bad;
  $('correct-count').textContent = good;
  $('c-all').textContent = total;
  $('c-blocks').textContent = blocks + '×';
  $('menu-chunk-size').textContent = CHUNK_SIZE;
  $('btn-unseen').disabled = unseen === 0;
  $('btn-wrongs').disabled = bad === 0;
  $('btn-correct').disabled = good === 0;
  $('btn-recall').style.display = RECALL.length ? '' : 'none'; // starý server /api/recall nemá
  const eligible = ALL.filter(q => !q.reveal);
  const n = Math.min(15, eligible.length), min = Math.max(5, Math.round(n * 2));
  $('exam-n').textContent = n;
  $('exam-min').textContent = min;
  $('exam-clock').textContent = String(min).padStart(2, '0') + ':00';
  const q = typeFilter !== 'recall' && session && session.idx < session.queue_ids.length ? FULL.find(x => x.id === session.queue_ids[session.idx]) : null;
  resumable = !!q;
  if (q) {
    $('go-title').textContent = `Pokračovat od otázky ${q.number}`;
    $('go-sub').textContent = `V rozdělané sadě zbývá ${session.queue_ids.length - session.idx} z ${session.queue_ids.length} otázek`;
  } else {
    $('go-title').textContent = 'Začít od první otázky';
    $('go-sub').textContent = total ? `${total} otázek popořadě` : 'Ve výběru nejsou žádné otázky';
  }
  renderBits(!!animate);
}
let resumable = false;
function goPrimary() { if (resumable) resumeSession(); else startAll(); }

// Postup jako binární řetězec: jeden řádek = jeden blok, 1 správně, 0 chybně, · nová.
function renderBits(animate) {
  let d = 0;
  const html = getChunks().map((qs, i) => {
    const cells = qs.map(q => {
      const s = progress[q.id];
      const k = s === 'correct' ? 'ok' : s === 'wrong' ? 'bad' : 'new';
      const c = k === 'ok' ? '1' : k === 'bad' ? '0' : '·';
      const delay = animate ? ` style="animation-delay:${(d++) * 9}ms"` : '';
      return `<span class="bit ${k}"${delay} title="Otázka ${esc(q.id)}">${c}</span>`;
    }).join('');
    return `<button class="brow" onclick="openBlock(${i})" aria-label="Blok ${i + 1}, otázky ${i * CHUNK_SIZE + 1} až ${i * CHUNK_SIZE + qs.length}"><b>${i + 1}</b><span class="cells">${cells}</span></button>`;
  }).join('');
  const el = $('bits');
  el.className = 'bits' + (animate ? ' anim' : '');
  el.innerHTML = html;
}
function openBlock(i) { const qs = getChunks()[i]; if (qs) showChunkDetail(qs, i); }

async function saveProgress() {
  const m = {};
  for (const h of history) m[h.id] = h.isCorrect ? 'correct' : 'wrong';
  const newProgress = Object.assign({}, progress, m);
  const recall = queue.length > 0 && isRecall(queue[0]); // doplňovačka: bez rozdělané sady, nesmí přepsat sadu přednášky
  const newSession = (idx < queue.length && !examMode && !kothMode && !recall) ? {queue_ids: queue.map(q => q.id), idx, sudden_death: suddenDeath, history} : null;
  const latestRec = history.length ? history[history.length - 1] : null;

  progress = newProgress;
  if (!recall && !kothMode) session = newSession;

  // Uložit lokálně pro offline režim
  try {
    localStorage.setItem('tzi_local_progress_' + (recall ? '_recall' : currentSource), JSON.stringify({seen: newProgress, session: newSession}));
  } catch(e) {}

  if (!isOnline()) {
    if (latestRec) {
      const qItem = { id: latestRec.id, user_answer: latestRec.userKeys, timestamp: Date.now() };
      const oq = getOfflineQueue();
      const filtered = oq.filter(item => item.id !== qItem.id);
      filtered.push(qItem);
      saveOfflineQueue(filtered);
    }
    updateNetStatus();
    return;
  }

  try {
    const payloadLatest = latestRec ? { id: latestRec.id, userKeys: latestRec.userKeys, isCorrect: latestRec.isCorrect } : null;
    const pRes = await fetch(`/api/progress?source=${encodeURIComponent(recall ? '_recall' : currentSource)}`, {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-TZI': '1'},
      body: JSON.stringify({seen: newProgress, session: newSession, latest: payloadLatest})
    });
    if (pRes.ok) {
      serverUnreachable = false;
      updateNetStatus();
      const pData = await pRes.json();
      if (pData && pData.score) {
        const s = pData.score;
        renderDailyProgressUI(s);
        let toastText = '';
        if (s.points_awarded > 0) {
          toastText = `<b>+${s.points_awarded} b.</b> (${s.difficulty})`;
          if (s.streak >= 5) toastText += ` 🔥 Streak ${s.streak}! (+${s.streak_bonus} b.)`;
        }
        if (s.daily_goal_just_met) {
          toastText += (toastText ? ' · ' : '') + `📅 Denní cíl splněn! Streak: <b>${s.daily_streak} dní</b>`;
        }
        if (toastText) showToast(toastText);
        refreshUserStats();
      }
    } else {
      throw new Error('Save failed');
    }
  } catch(e) {
    serverUnreachable = true;
    if (latestRec) {
      const qItem = { id: latestRec.id, user_answer: latestRec.userKeys, timestamp: Date.now() };
      const oq = getOfflineQueue();
      const filtered = oq.filter(item => item.id !== qItem.id);
      filtered.push(qItem);
      saveOfflineQueue(filtered);
    }
    updateNetStatus();
  }
}

let fromChunks = false;
function showMenu() { show('menu'); stopRoomPolling(); kothMode = false; activeRoomId = null; activeRoomData = null; if ($('room-results-board')) $('room-results-board').style.display = 'none'; updateMenuStats(false); refreshDailyProgress(); refreshKothStatus(); show('menu'); }
function showResults() { show('results'); renderResults(); }

