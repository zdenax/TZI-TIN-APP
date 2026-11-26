// Sdílený mini-markdown pro glosar.html (mdRender(body, true)) a vypisky.html (mdRender(body)). Potřebuje fmt.js.
// Umí odstavce, odrážky, tabulky; v plném režimu i číslované seznamy, callouty „> [!typ]± název“ (vnořené),
// display matematiku „@@ text“ a blok „{small}“ … „{/small}“. Formát generuje build_vypisky.py.
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const gInline = t => fmt(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\*(.+?)\*/g, '<i>$1</i>').replace(/`(.+?)`/g, '<code>$1</code>')
  .replace(//g, '<u>').replace(//g, '</u>');

const CO_LABEL = { info: 'Info', note: 'Poznámka', warning: 'Pozor', important: 'Důležité', example: 'Příklad', success: 'Řešení' };

function mdCallout(q) {
  const m = q[0].match(/^\[!(\w+)\]([+-]?)\s*(.*)$/);
  if (!m) return `<blockquote>${mdBlocks(q, false).join('')}</blockquote>`;
  const type = m[1].toLowerCase(), fold = m[2], title = m[3];
  const ai = /Doplněno z Claude/.test(title);
  const t = ai && title.match(/^(🤖\s*Doplněno z Claude[^:]*)(?::\s*(.*))?$/);
  const head = t ? `<span class="ai-tag">${gInline(t[1])}</span>${t[2] ? `<span class="co-t">${gInline(t[2])}</span>` : ''}`
    : `<span class="co-t">${title ? gInline(title) : CO_LABEL[type] || type}</span>`;
  const body = mdBlocks(q.slice(1), false).join('');
  const cls = `co co-${esc(type)}${ai ? ' ai' : ''}`;
  if (fold) return `<details class="${cls}"${fold === '+' ? ' open' : ''}><summary class="co-h">${head}</summary><div class="co-b">${body}</div></details>`;
  return `<div class="${cls}"><div class="co-h">${head}</div>${body ? `<div class="co-b">${body}</div>` : ''}</div>`;
}

function mdBlocks(L, flat) {
  const out = [], run = (re, i) => { const a = []; for (; i < L.length && re.test(L[i]); i++) a.push(L[i]); return a; };
  for (let i = 0; i < L.length; i++) {
    const l = L[i];
    if (!flat && /^>/.test(l)) {
      const q = run(/^>/, i); i += q.length - 1;
      out.push(mdCallout(q.map(x => x.replace(/^>\s?/, ''))));
    } else if (/^\|/.test(l)) {
      const rows = run(/^\|/, i).filter(r => !/^\|[\s|:-]+$/.test(r)); i += run(/^\|/, i).length - 1;
      const t = '<table>' + rows.map((r, k) => '<tr>' + r.replace(/^\||\|$/g, '').split('|').map(c => `<${k ? 'td' : 'th'}>${gInline(c.trim())}</${k ? 'td' : 'th'}>`).join('') + '</tr>').join('') + '</table>';
      out.push(flat ? t : `<div class="tw">${t}</div>`);
    } else if (/^- /.test(l)) {
      const items = run(/^- /, i); i += items.length - 1;
      out.push('<ul>' + items.map(x => `<li>${gInline(x.slice(2))}</li>`).join('') + '</ul>');
    } else if (!flat && /^\d+\. /.test(l)) {
      const items = run(/^\d+\. /, i); i += items.length - 1;
      out.push(`<ol start="${parseInt(l, 10)}">` + items.map(x => `<li>${gInline(x.replace(/^\d+\. /, ''))}</li>`).join('') + '</ol>');
    } else if (!flat && /^@@ /.test(l)) {
      const rows = run(/^@@ /, i); i += rows.length - 1;
      out.push('<div class="dm">' + rows.map(r => `<div>${gInline(r.slice(3))}</div>`).join('') + '</div>');
    } else if (!flat && l === '{small}') {
      const e = L.indexOf('{/small}', i);
      out.push(`<div class="small">${mdBlocks(L.slice(i + 1, e < 0 ? L.length : e), false).join('')}</div>`);
      i = e < 0 ? L.length : e;
    } else if (l.trim()) {
      out.push(`<p${/^\*Zdroj/.test(l) ? ' class="src"' : !flat && /^\*🤖/.test(l) ? ' class="ai-note"' : ''}>${gInline(l)}</p>`);
    }
  }
  return out;
}

// flat = glosář: citace ztratí předponu, popisek „[!warning] Název“ je tučně
function mdRender(body, flat) {
  let L = body.split('\n');
  if (flat) L = L.map(l => l.replace(/^>\s?(\[![a-z]+\]\s*(.*))?/, (m, c, t) => c ? (t ? `**${t}**` : '') : ''));
  return mdBlocks(L, flat).join('');
}
