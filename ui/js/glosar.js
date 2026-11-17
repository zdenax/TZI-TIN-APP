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

const ICO_WARN = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
const ICO_X = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
const ICO_CHECK = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><polyline points="8.5 12.5 11 15 15.5 9.5"/></svg>';
const ICO_CHEV = '<svg class="chev ico" viewBox="0 0 24 24" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>';

let _gTblSeq = 0;

function gTable(lines, label) {
  let aligns = [];
  const rows = [];
  for (const l of lines) {
    if (/^\|[\s|:-]+\|?\s*$/.test(l)) {
      aligns = l.replace(/^\||\|$/g, '').split('|').map(c => {
        const s = c.trim();
        if (s.startsWith(':') && s.endsWith(':')) return 'col-c';
        if (s.endsWith(':')) return 'col-r';
        return '';
      });
      continue;
    }
    rows.push(l.replace(/^\||\|$/g, '').split('|'));
  }
  if (!rows.length) return '';
  const head = rows[0].map((c, idx) => {
    const raw = c.trim();
    const cls = aligns[idx] ? ` class="${aligns[idx]}"` : '';
    const h = gInline(raw);
    if (!raw) return `<th scope="col"${cls}><span class="sr-only">Sloupec</span></th>`;
    return h.includes('<math')
      ? `<th scope="col"${cls}><span class="sr-only">${esc(raw)}</span><span aria-hidden="true">${h}</span></th>`
      : `<th scope="col"${cls}>${h}</th>`;
  }).join('');
  const body = rows.slice(1).map(r => '<tr>' + r.map((c, idx) => {
    const cls = aligns[idx] ? ` class="${aligns[idx]}"` : '';
    return `<td${cls}>${gInline(c.trim())}</td>`;
  }).join('') + '</tr>').join('');
  const regionLabel = `${label || 'Tabulka'} #${++_gTblSeq}`;
  return `<div class="table-wrap" tabindex="0" role="region" aria-label="${esc(regionLabel)}"><table class="g-table"><thead><tr>${head}</tr></thead>${body ? `<tbody>${body}</tbody>` : ''}</table></div>`;
}

function gMistakeItem(raw) {
  const txt = String(raw || '').trim();
  const checkPos = txt.indexOf('✅');
  if (!txt.includes('❌') && checkPos === -1) return `<li>${gInline(txt)}</li>`;
  const before = (checkPos !== -1 ? txt.slice(0, checkPos) : txt).replace(/^❌\s*/, '').trim();
  const after = checkPos !== -1 ? txt.slice(checkPos + 1).trim() : '';
  const qm = before.match(/^(„[^“]+“)\s*(.+)$/);
  const claim = qm ? qm[1] : before;
  const why = qm ? qm[2] : '';
  return `<li class="mistake-item">${claim ? `<div class="m-row m-wrong">${ICO_X}<span class="m-claim">${gInline(claim)}</span></div>` : ''}${why ? `<div class="m-why">${gInline(why)}</div>` : ''}${after ? `<div class="m-row m-right">${ICO_CHECK}<span>${gInline(after)}</span></div>` : ''}</li>`;
}

