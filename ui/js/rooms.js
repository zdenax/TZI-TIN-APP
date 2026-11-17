function renderFfaUI(st) {
  if (!st) return;
  const leader = st.leader;
  const nameEl = document.getElementById('ffa-leader-name');
  const subEl = document.getElementById('ffa-leader-sub');
  const badgeEl = document.getElementById('ffa-players-badge');
  const scoreEl = document.getElementById('ffa-leader-score');
  if (leader && leader.username) {
    if (nameEl) nameEl.textContent = `Lídr: ${leader.username}`;
    if (subEl) subEl.textContent = `${leader.best_correct || 0} správně (${Math.round((leader.best_time_ms || 0) / 1000)}s)`;
    if (scoreEl) scoreEl.textContent = `${leader.best_score || 0} b.`;
  } else {
    if (nameEl) nameEl.textContent = 'Aréna je otevřená!';
    if (subEl) subEl.textContent = '10 otázek o nejvyšší skóre';
    if (scoreEl) scoreEl.textContent = '0 b.';
  }
  if (badgeEl) badgeEl.textContent = `${st.total_players || 0} hráčů`;
}

function renderDuelUI(st) {
  if (!st) return;
  const openList = Array.isArray(st.open_challenges) ? st.open_challenges : [];
  const lb = Array.isArray(st.leaderboard) ? st.leaderboard : [];
  const nameEl = document.getElementById('duel-status-name');
  const subEl = document.getElementById('duel-status-sub');
  const badgeEl = document.getElementById('duel-open-badge');
  const winsEl = document.getElementById('duel-top-wins');
  if (openList.length > 0) {
    const ch = openList[0];
    if (nameEl) nameEl.textContent = `Výzva od: ${ch.creator_username}`;
    if (subEl) subEl.textContent = `Skóre k překonání: ${ch.creator_score} b.`;
  } else {
    if (nameEl) nameEl.textContent = 'Založ novou 1v1 výzvu';
    if (subEl) subEl.textContent = 'Vyzvi soupeře na stejných 10 otázkách';
  }
  if (badgeEl) badgeEl.textContent = `${openList.length} otevřených`;
  if (winsEl) winsEl.textContent = lb.length > 0 ? `🏆 ${lb[0].wins}×` : '1v1';
}

function renderKothUI(st, overview) {
  if (!st) return;
  const king = st.king;
  const nameEl = document.getElementById('koth-king-name');
  const subEl = document.getElementById('koth-king-sub');
  const scoreEl = document.getElementById('koth-king-score');
  const defEl = document.getElementById('koth-defenses-badge');
  if (king && king.username) {
    if (nameEl) nameEl.textContent = `Král: ${king.username}`;
    if (subEl) subEl.textContent = `${king.correct || 0} správně (${Math.round((king.time_ms || 0) / 1000)}s)`;
    if (scoreEl) scoreEl.textContent = `${king.score} b.`;
    if (defEl) defEl.textContent = `obhájení ${king.defenses_count || 0}×`;
  } else {
    if (nameEl) nameEl.textContent = 'Kopec je volný!';
    if (subEl) subEl.textContent = '10 otázek na čas';
    if (scoreEl) scoreEl.textContent = '0 b.';
    if (defEl) defEl.textContent = '0×';
  }
  const listEl = document.getElementById('koth-history-list');
  if (listEl) {
    const items = [];
    const duelSt = overview && overview.duel ? overview.duel : null;
    const ffaSt = overview && overview.ffa ? overview.ffa : null;
    if (duelSt && Array.isArray(duelSt.open_challenges)) {
      duelSt.open_challenges.slice(0, 2).forEach(ch => {
        items.push(`<li><span>⚔️ <b>1v1 výzva: ${esc(ch.creator_username)}</b> (${ch.creator_score} b.)</span><span><button class="lnk" onclick="startCompetitiveMode('duel', ${Number(ch.id)})">Přijmout 1v1</button></span></li>`);
      });
    }
    if (duelSt && Array.isArray(duelSt.recent_duels)) {
      duelSt.recent_duels.slice(0, 2).forEach(d => {
        const winTxt = d.winner_username ? `🏆 ${esc(d.winner_username)}` : '🤝 Remíza';
        items.push(`<li><span>⚔️ 1v1: <b>${esc(d.creator_username)}</b> (${d.creator_score}) vs <b>${esc(d.opponent_username)}</b> (${d.opponent_score})</span><span><b>${winTxt}</b></span></li>`);
      });
    }
    if (ffaSt && Array.isArray(ffaSt.leaderboard) && ffaSt.leaderboard.length > 0) {
      const topFfa = ffaSt.leaderboard.slice(0, 2).map((r, i) => `#${i+1} ${esc(r.username)} (${r.best_score} b.)`).join(' · ');
      items.push(`<li><span>🏟️ <b>FFA TOP:</b> ${topFfa}</span><span><b>${ffaSt.total_players} hráčů</b></span></li>`);
    }
    if (Array.isArray(st.recent_matches)) {
      st.recent_matches.slice(0, 3).forEach(m => {
        items.push(`<li><span>${m.won_throne ? '👑' : '🛡️'} KotH: <b>${esc(m.challenger_username)}</b> (${m.correct_count}/${m.total_questions})</span><span><b>${m.challenger_score} b.</b></span></li>`);
      });
    }
    listEl.innerHTML = items.slice(0, 6).join('');
  }
}

