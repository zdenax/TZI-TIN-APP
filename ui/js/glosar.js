try {
  const th = localStorage.getItem('tzi_theme');
  if (th === 'light' || th === 'dark') document.documentElement.setAttribute('data-theme', th);
} catch (e) {}

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));
function gInlineSeg(str) {
  const out = [];
  let pos = 0;
  const re = /(?:^|(?<=[\s(>„"']))\*(?!\*)((?:[^*\n]|\*\*[^*\n]+?\*\*)+?)(?<!\*)\*(?=$|[\s.,:;!?)"“'<])|\*\*(.+?)\*\*/g;
  for (const m of str.matchAll(re)) {
    if (m.index > pos) out.push(fmt(str.slice(pos, m.index)));
    if (m[1] !== undefined) out.push(`<i>${gInlineSeg(m[1])}</i>`);
    else out.push(`<b>${gInlineSeg(m[2])}</b>`);
    pos = m.index + m[0].length;
  }
  if (pos < str.length) out.push(fmt(str.slice(pos)));
  return out.join('');
}
function gInline(raw) {
  return String(raw ?? '').split(/(`[^`\n]+`)/g).map(part =>
    part.startsWith('`') && part.endsWith('`') && part.length >= 2
      ? `<code>${esc(part.slice(1, -1))}</code>`
      : gInlineSeg(part)
  ).join('');
}

// pojmy jsou jednoduchý markdown: odstavce, odrážky, tabulky; citace (> ...) ztratí předponu, popisek „[!warning] Název“ je tučně
function gBody(body) {
  const out = [], L = String(body ?? '').split('\n').map(l => l.replace(/^>\s?(\[![a-z]+\]\s*(.*))?/, (m, c, t) => c ? (t ? `**${t}**` : '') : ''));
  for (let i = 0; i < L.length; i++) {
    const l = L[i];
    if (/^\|/.test(l)) {
      const rows = [];
      for (; i < L.length && /^\|/.test(L[i]); i++) if (!/^\|[\s|:-]+$/.test(L[i])) rows.push(L[i].replace(/^\||\|$/g, '').split('|'));
      i--;
      out.push('<table>' + rows.map((r, k) => '<tr>' + r.map(c => {
        const raw = c.trim();
        if (k) return `<td>${gInline(raw)}</td>`;
        const h = gInline(raw);
        if (!raw) return `<th scope="col"><span class="sr-only">Sloupec</span></th>`;
        return h.includes('<math') ? `<th scope="col"><span class="sr-only">${esc(raw)}</span><span aria-hidden="true">${h}</span></th>` : `<th scope="col">${h}</th>`;
      }).join('') + '</tr>').join('') + '</table>');
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
