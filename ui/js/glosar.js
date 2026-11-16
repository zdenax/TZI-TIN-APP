const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));
const gInline = t => fmt(String(t ?? '')).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\*(.+?)\*/g, '<i>$1</i>').replace(/`(.+?)`/g, '<code>$1</code>');

// pojmy jsou jednoduchý markdown: odstavce, odrážky, tabulky; citace (> ...) ztratí předponu, popisek „[!warning] Název“ je tučně
function gBody(body) {
  const out = [], L = String(body ?? '').split('\n').map(l => l.replace(/^>\s?(\[![a-z]+\]\s*(.*))?/, (m, c, t) => c ? (t ? `**${t}**` : '') : ''));
  for (let i = 0; i < L.length; i++) {
    const l = L[i];
    if (/^\|/.test(l)) {
      const rows = [];
      for (; i < L.length && /^\|/.test(L[i]); i++) if (!/^\|[\s|:-]+$/.test(L[i])) rows.push(L[i].replace(/^\||\|$/g, '').split('|'));
      i--;
      out.push('<table>' + rows.map((r, k) => '<tr>' + r.map(c => `<${k ? 'td' : 'th'}>${gInline(c.trim())}</${k ? 'td' : 'th'}>`).join('') + '</tr>').join('') + '</table>');
    } else if (/^- /.test(l)) {
      const items = [];
      for (; i < L.length && /^- /.test(L[i]); i++) items.push(L[i].slice(2));
      i--;
      out.push('<ul>' + items.map(x => `<li>${gInline(x)}</li>`).join('') + '</ul>');
    } else if (l.trim()) {
      out.push(`<p${/^\*Zdroj/.test(l) ? ' class="src"' : ''}>${gInline(l)}</p>`);
    }
  }
  return out.join('');
}

(async () => {
  const outEl = document.getElementById('out');
  const showEmpty = msg => {
    outEl.textContent = '';
    const p = document.createElement('p');
    p.className = 'empty';
    p.textContent = msg;
    outEl.appendChild(p);
  };
  const rawSource = new URLSearchParams(location.search).get('source') || '_all';
  const source = /^[A-Za-z0-9_-]{1,64}$/.test(rawSource) ? rawSource : '_all';
  let r;
  try {
    r = await fetch('/api/teorie?source=' + encodeURIComponent(source), { credentials: 'same-origin' });
  } catch (_) {
    showEmpty('Teorii se nepodařilo načíst.');
    return;
  }
  if (!r.ok) { showEmpty('Teorii se nepodařilo načíst.'); return; }
  let d;
  try {
    d = await r.json();
  } catch (_) {
    showEmpty('Neplatná odpověď serveru.');
    return;
  }
  if (!d || typeof d.title !== 'string' || !Array.isArray(d.groups)) {
    showEmpty('Neplatná data teorie.');
    return;
  }
  document.getElementById('sub').textContent = d.title;
  document.title = `Teorie: ${d.title} · TZI Trenér`;
  const multi = d.groups.length > 1;
  if (!d.groups.length) {
    showEmpty('K téhle přednášce zatím není v teorii žádný obsah.');
    return;
  }
  outEl.innerHTML = d.groups.map(g => {
    const entries = Array.isArray(g && g.entries) ? g.entries : [];
    return (multi ? `<h2>${esc(g && g.label)}</h2>` : '') +
      entries.map(e => `<div class="entry"><h3>${gInline(e && e.term)}</h3>${gBody(e && e.body)}</div>`).join('');
  }).join('');
})();