let roomCountdownTimer = null;
let roomDeadlineMs = null;

function formatRoomCountdown(secs) {
  const s = Math.max(0, Math.floor(Number(secs) || 0));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}

function updateRoomCountdownLabel() {
  const el = $('rl-timer');
  if (!el) return;
  if (roomDeadlineMs == null) {
    el.textContent = '';
    el.classList.remove('warn');
    return;
  }
  const remSec = Math.max(0, Math.ceil((roomDeadlineMs - Date.now()) / 1000));
  el.textContent = `⏱ Limit ${formatRoomCountdown(remSec)}`;
  el.classList.toggle('warn', remSec <= 60);
}

function handleRoomExpired() {
  stopRoomPolling();
  activeRoomId = null;
  activeRoomData = null;
  showToast('⏰ Lobby vypršelo (limit 5 minut bez spuštění).');
  openCompArena();
}

function modeBadgeLabel(m) {
  return m === 'ffa' ? 'FFA' : m === 'duel' ? '1v1 Duel' : 'King of the Hill';
}

function renderRoomsListUI(roomsData) {
  const listEl = document.getElementById('comp-rooms-list');
  const badgeEl = document.getElementById('rooms-count-badge');
  if (!listEl) return;
  const active = roomsData && Array.isArray(roomsData.active_rooms) ? roomsData.active_rooms : [];
  const waiting = active.filter(r => r.status === 'waiting');
  if (badgeEl) badgeEl.textContent = `${waiting.length} otevřených`;
  if (!active.length) {
    listEl.innerHTML = `<li class="room-row"><span class="room-row-meta">Žádná aktivní místnost – vytvoř novou roomku výše a počkej na hráče nebo ji spusť jako 👑!</span></li>`;
    return;
  }
  const myUid = currentUserData ? currentUserData.user_id : 0;
  listEl.innerHTML = active.slice(0, 6).map(r => {
    const isMember = Array.isArray(r.players) && r.players.some(p => p.user_id === myUid);
    const playersNames = Array.isArray(r.players) ? r.players.map(p => (p.is_host ? '👑 ' : '') + esc(p.username)).join(', ') : '';
    const expText = (r.status === 'waiting' && typeof r.expires_in_seconds === 'number')
      ? ` · ⏱ ${formatRoomCountdown(r.expires_in_seconds)}`
      : '';
    const btnLabel = r.status === 'waiting'
      ? (isMember ? 'Otevřít lobby 👑' : 'Připojit se')
      : (isMember ? 'Probíhá (Vstoupit)' : 'Probíhá');
    const canClick = r.status === 'waiting' || isMember;
    return `<li class="room-row">
      <div>
        <div><b>${modeBadgeLabel(r.mode)} · ${esc(r.name)}</b> <span class="room-row-meta">(${r.player_count}/${r.max_players} hráčů · ${r.question_count} ot.${expText})</span></div>
        <div class="room-row-meta">Hráči: ${playersNames || esc(r.host_username)}</div>
      </div>
      ${canClick ? `<button type="button" class="room-join-btn" onclick="joinCompRoom(${Number(r.id)})">${btnLabel}</button>` : `<span class="room-row-meta">Hraje se</span>`}
    </li>`;
  }).join('');
}

async function refreshKothStatus() {
  if (!isOnline()) {
    updateCompArenaMenuState();
    return;
  }
  try {
    const res = await fetch('/api/competitive/overview');
    if (res.ok) {
      serverUnreachable = false;
      const ov = await res.json();
      if (ov.ffa) renderFfaUI(ov.ffa);
      if (ov.duel) renderDuelUI(ov.duel);
      if (ov.koth) renderKothUI(ov.koth, ov);
      if (ov.rooms) renderRoomsListUI(ov.rooms);
      const waitingCount = ov.rooms && Array.isArray(ov.rooms.active_rooms) ? ov.rooms.active_rooms.filter(r => r.status === 'waiting').length : 0;
      const kingUser = ov.koth && ov.koth.king ? ov.koth.king.username : null;
      updateCompArenaMenuState(waitingCount, kingUser);
      return;
    } else {
      updateCompArenaMenuState();
    }
  } catch (e) {
    updateCompArenaMenuState();
  }
  try {
    const res = await fetch('/api/koth/status');
    if (res.ok) {
      const st = await res.json();
      renderKothUI(st);
    }
  } catch (e) {}
}

