// Sdílené vyhledávání pro glosar.html a vypisky.html. Jako Ctrl+F: obsah zůstane vidět, shody se zvýrazní (bez ohledu na velikost písmen a diakritiku),
// čítač „3 / 17“, Enter = další, Shift+Enter = předchozí, Esc smaže. Prochází jen textové uzly, takže zlomky a indexy zůstanou celé.
function initSearch(unitSel, noun) {
  const q = document.getElementById('q'), cnt = document.getElementById('cnt'), out = document.getElementById('out');
  const prevB = document.getElementById('sprev'), nextB = document.getElementById('snext');
  const total = out.querySelectorAll(unitSel).length;
  const fold1 = c => c.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const fold = t => [...t].map(fold1).join('');
  let marks = [], cur = -1;
  const idle = () => { cnt.textContent = total && noun ? total + noun : ''; prevB.disabled = nextB.disabled = true; };
  function clear() {
    out.querySelectorAll('mark.hit').forEach(m => { const p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize(); });
    marks = []; cur = -1;
  }
  function go(i, scroll) {
    if (!marks.length) return;
    if (cur >= 0) marks[cur].classList.remove('cur');
    cur = (i + marks.length) % marks.length;
    marks[cur].classList.add('cur');
    cnt.textContent = (cur + 1) + ' / ' + marks.length;
    for (let d = marks[cur].closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true; // nález ve sbaleném callout
    if (scroll) marks[cur].scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }
  function run() {
    clear();
    const w = fold(q.value.trim());
    if (!w) { idle(); return; }
    const walker = document.createTreeWalker(out, NodeFilter.SHOW_TEXT), nodes = [];
    for (let n; (n = walker.nextNode());) if (!n.parentElement.closest('svg')) nodes.push(n); // <mark> v SVG by text schovalo
    for (const node of nodes) {
      const chars = [...node.data], f = chars.map(fold1); // 1 znak původního textu = 1 položka (diakritika se skládá po znacích)
      const flat = f.join(''), map = []; // map: pozice ve složeném textu -> index znaku původního textu
      f.forEach((x, i) => { for (let k = 0; k < x.length; k++) map.push(i); });
      const hits = [];
      for (let i = flat.indexOf(w); i >= 0; i = flat.indexOf(w, i + w.length)) hits.push([map[i], map[i + w.length - 1] + 1]);
      for (let h = hits.length - 1; h >= 0; h--) { // odzadu, aby se neposouvaly pozice
        const [a, b] = hits[h], off = a => chars.slice(0, a).join('').length;
        node.splitText(off(b)); const mid = node.splitText(off(a));
        const m = document.createElement('mark'); m.className = 'hit';
        mid.parentNode.replaceChild(m, mid); m.appendChild(mid);
        marks.unshift(m);
      }
    }
    // pořadí v dokumentu: zpracování uzlů je popořadě, uvnitř uzlu zpětně, proto seřadit
    marks.sort((x, y) => (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
    prevB.disabled = nextB.disabled = !marks.length;
    if (marks.length) go(0, true); else cnt.textContent = 'Nic nenalezeno. Zkus kratší výraz.';
  }
  q.addEventListener('input', run);
  q.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); go(cur + (e.shiftKey ? -1 : 1), true); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); go(cur + 1, true); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); go(cur - 1, true); }
    else if (e.key === 'Escape') { q.value = ''; run(); }
  });
  nextB.addEventListener('click', () => go(cur + 1, true));
  prevB.addEventListener('click', () => go(cur - 1, true));
  document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') { e.preventDefault(); q.focus(); q.select(); } });
  idle();
}