function gSourceFooter(rawLines) {
  if (!rawLines.length) return '';
  const items = rawLines.map(rawLine => {
    const s = rawLine.trim();
    return (/^\*[^*\n].*\*$/.test(s) ? s.slice(1, -1) : s).trim();
  });
  const combinedPlain = items.join(' ').replace(/\*\*/g, '');
  const hasClaude = /Doplněno z Claude/i.test(combinedPlain);
  if (items.length === 1 && combinedPlain.length <= 85 && !combinedPlain.includes(';') && !hasClaude) {
    return `<p class="src-inline">${gInline(items[0])}</p>`;
  }
  const firstPlain = items[0].replace(/\*\*/g, '');
  const shortMatch = firstPlain.match(/^([^;(]+)/);
  let shortLabel = (shortMatch ? shortMatch[1] : firstPlain).trim()
    .replace(/\s*\*\*Doplněno z Claude\*\*/gi, '')
    .replace(/\s*Doplněno z Claude/gi, '')
    .replace(/[.:,\s]+$/, '');
  if (!shortLabel || shortLabel.toLowerCase() === 'zdroj:') shortLabel = 'Zdroj: přednáška';
  if (shortLabel.length > 56) shortLabel = shortLabel.slice(0, 54).trim() + '…';
  return `<details class="entry-src"><summary>${ICO_CHEV}<span>${esc(shortLabel)}</span>${hasClaude ? '<span class="src-badge">doplněno AI</span>' : ''}</summary><div class="src-full">${items.map(it => `<p>${gInline(it)}</p>`).join('')}</div></details>`;
}

// Formátuje heslo v teorii: callouty (> [!warning]), tabulky, číslované/odrážkové seznamy, časté omyly, příklady a zdroje.
function gBody(body, termLabel) {
  const out = [];
  const srcLines = [];
  const L = String(body ?? '').split('\n');
  for (let i = 0; i < L.length; i++) {
    const l = L[i];
    if (/^>/.test(l)) {
      const qLines = [];
      for (; i < L.length && /^>/.test(L[i]); i++) qLines.push(L[i].replace(/^>\s?/, ''));
      i--;
      let title = '';
      if (qLines.length && /^\[![a-z]+\]/i.test(qLines[0])) {
        const tm = qLines[0].match(/^\[![a-z]+\]\s*(.*)$/i);
        title = tm && tm[1] ? tm[1].trim() : 'Poznámka';
        qLines.shift();
      }
      out.push(`<aside class="callout">${title ? `<div class="callout-head">${ICO_WARN}<span>${esc(title)}</span></div>` : ''}${gBody(qLines.join('\n'), termLabel)}</aside>`);
    } else if (/^\|/.test(l)) {
      const tLines = [];
      for (; i < L.length && /^\|/.test(L[i]); i++) tLines.push(L[i]);
      i--;
      out.push(gTable(tLines, termLabel ? `Tabulka: ${termLabel}` : 'Tabulka'));
    } else if (/^\*Časté omyly:\*\s*$/i.test(l.trim()) && i + 1 < L.length && /^- /.test(L[i + 1])) {
      const items = [];
      i++;
      for (; i < L.length && /^- /.test(L[i]); i++) items.push(L[i].slice(2));
      i--;
      out.push(`<div class="mistakes"><div class="mistakes-head">Časté omyly</div><ul class="mistake-list">${items.map(gMistakeItem).join('')}</ul></div>`);
    } else if (/^- /.test(l)) {
      const items = [];
      for (; i < L.length && /^- /.test(L[i]); i++) items.push(L[i].slice(2));
      i--;
      const isMistake = items.some(x => x.includes('❌') && x.includes('✅'));
      out.push(isMistake
        ? `<ul class="mistake-list">${items.map(gMistakeItem).join('')}</ul>`
        : `<ul class="g-ul">${items.map(x => `<li>${gInline(x)}</li>`).join('')}</ul>`);
    } else if (/^\d+\.\s+/.test(l)) {
      const items = [];
      for (; i < L.length && /^\d+\.\s+/.test(L[i]); i++) items.push(L[i].replace(/^\d+\.\s+/, ''));
      i--;
      out.push(`<ol class="g-ol">${items.map(x => `<li>${gInline(x)}</li>`).join('')}</ol>`);
    } else if (/^\*Zdroj\s*:/i.test(l.trim())) {
      srcLines.push(l);
    } else if (l.trim()) {
      const exMatch = l.match(/^\*(Příklad[^*:]*|Příklady[^*:]*|Další příklad[^*:]*|Dveře[^*:]*):\*\s*(.+)$/);
      const noteMatch = l.match(/^\*(Pozor[^*:]*):\*\s*(.+)$/);
      if (exMatch) out.push(`<p class="block-ex"><span class="b-tag">${gInline(exMatch[1])}:</span>${gInline(exMatch[2])}</p>`);
      else if (noteMatch) out.push(`<p class="block-note"><span class="b-tag">${gInline(noteMatch[1])}:</span>${gInline(noteMatch[2])}</p>`);
      else out.push(`<p>${gInline(l)}</p>`);
    }
  }
  return (out.length ? `<div class="entry-body">${out.join('')}</div>` : '') + gSourceFooter(srcLines);
}

function parseLectureMeta(label) {
  const m = String(label || '').match(/^(\d+)\.\s*přednáška\s*\(([^)]+)\):\s*(.+)$/);
  if (!m) return { key: String(label || ''), num: '', date: '', heading: String(label || ''), topic: '' };
  return {
    key: `${m[1]}|${m[2].trim()}`,
    num: m[1],
    date: m[2].trim(),
    heading: `${m[1]}. přednáška · ${m[2].trim()}`,
    topic: m[3].trim()
  };
}