function stopRoomPolling() {
  if (roomPollTimer) {
    clearInterval(roomPollTimer);
    roomPollTimer = null;
  }
  if (roomCountdownTimer) {
    clearInterval(roomCountdownTimer);
    roomCountdownTimer = null;
  }
  roomDeadlineMs = null;
}

function renderRoomLobbyView(room) {
  if (!room) return;
  activeRoomData = room;
  activeRoomId = room.id;
  if (room.status === 'waiting' && typeof room.expires_in_seconds === 'number') {
    roomDeadlineMs = Date.now() + room.expires_in_seconds * 1000;
    updateRoomCountdownLabel();
    if (!roomCountdownTimer) {
      roomCountdownTimer = setInterval(updateRoomCountdownLabel, 1000);
    }
  } else {
    roomDeadlineMs = null;
    if (roomCountdownTimer) {
      clearInterval(roomCountdownTimer);
      roomCountdownTimer = null;
    }
    updateRoomCountdownLabel();
  }
  const myUid = currentUserData ? currentUserData.user_id : 0;
  const isHost = room.host_id === myUid || (Array.isArray(room.players) && room.players.some(p => p.user_id === myUid && p.is_host));
  if ($('rl-mode-badge')) $('rl-mode-badge').textContent = `${modeBadgeLabel(room.mode)} · MÍSTNOST #${room.id}`;
  if ($('rl-title')) $('rl-title').textContent = room.name;
  if ($('rl-subtitle')) $('rl-subtitle').textContent = `${room.question_count} otázek na čas · Zakladatel: 👑 ${room.host_username}`;
  if ($('rl-player-count')) $('rl-player-count').textContent = `${room.player_count}/${room.max_players}`;
  if ($('rl-status-banner')) {
    $('rl-status-banner').textContent = isHost
      ? (room.player_count > 1
          ? `✅ Připojeno ${room.player_count} hráčů! Jako 👑 hostitel můžeš hru kdykoliv odstartovat.`
          : `⏳ Čeká se na připojení dalšího hráče do místnosti, nebo hru odstartuj rovnou tlačítkem 👑 Spustit hru hned.`)
      : `⏳ Čeká se, až se připojí další hráči nebo 👑 ${room.host_username} spustí hru...`;
  }
  const plEl = $('rl-players-list');
  if (plEl && Array.isArray(room.players)) {
    plEl.innerHTML = room.players.map(p => `
      <li>
        <span>${p.is_host ? '👑' : '👤'} <b>${esc(p.username)}</b> ${p.is_host ? '<small style="color:var(--muted)">(Hostitel)</small>' : ''}</span>
        <span style="font-family:var(--mono);font-size:.8rem;color:var(--ok);">Připraven</span>
      </li>
    `).join('');
  }
  const startBtn = $('btn-rl-start');
  if (startBtn) {
    startBtn.style.display = isHost ? 'inline-block' : 'none';
    startBtn.textContent = room.player_count > 1 ? `👑 Spustit hru (${room.player_count} hráčů)` : '👑 Spustit hru hned';
  }
}

function launchRoomQuiz(room, questions) {
  stopRoomPolling();
  let qs = Array.isArray(questions) && questions.length ? questions : [];
  if (!qs.length && room && Array.isArray(room.question_ids) && room.question_ids.length) {
    const idSet = new Set(room.question_ids.map(String));
    qs = FULL.filter(q => idSet.has(String(q.id)));
  }
  if (!qs.length) {
    qs = shuffle(ALL.filter(q => !q.reveal)).slice(0, (room && room.question_count) || 10);
  }
  if (!qs.length) return;
  queue = qs; idx = 0; history = []; optOrder = {};
  suddenDeath = false; studyMode = false; examMode = false;
  kothMode = true;
  compMode = (room && room.mode) || 'ffa';
  activeRoomId = room ? room.id : activeRoomId;
  activeRoomData = room || activeRoomData;
  kothStartTime = Date.now(); kothLastResult = null;
  const pNames = room && Array.isArray(room.players) ? room.players.map(p => (p.is_host ? '👑' : '') + esc(p.username)).join(' vs ') : '';
  $('sudden-banner').innerHTML = `${modeBadgeLabel(compMode)} · ${esc(room ? room.name : 'Místnost')}<span>Hráči v místnosti: ${pNames}</span>`;
  $('sudden-banner').style.display = 'block';
  show('quiz');
  renderQ();
}

