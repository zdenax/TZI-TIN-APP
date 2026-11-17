let currentUserData = null;

function getCsrfToken() {
  if (typeof document !== 'undefined' && document.cookie) {
    const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (m && m[1]) return decodeURIComponent(m[1]);
  }
  if (currentUserData && currentUserData.csrf_token) {
    return currentUserData.csrf_token;
  }
  return '';
}

if (typeof window !== 'undefined' && typeof window.fetch === 'function') {
  const _origFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const sameOrigin = url.startsWith('/') || url.startsWith(window.location.origin);
    if (sameOrigin && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const nextInit = { ...(init || {}) };
      const headers = new Headers(nextInit.headers || (typeof Request !== 'undefined' && input instanceof Request ? input.headers : undefined));
      const tok = getCsrfToken();
      if (tok && !headers.has('X-CSRF-Token')) headers.set('X-CSRF-Token', tok);
      nextInit.headers = headers;
      return _origFetch(input, nextInit);
    }
    return _origFetch(input, init);
  };
}

function showToast(html) {
  const t = document.getElementById('score-toast');
  if (!t) return;
  t.innerHTML = html;
  t.classList.add('visible');
  setTimeout(() => t.classList.remove('visible'), 2800);
}

function applyUserTheme(th) {
  const valid = ['catppuccin', 'dark', 'amoled', 'light', 'auto'].includes(th) ? th : 'catppuccin';
  try { localStorage.setItem('tzi_theme', valid); } catch (_) {}
  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.setAttribute('data-theme', valid);
    const tc = document.querySelector('meta[name="theme-color"]');
    if (tc) {
      const darkPref = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
      const bgMap = { catppuccin: '#1e1e2e', dark: '#141415', amoled: '#000000', light: '#EEF2F6', auto: darkPref ? '#EEF2F6' : '#141415' };
      tc.setAttribute('content', bgMap[valid] || '#1e1e2e');
    }
  }
}

// PWA Service Worker Registration
if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator && typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(e => console.warn('[TZI] SW reg failed:', e));
  });
}

const OFFLINE_QUEUE_KEY = 'tzi_offline_sync_queue';

function getOfflineQueue() {
  try { return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]'); }
  catch(e) { return []; }
}

function saveOfflineQueue(q) {
  try { localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(q)); }
  catch(e) {}
  updateNetStatus();
}

let forceOffline = localStorage.getItem('tzi_force_offline') === '1';
let serverUnreachable = false;
const isOnline = () => !forceOffline && (typeof navigator === 'undefined' || navigator.onLine !== false);

function toggleOfflineMode() {
  if (!forceOffline && serverUnreachable) {
    forceOffline = false;
    serverUnreachable = false;
  } else {
    forceOffline = !forceOffline;
    if (!forceOffline) serverUnreachable = false;
  }
  localStorage.setItem('tzi_force_offline', forceOffline ? '1' : '0');
  updateNetStatus();
  if (!forceOffline && isOnline()) {
    showToast('Switched to <b>Online mode</b>. Syncing...');
    syncOfflineQueue();
    refreshUserStats();
  } else {
    showToast('Switched to <b>Offline mode</b>. Progress is saved locally.');
  }
}

function updateNetStatus() {
  const netEl = document.getElementById('u-net');
  if (!netEl) return;
  const q = getOfflineQueue();
  netEl.style.display = 'inline-flex';
  if (!isOnline() || serverUnreachable) {
    netEl.className = 'badge-net badge-net-offline';
    netEl.textContent = `Offline${forceOffline ? ' (manual)' : ''}${q.length ? ` · ${q.length}` : ''}`;
    netEl.title = 'Offline režim: postup se ukládá v prohlížeči a odešle se po připojení (klikni pro přepnutí)';
  } else if (isSyncing || q.length > 0) {
    netEl.className = 'badge-net badge-net-sync';
    netEl.textContent = `Syncing (${q.length})...`;
    netEl.title = 'Probíhá synchronizace offline odpovědí se serverem';
  } else {
    netEl.className = 'badge-net badge-net-online';
    netEl.textContent = 'Online';
    netEl.title = 'Online režim: spojení se serverem je aktivní (kliknutím lze přepnout do Offline režimu)';
  }
  updateCompArenaMenuState();
}