function mergeGroupsByDate(groups) {
  const map = new Map();
  const order = [];
  for (const g of groups || []) {
    const meta = parseLectureMeta(g && g.label);
    let bucket = map.get(meta.key);
    if (!bucket) {
      bucket = {
        key: meta.key,
        num: meta.num,
        date: meta.date,
        heading: meta.heading,
        topics: meta.topic ? [meta.topic] : [],
        entries: []
      };
      map.set(meta.key, bucket);
      order.push(bucket);
    } else if (meta.topic && !bucket.topics.includes(meta.topic)) {
      bucket.topics.push(meta.topic);
    }
    const seen = new Set(bucket.entries.map(e => e && e.term));
    for (const e of (g && g.entries) || []) {
      if (e && !seen.has(e.term)) {
        bucket.entries.push(e);
        seen.add(e.term);
      }
    }
  }
  return order.map(b => ({
    key: b.key,
    num: b.num,
    date: b.date,
    heading: b.heading,
    topicsText: b.topics.join(' · '),
    label: b.topics.length ? `${b.heading}: ${b.topics.join(' · ')}` : b.heading,
    entries: b.entries
  }));
}

(async () => {
  const THEME_ORDER = ['catppuccin', 'dark', 'amoled', 'light'];
  const THEME_NAMES = { catppuccin: 'Mocha', dark: 'Dark', amoled: 'AMOLED', light: 'Světlý', auto: 'Auto' };
  const themeBtn = document.getElementById('themeBtn');
  const applyTheme = t => {
    const mode = THEME_NAMES[t] ? t : 'catppuccin';
    if (mode === 'catppuccin') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', mode);
    if (themeBtn) themeBtn.textContent = 'Motiv: ' + THEME_NAMES[mode];
    try { localStorage.setItem('tzi_theme', mode); } catch (_) {}
  };
  let initTheme = 'catppuccin';
  try {
    const saved = localStorage.getItem('tzi_theme');
    if (THEME_NAMES[saved]) initTheme = saved;
  } catch (_) {}
  applyTheme(initTheme);
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') || 'catppuccin';
      const idx = THEME_ORDER.indexOf(cur);
      const next = THEME_ORDER[(idx + 1) % THEME_ORDER.length];
      applyTheme(next);
    });
  }

  const outEl = document.getElementById('out');
  const subEl = document.getElementById('sub');
  const countMeta = document.getElementById('countMeta');
  const lecSelect = document.getElementById('lecSelect');
  const tocAside = document.getElementById('tocAside');
  const tocLabel = document.getElementById('tocLabel');
  const tocNav = document.getElementById('tocNav');
  const qInput = document.getElementById('q');
  const qClear = document.getElementById('qClear');
  const resetFilterBtn = document.getElementById('resetFilterBtn');
  const emptyResetBtn = document.getElementById('emptyResetBtn');
  const emptySearch = document.getElementById('emptySearch');
  const emptyMsg = document.getElementById('emptyMsg');
  const toTopBtn = document.getElementById('toTop');

  const menuBtn = document.getElementById('menuBtn');
  const drawer = document.getElementById('overviewDrawer');
  const drawerSheet = document.getElementById('drawerSheet');
  const drawerClose = document.getElementById('drawerClose');
  const ovStats = document.getElementById('ovStats');
  const ovLectures = document.getElementById('ovLectures');
  const drawerSrcToggle = document.getElementById('drawerSrcToggle');

  const tocTermHtml = t => esc(t)
    .replace(/\^\(([^)]+)\)/g, '<sup>$1</sup>')
    .replace(/\^([A-Za-z0-9]+)/g, '<sup>$1</sup>')
    .replace(/_\(([^)]+)\)/g, '<sub>$1</sub>')
    .replace(/_([A-Za-z0-9]+)/g, '<sub>$1</sub>');

  const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const bodyWithoutSources = b => String(b || '').split('\n').filter(l => !/^\*Zdroj\s*:/i.test(l.trim())).join('\n');

  let state = {
    source: '_all',
    activeDateKey: '',
    rawTitle: '',
    allMerged: [],
    groups: [],
    entryIndex: [],
    groupEls: [],
    tocEls: [],
    showSources: false
  };

  function openDrawer() {
    if (!drawer || drawer.open) return;
    drawer.showModal();
    if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
  }
  function closeDrawer() {
    if (drawer && drawer.open) drawer.close();
  }
  if (menuBtn) menuBtn.addEventListener('click', openDrawer);
  if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
  if (drawer) {
    drawer.addEventListener('click', e => {
      if (drawerSheet && !drawerSheet.contains(e.target)) closeDrawer();
    });
    drawer.addEventListener('cancel', () => {
      if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    });
    drawer.addEventListener('close', () => {
      if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    });
  }

  if (drawerSrcToggle) {
    drawerSrcToggle.addEventListener('click', () => {
      state.showSources = !state.showSources;
      outEl.classList.toggle('show-sources', state.showSources);
      drawerSrcToggle.setAttribute('aria-pressed', state.showSources ? 'true' : 'false');
      drawerSrcToggle.textContent = state.showSources ? 'Skrýt zdroje u pojmů' : 'Zobrazit zdroje u pojmů';
    });
  }

  const showEmpty = msg => {
    outEl.textContent = '';
    const p = document.createElement('p');
    p.className = 'empty';
    p.textContent = msg;
    outEl.appendChild(p);
    if (tocAside) tocAside.hidden = true;
    if (emptySearch) emptySearch.hidden = true;
  };

  function updateOverview() {
    const overviewGroups = state.allMerged.length ? state.allMerged : state.groups;
    const totalEntries = overviewGroups.reduce((sum, g) => sum + g.entries.length, 0);
    const totalTables = overviewGroups.reduce((s, g) => s + g.entries.reduce((a, e) => a + (String(e.body || '').match(/^[>\s]*\|[\s|:-]+\|\s*$/gm) || []).length, 0), 0);
    const totalMistakes = overviewGroups.reduce((s, g) => s + g.entries.reduce((a, e) => a + (String(e.body || '').match(/^- ❌/gm) || []).length, 0), 0);
    if (ovStats) {
      ovStats.innerHTML =
        `<div class="ov-stat"><span class="ov-stat-val">${overviewGroups.length}</span><span class="ov-stat-lbl">Přednášek</span></div>` +
        `<div class="ov-stat"><span class="ov-stat-val">${totalEntries}</span><span class="ov-stat-lbl">Pojmů</span></div>` +
        `<div class="ov-stat"><span class="ov-stat-val">${totalTables}/${totalMistakes}</span><span class="ov-stat-lbl">Tabulek/Omylů</span></div>`;
    }
    if (ovLectures) {
      const isAll = state.source === '_all' && !state.activeDateKey;
      const items = [
        `<button type="button" class="ov-lec-btn${isAll ? ' active' : ''}" data-pick="_all">` +
          `<span class="ov-lec-title">Všechny přednášky podle data</span><span class="ov-lec-cnt">${totalEntries}</span></button>`
      ];
      for (const g of overviewGroups) {
        const active = (state.source === '_all' && state.activeDateKey === g.key) || (state.groups.length === 1 && state.groups[0].key === g.key && !isAll);
        items.push(
          `<button type="button" class="ov-lec-btn${active ? ' active' : ''}" data-pick="${esc('date:' + g.key)}">` +
            `<span class="ov-lec-title">${esc(g.heading)}</span>` +
            `<span class="ov-lec-cnt">${g.entries.length}</span>` +
            (g.topicsText ? `<span class="ov-lec-topics">${esc(g.topicsText)}</span>` : '') +
          `</button>`
        );
      }
      ovLectures.innerHTML = items.join('');
    }
  }

  function applyFilter() {
    const raw = (qInput && qInput.value || '').trim();
    const q = norm(raw);
    if (qClear) qClear.hidden = !raw;
    if (resetFilterBtn) resetFilterBtn.hidden = !raw;

    let visibleTotal = 0;
    const total = state.entryIndex.length;
    const grpVisible = new Array(state.groupEls.length).fill(0);

    for (const item of state.entryIndex) {
      const show = !q || item.searchText.includes(q);
      item.el.hidden = !show;
      if (show) {
        visibleTotal++;
        grpVisible[item.grpIdx]++;
      }
      if (item.tocEl) item.tocEl.hidden = !show;
    }

    state.groupEls.forEach((gEl, gi) => {
      const cnt = grpVisible[gi];
      gEl.hidden = cnt === 0;
      const cSpan = gEl.querySelector('.grp-count');
      const fullCnt = (state.groups[gi] && state.groups[gi].entries.length) || 0;
      if (cSpan) cSpan.textContent = q ? `${cnt} / ${fullCnt}` : `${fullCnt} pojmů`;
      if (state.groups.length > 1 && state.tocEls[gi]) {
        state.tocEls[gi].hidden = cnt === 0;
        const tCnt = state.tocEls[gi].querySelector('.toc-cnt');
        if (tCnt) tCnt.textContent = q ? `${cnt}/${fullCnt}` : String(fullCnt);
      }
    });

    if (emptySearch) {
      emptySearch.hidden = visibleTotal > 0 || total === 0;
      if (emptyMsg && raw) emptyMsg.textContent = `Dotazu „${raw}“ neodpovídá žádný pojem.`;
    }
    if (subEl) {
      if (q) subEl.textContent = `Nalezeno ${visibleTotal} z ${total} pojmů`;
      else if (state.groups.length > 1) subEl.textContent = `${state.groups.length} přednášek seřazených podle data`;
      else subEl.textContent = state.groups[0] ? `${state.groups[0].entries.length} pojmů v přednášce` : state.rawTitle;
    }
    if (countMeta) {
      countMeta.textContent = q ? `${visibleTotal}/${total}` : `${total} pojmů`;
    }
  }

  function renderGroups(groups, title) {
    state.groups = groups;
    document.title = `Teorie: ${title} · TZI Trenér`;

    if (!groups.length) {
      if (subEl) subEl.textContent = title;
      if (countMeta) countMeta.textContent = '0 pojmů';
      showEmpty('K téhle přednášce zatím není v teorii žádný obsah.');
      updateOverview();
      return;
    }

    const multi = groups.length > 1;
    outEl.innerHTML = groups.map((g, gi) => {
      const entries = g.entries || [];
      const cards = entries.map((e, ei) => `<article class="entry" id="e-${gi}-${ei}"><h3>${gInline(e && e.term)}</h3>${gBody(e && e.body, e && e.term)}</article>`).join('');
      return `<section class="lec-group" id="grp-${gi}" aria-labelledby="gh-${gi}">` +
        `<div class="grp-head"><h2 id="gh-${gi}">${esc(g.heading)}</h2><span class="grp-count">${entries.length} pojmů</span>` +
        (g.topicsText ? `<div class="grp-topics">${esc(g.topicsText)}</div>` : '') +
        `</div><div class="entries-list">${cards}</div></section>`;
    }).join('');

    state.groupEls = [...outEl.querySelectorAll('.lec-group')];
    state.entryIndex = [];
    state.tocEls = [];

    if (tocNav && tocAside) {
      tocAside.hidden = false;
      if (multi) {
        if (tocLabel) tocLabel.textContent = 'Přednášky';
        tocNav.innerHTML = groups.map((g, gi) =>
          `<a class="toc-link${gi === 0 ? ' active' : ''}" href="#grp-${gi}" title="${esc(g.label)}">` +
            `<span>${esc(g.heading)}</span><span class="toc-cnt">${g.entries.length}</span>` +
            (g.topicsText ? `<span class="toc-sub">${esc(g.topicsText)}</span>` : '') +
          `</a>`
        ).join('');
        state.tocEls = [...tocNav.querySelectorAll('.toc-link')];
      } else {
        if (tocLabel) tocLabel.textContent = 'Pojmy v přednášce';
        const entries = groups[0].entries || [];
        tocNav.innerHTML = entries.map((e, ei) =>
          `<a class="toc-link${ei === 0 ? ' active' : ''}" href="#e-0-${ei}"><span>${tocTermHtml(e.term)}</span></a>`
        ).join('');
      }
    }

    let flatIdx = 0;
    const entryTocLinks = !multi && tocNav ? [...tocNav.querySelectorAll('.toc-link')] : [];
    groups.forEach((g, gi) => {
      const els = state.groupEls[gi] ? [...state.groupEls[gi].querySelectorAll('.entry')] : [];
      (g.entries || []).forEach((e, ei) => {
        const el = els[ei];
        if (!el) return;
        const tocEl = !multi ? entryTocLinks[flatIdx++] : null;
        state.entryIndex.push({
          el,
          grpIdx: gi,
          tocEl,
          searchText: norm(`${g.label || ''} ${e.term || ''} ${bodyWithoutSources(e.body)}`)
        });
      });
    });

    updateOverview();
    applyFilter();
  }

  function populateLectureSelect() {
    if (!lecSelect) return;
    const list = state.allMerged;
    if (!list.length) return;
    const total = list.reduce((s, g) => s + g.entries.length, 0);
    const opts = [`<option value="_all">Všechny přednášky (${total})</option>`];
    for (const g of list) {
      opts.push(`<option value="${esc('date:' + g.key)}">${esc(g.heading)}</option>`);
    }
    lecSelect.innerHTML = opts.join('');
    if (state.source === '_all' && state.activeDateKey) lecSelect.value = 'date:' + state.activeDateKey;
    else if (state.source === '_all') lecSelect.value = '_all';
    else if (state.groups.length === 1 && list.some(x => x.key === state.groups[0].key)) {
      lecSelect.value = 'date:' + state.groups[0].key;
    }
  }

  async function fetchGlosar(src) {
    const r = await fetch('/api/teorie?source=' + encodeURIComponent(src), { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    if (!d || typeof d.title !== 'string' || !Array.isArray(d.groups)) throw new Error('invalid');
    return d;
  }

  async function selectView(pickVal, updateUrl = true) {
    const isDatePick = String(pickVal || '').startsWith('date:');
    const targetSrc = (isDatePick || pickVal === '_all') ? '_all' : pickVal;
    const safeSrc = /^[A-Za-z0-9_-]{1,64}$/.test(targetSrc) ? targetSrc : '_all';
    state.source = safeSrc;
    state.activeDateKey = isDatePick ? pickVal.slice(5) : '';

    if (updateUrl) {
      const u = new URL(location.href);
      u.searchParams.set('source', safeSrc);
      if (state.activeDateKey) u.searchParams.set('den', state.activeDateKey);
      else u.searchParams.delete('den');
      history.replaceState(null, '', u.pathname + u.search);
    }

    if (safeSrc === '_all' && state.allMerged.length) {
      const subset = state.activeDateKey ? state.allMerged.filter(g => g.key === state.activeDateKey) : state.allMerged;
      const viewTitle = state.activeDateKey && subset[0] ? subset[0].heading : state.rawTitle || 'Všechny přednášky podle data';
      populateLectureSelect();
      renderGroups(subset, viewTitle);
      return;
    }

    try {
      const d = await fetchGlosar(safeSrc);
      state.rawTitle = d.title;
      const merged = mergeGroupsByDate(d.groups);
      if (safeSrc === '_all') state.allMerged = merged;
      const subset = state.activeDateKey ? merged.filter(g => g.key === state.activeDateKey) : merged;
      const viewTitle = state.activeDateKey && subset[0] ? subset[0].heading : d.title;
      populateLectureSelect();
      renderGroups(subset, viewTitle);
    } catch (_) {
      showEmpty('Teorii se nepodařilo načíst.');
    }
  }

  if (qInput) {
    qInput.addEventListener('input', applyFilter);
    qInput.addEventListener('keydown', e => {
      if (e.key === 'Escape' && qInput.value) {
        qInput.value = '';
        applyFilter();
      }
    });
  }
  const clearSearch = () => {
    if (!qInput) return;
    qInput.value = '';
    applyFilter();
    qInput.focus();
  };
  if (qClear) qClear.addEventListener('click', clearSearch);
  if (resetFilterBtn) resetFilterBtn.addEventListener('click', clearSearch);
  if (emptyResetBtn) emptyResetBtn.addEventListener('click', clearSearch);

  document.addEventListener('keydown', e => {
    if (e.key === '/' && qInput && document.activeElement !== qInput && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      qInput.focus();
      qInput.select();
    }
  });

  if (tocNav) {
    tocNav.addEventListener('click', e => {
      const link = e.target.closest('.toc-link');
      if (!link) return;
      tocNav.querySelectorAll('.toc-link.active').forEach(a => a.classList.remove('active'));
      link.classList.add('active');
    });
  }

  if (ovLectures) {
    ovLectures.addEventListener('click', async e => {
      const btn = e.target.closest('.ov-lec-btn');
      if (!btn) return;
      const pick = btn.dataset.pick || '_all';
      closeDrawer();
      await selectView(pick, true);
      window.scrollTo({ top: 0 });
    });
  }

  if (toTopBtn) {
    window.addEventListener('scroll', () => {
      toTopBtn.hidden = window.scrollY < 420;
    }, { passive: true });
    toTopBtn.addEventListener('click', () => window.scrollTo({ top: 0 }));
  }

  if (lecSelect) {
    lecSelect.addEventListener('change', () => {
      selectView(lecSelect.value || '_all', true);
    });
  }

  const sp = new URLSearchParams(location.search);
  const rawSource = sp.get('source') || '_all';
  const initSource = /^[A-Za-z0-9_-]{1,64}$/.test(rawSource) ? rawSource : '_all';
  const initDen = sp.get('den') || '';

  // Přednačíst _all pro kompletní přehled podle data i při otevření konkrétní banky z kvízu
  if (initSource !== '_all') {
    fetchGlosar('_all').then(allD => {
      state.allMerged = mergeGroupsByDate(allD.groups);
      if (!state.rawTitle) state.rawTitle = allD.title;
      populateLectureSelect();
      updateOverview();
    }).catch(() => {});
  }

  await selectView(initDen ? 'date:' + initDen : initSource, false);
})();