function startRoomLobbyPolling(roomId) {
  if (roomPollTimer) {
    clearInterval(roomPollTimer);
    roomPollTimer = null;
  }
  updateRoomCountdownLabel();
  if (!roomCountdownTimer && roomDeadlineMs != null) {
    roomCountdownTimer = setInterval(updateRoomCountdownLabel, 1000);
  }
  roomPollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/rooms/${roomId}`);
      if (!res.ok) {
        if (res.status === 404) {
          handleRoomExpired();
          return;
        }
        stopRoomPolling();
        return;
      }
      const data = await res.json();
      if (!data.room) return;
      if (data.room.status === 'in_progress') {
        launchRoomQuiz(data.room, data.questions);
        return;
      }
      renderRoomLobbyView(data.room);
    } catch (e) {}
  }, 1500);
}

async function createRoomFromUI(forcedMode = null) {
  if (currentUserData && currentUserData.role === 'trial') {
    showToast('⚠️ Pro vytvoření kompetitivní místnosti je nutné se přihlásit.');
    return;
  }
  const modeSel = document.getElementById('room-mode-select');
  const nameInp = document.getElementById('room-name-input');
  const mode = forcedMode || (modeSel ? modeSel.value : 'ffa');
  const name = nameInp ? nameInp.value.trim() : '';
  try {
    const res = await fetch('/api/rooms/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-TZI': '1'},
      body: JSON.stringify({ mode, name, count: 10, source: currentSource })
    });
    if (!res.ok) {
      showToast('⚠️ Nepodařilo se vytvořit místnost.');
      return;
    }
    const data = await res.json();
    if (nameInp) nameInp.value = '';
    renderRoomLobbyView(data.room);
    show('room-lobby');
    startRoomLobbyPolling(data.room.id);
    refreshKothStatus();
  } catch (e) {
    showToast('⚠️ Chyba spojení při vytváření místnosti.');
  }
}

async function joinCompRoom(roomId) {
  if (currentUserData && currentUserData.role === 'trial') {
    showToast('⚠️ Pro připojení do místnosti je nutné se přihlásit.');
    return;
  }
  const autoChk = document.getElementById('room-autostart-chk');
  const autoStartDuel = autoChk ? autoChk.checked : true;
  try {
    const res = await fetch(`/api/rooms/${roomId}/join`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-TZI': '1'},
      body: JSON.stringify({ auto_start_duel: autoStartDuel })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast('⚠️ ' + (err.detail || 'Nelze se připojit do místnosti.'));
      refreshKothStatus();
      return;
    }
    const data = await res.json();
    if (data.room && data.room.status === 'in_progress') {
      launchRoomQuiz(data.room, data.questions);
      return;
    }
    renderRoomLobbyView(data.room);
    show('room-lobby');
    startRoomLobbyPolling(roomId);
  } catch (e) {}
}

async function startActiveRoomByHost() {
  if (!activeRoomId) return;
  try {
    const res = await fetch(`/api/rooms/${activeRoomId}/start`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-TZI': '1'}
    });
    if (res.ok) {
      const data = await res.json();
      launchRoomQuiz(data.room, data.questions);
    } else {
      const err = await res.json().catch(() => ({}));
      if (res.status === 404 || (err.detail && err.detail.includes('vypršela'))) {
        handleRoomExpired();
        return;
      }
      showToast('⚠️ ' + (err.detail || 'Hru může spustit pouze 👑 hostitel.'));
    }
  } catch (e) {}
}

async function leaveActiveRoom() {
  stopRoomPolling();
  const rid = activeRoomId;
  activeRoomId = null;
  activeRoomData = null;
  if (rid) {
    try {
      await fetch(`/api/rooms/${rid}/leave`, { method: 'POST', headers: {'X-TZI': '1'} });
    } catch (e) {}
  }
  openCompArena();
}

function renderRoomStandingsBoard(room) {
  const wrap = $('room-results-board');
  const list = $('room-results-list');
  if (!wrap || !list || !room || !Array.isArray(room.players)) {
    if (wrap) wrap.style.display = 'none';
    return;
  }
  wrap.style.display = 'block';
  list.innerHTML = room.players.map((p, i) => {
    const st = p.status === 'finished' ? `<b>${p.score} b.</b> (${p.correct_count}/${p.total_questions} · ${Math.round((p.time_ms || 0)/1000)}s)` : '⏳ Hraje...';
    const crown = i === 0 && p.status === 'finished' ? '🏆 ' : (p.is_host ? '👑 ' : '');
    return `<li><span>#${i+1} ${crown}<b>${esc(p.username)}</b></span><span>${st}</span></li>`;
  }).join('');
}

