#!/usr/bin/env python3
"""TZI Trenér: opakování 1. přednášky (číselné soustavy).

Spuštění:  python3 tzi_trener.py          # spustí aplikaci v prohlížeči (http://127.0.0.1:8000)
           python3 tzi_trener.py --cli    # terminálová verze
Bez závislostí (jen standardní knihovna). Celé webové rozhraní je vložené v tomto souboru (HTML níže).
Postup kartiček v terminálové verzi se ukládá do ~/.tzi_trener.json.
"""
import http.server
import json
import random
import sys
import threading
import webbrowser
from pathlib import Path

HTML = r"""<title>TZI Trenér</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
/* Layout: one narrow column, tab bar on top, one task card at a time; numbers in mono like a terminal printout */
:root{
  --bg:#f3f5f8; --surface:#ffffff; --fg:#14202e; --muted:#5b6878; --line:#d5dbe4;
  --accent:#1457c4; --accent-fg:#ffffff; --good:#17794a; --good-bg:#e3f4ea; --bad:#b3261e; --bad-bg:#fbe7e5;
  --display:'Bricolage Grotesque',system-ui,sans-serif; --body:'IBM Plex Sans',system-ui,sans-serif; --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0f161f; --surface:#18222e; --fg:#e6ecf3; --muted:#93a1b3; --line:#2b3948;
  --accent:#6aa3ff; --accent-fg:#0b1624; --good:#5ed39a; --good-bg:#12301f; --bad:#ff8f86; --bad-bg:#3a1916; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f161f; --surface:#18222e; --fg:#e6ecf3; --muted:#93a1b3; --line:#2b3948;
  --accent:#6aa3ff; --accent-fg:#0b1624; --good:#5ed39a; --good-bg:#12301f; --bad:#ff8f86; --bad-bg:#3a1916; color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.5;padding-inline:16px;padding-block:20px 48px}
main{max-width:640px;margin-inline:auto;display:flex;flex-direction:column;gap:16px}
h1{font-family:var(--display);font-size:1.7rem;line-height:1.1;margin:0;text-wrap:balance}
.sub{color:var(--muted);margin:4px 0 0;font-size:.9rem}
nav{display:flex;gap:6px;border-bottom:1px solid var(--line)}
nav button{flex:1;background:none;border:0;border-bottom:3px solid transparent;color:var(--muted);font:500 .95rem var(--body);padding:10px 4px;cursor:pointer}
nav button[aria-selected="true"]{color:var(--fg);border-bottom-color:var(--accent)}
button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px;display:flex;flex-direction:column;gap:14px;min-width:0}
.meta{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:.85rem;font-family:var(--mono)}
.q{font-family:var(--display);font-size:1.3rem;line-height:1.25;margin:0;text-wrap:balance}
.task{font-family:var(--mono);font-size:1.5rem;margin:0;overflow-wrap:anywhere}
.ans{border-top:1px dashed var(--line);padding-top:12px;min-width:0;overflow-wrap:anywhere}
.ans p{margin:0 0 8px}
.row{display:flex;gap:8px;flex-wrap:wrap}
.btn{font:500 1rem var(--body);padding:11px 16px;border-radius:8px;border:1px solid var(--line);background:var(--surface);color:var(--fg);cursor:pointer;flex:1;min-width:120px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-fg)}
.btn.good{background:var(--good-bg);border-color:var(--good);color:var(--good)}
.btn.bad{background:var(--bad-bg);border-color:var(--bad);color:var(--bad)}
input[type=text],select{font:400 1.2rem var(--mono);padding:10px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);width:100%;min-width:0}
select{font:400 .95rem var(--body);width:auto;flex:1}
.fb{padding:10px 12px;border-radius:8px;font-weight:500}
.fb.ok{background:var(--good-bg);color:var(--good)} .fb.no{background:var(--bad-bg);color:var(--bad)}
.steps{font-family:var(--mono);font-size:.9rem;overflow-x:auto}
.steps table{border-collapse:collapse} .steps td,.steps th{border:1px solid var(--line);padding:3px 10px;text-align:right}
.steps p{margin:6px 0}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.link{background:none;border:0;color:var(--muted);font:.85rem var(--body);text-decoration:underline;cursor:pointer;padding:4px;align-self:flex-start}
@media (prefers-reduced-motion:no-preference){.bar i{transition:width .25s}}
</style>

<main>
  <header>
    <h1>TZI Trenér</h1>
    <p class="sub">KI/TIN, 1. přednáška: číselné soustavy. Kartičky na teorii a generované příklady na papír.</p>
  </header>
  <nav role="tablist" aria-label="Režim">
    <button role="tab" id="t-cards" aria-selected="true">Teorie</button>
    <button role="tab" id="t-conv" aria-selected="false">Převody</button>
    <button role="tab" id="t-arit" aria-selected="false">Aritmetika</button>
  </nav>
  <section id="view"></section>
</main>

<script>
const D="0123456789ABCDEF";
const sub=(s,z)=>`(${s})<sub>${z}</sub>`;
const rnd=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
const pick=a=>a[rnd(0,a.length-1)];
const toS=(n,z)=>n.toString(z).toUpperCase();
const clean=s=>s.toUpperCase().replace(/[\s_]/g,'').replace(/^0+(?=.)/,'');
let store={};try{store=JSON.parse(localStorage.getItem('tzi')||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem('tzi',JSON.stringify(store))}catch(e){}};

/* ---------- Teorie ---------- */
const CARDS=[
["Co je číselná soustava? Jak se dělí?","Způsob reprezentace čísel. Čísla se tvoří z uspořádaných souborů znaků = <b>číslic</b>. Dělí se na <b>poziční</b> a <b>nepoziční</b>."],
["Čím se liší poziční a nepoziční soustava? Příklady?","Poziční má <b>základ Z &gt; 1</b> a hodnota číslice závisí na pozici (dvojková, osmičková, desítková, šestnáctková). Nepoziční základ nemá, příklad: <b>římská</b> soustava (I, II, III, IV, V, VI…)."],
["Co udává základ soustavy?","<b>Max. počet číslic</b>, které jsou v soustavě k dispozici. Soustava o základu Z má číslice 0 až Z−1. V osmičkové neexistují 8 a 9, po 7 následuje 10."],
["Napiš obecný zápis čísla v poziční soustavě o základu Z.","<p>a = a<sub>n</sub>·Z<sup>n</sup> + a<sub>n−1</sub>·Z<sup>n−1</sup> + … + a<sub>1</sub>·Z<sup>1</sup> + a<sub>0</sub>·Z<sup>0</sup></p><p>Nejvyšší mocnina = <b>počet číslic − 1</b>.</p>"],
["Rozepiš (251)<sub>10</sub> a (101)<sub>2</sub> podle obecného zápisu.","<p>(251)<sub>10</sub> = 2·10² + 5·10¹ + 1·10⁰ = 200 + 50 + 1 = 251</p><p>(101)<sub>2</sub> = 1·2² + 0·2¹ + 1·2⁰ = 4 + 0 + 1 = 5</p>"],
["Jak se zapisují číslice 10 až 15 v šestnáctkové soustavě?","A=10, B=11, C=12, D=13, E=14, F=15."],
["Proč jde převod 2 ↔ 16 po čtveřicích bitů a 2 ↔ 8 po trojicích?","16 = 2⁴ a 8 = 2³. Jedna hex číslice nese přesně <b>4 bity</b>, jedna osmičková <b>3 bity</b>. Např. (1010 1111)<sub>2</sub> = (AF)<sub>16</sub>. Skupiny se dělí <b>zprava</b>."],
["Postup převodu 10 → Z a Z → 10?","<p><b>10 → Z:</b> dělím základem Z, zapisuji zbytky, dokud podíl není 0; zbytky čtu <b>zdola nahoru</b>.</p><p><b>Z → 10:</b> rozvoj podle obecného zápisu (číslice · Z<sup>pozice</sup>, sečíst).</p>"],
["Jak se převádí 8 ↔ 16?","Oklikou přes dvojkovou: osmičkové číslice na trojice bitů, pak bity po čtveřicích zprava (a naopak)."],
["Pravidla sčítání ve dvojkové soustavě?","0+0=0, 0+1=1, 1+0=1, <b>1+1 = (10)<sub>2</sub></b> → zapíšu 0, přenos 1 do vyššího řádu. 1+1+1 = (11)<sub>2</sub> → zapíšu 1, přenos 1."],
["Jak se násobí a dělí ve dvojkové soustavě?","Násobení jako na papíře: pro každou 1 opíšu první číslo posunuté o řád doleva, pak sečtu. Dělení písemně jako v desítkové (odčítám dělitele nebo 0). Dělení nulou není definováno."],
["Co znamená N ⊂ Z ⊂ Q ⊂ R ⊂ C?","Každý obor je částí dalšího: přirozená (0, 1, 2…), celá, racionální (zlomky), reálná (i √2, π), komplexní (a + ib)."],
["Vysvětli značení n!, |x|, Σ, Π.","<p>n! = 1·2·3·…·n, 0! = 1 (5! = 120)</p><p>|x| absolutní hodnota: |−5| = 5</p><p>Σ součet a<sub>1</sub> + … + a<sub>n</sub>, Π součin a<sub>1</sub>·…·a<sub>n</sub></p>"],
["Čemu se rovná a⁰ a co je zvláštní případ?","a⁰ = 1. Zvláštní případ je 0⁰ (na přednášce naznačeno na tabuli, ověřit)."]
];
let deck=[],ci=0,shown=false;
function newDeck(onlyUnknown){
  const known=store.known||[];
  deck=CARDS.map((_,i)=>i).filter(i=>!onlyUnknown||!known.includes(i));
  for(let i=deck.length-1;i>0;i--){const j=rnd(0,i);[deck[i],deck[j]]=[deck[j],deck[i]]}
  ci=0;shown=false;
}
function viewCards(){
  const v=document.getElementById('view');
  const known=(store.known||[]).length;
  if(!deck.length||ci>=deck.length){
    v.innerHTML=`<div class="card"><p class="q">Balíček hotový</p><p>Umíš ${known} z ${CARDS.length} kartiček.</p>
    <div class="row"><button class="btn primary" id="again">${known<CARDS.length?'Projít ty, co neumím':'Znovu všechny'}</button><button class="btn" id="all">Všechny od začátku</button></div></div>`;
    document.getElementById('again').onclick=()=>{if(known>=CARDS.length)store.known=[];save();newDeck(true);viewCards()};
    document.getElementById('all').onclick=()=>{newDeck(false);viewCards()};
    return;
  }
  const idx=deck[ci],c=CARDS[idx];
  v.innerHTML=`<div class="card">
    <div class="meta"><span>Kartička ${ci+1} / ${deck.length}</span><span>umím: ${known}/${CARDS.length}</span></div>
    <div class="bar"><i style="width:${ci/deck.length*100}%"></i></div>
    <p class="q">${c[0]}</p>
    ${shown?`<div class="ans">${c[1].startsWith('<p>')?c[1]:'<p>'+c[1]+'</p>'}</div>
      <div class="row"><button class="btn bad" id="no">Neuměl jsem</button><button class="btn good" id="yes">Uměl jsem</button></div>`
      :`<button class="btn primary" id="show">Ukázat odpověď</button>`}
  </div>`;
  if(!shown){document.getElementById('show').onclick=()=>{shown=true;viewCards()};return}
  document.getElementById('yes').onclick=()=>{const k=new Set(store.known||[]);k.add(idx);store.known=[...k];save();ci++;shown=false;viewCards()};
  document.getElementById('no').onclick=()=>{store.known=(store.known||[]).filter(x=>x!==idx);save();deck.push(idx);ci++;shown=false;viewCards()};
}

/* ---------- Převody ---------- */
const MODES={
 all:"Všechny směry",d2z:"Z desítkové (2, 8, 16)",z2d:"Do desítkové",b2o:"2 → 8",o2b:"8 → 2",b2h:"2 → 16",h2b:"16 → 2",o2h:"8 → 16",h2o:"16 → 8"};
const SPEC={d2z:null,z2d:null,b2o:[2,8],o2b:[8,2],b2h:[2,16],h2b:[16,2],o2h:[8,16],h2o:[16,8]};
let cmode=localStorage.getItem&&'all',ctask=null,cdone=false,cstat={ok:0,all:0};
try{cmode=localStorage.getItem('tzi-mode')||'all'}catch(e){}
function groups(s,k){s=s.padStart(Math.ceil(s.length/k)*k,'0');return s.match(new RegExp('.{'+k+'}','g'))}
function steps(s,from,to){
  const n=parseInt(s,from);let h='';
  if(from===10){
    const rows=[];let m=n;while(m>0){rows.push([m,Math.floor(m/to),m%to]);m=Math.floor(m/to)}
    h+=`<table><tr><th>dělení</th><th>podíl</th><th>zbytek</th></tr>`+rows.map(r=>`<tr><td>${r[0]} : ${to}</td><td>${r[1]}</td><td>${r[2]}${r[2]>9?' = '+D[r[2]]:''}</td></tr>`).join('')+`</table><p>Zbytky zdola nahoru: <b>${toS(n,to)}</b></p>`;
  }else if(to===10){
    const L=s.length,t=[...s].map((c,i)=>`${D.indexOf(c)}·${from}^${L-1-i}`),v=[...s].map((c,i)=>D.indexOf(c)*from**(L-1-i));
    h+=`<p>${t.join(' + ')}</p><p>= ${v.join(' + ')} = <b>${n}</b></p>`;
  }else{
    const k=x=>x===2?1:x===8?3:4;
    if(from===2){const g=groups(s,k(to));h+=`<p>Zprava po ${k(to)} bitech: ${g.join(' | ')}</p><p>→ ${g.map(x=>D[parseInt(x,2)]).join(' ')} = <b>${toS(n,to)}</b></p>`}
    else if(to===2){const g=[...s].map(c=>parseInt(c,from).toString(2).padStart(k(from),'0'));h+=`<p>Každá číslice na ${k(from)} bity: ${g.join(' | ')}</p><p>= <b>${toS(n,2)}</b> (vedoucí nuly pryč)</p>`}
    else{const b=toS(n,2),g=groups(b,k(to));h+=`<p>Přes dvojkovou: ${s} = ${b}</p><p>Po ${k(to)} bitech zprava: ${g.join(' | ')} → <b>${toS(n,to)}</b></p>`}
  }
  const chk=to===10?'':`<p>Kontrola zpět do desítkové: ${parseInt(toS(n,to),to)}</p>`;
  return h+chk;
}
function newConv(){
  let m=cmode==='all'?pick(Object.keys(SPEC)):cmode,from,to,s;
  if(m==='d2z'){from=10;to=pick([2,2,8,16]);s=String(rnd(10,to===2?200:900))}
  else if(m==='z2d'){from=pick([2,8,16]);to=10;s=toS(rnd(10,from===2?200:900),from)}
  else{[from,to]=SPEC[m];s=toS(rnd(16,from===2?250:700),from)}
  ctask={s,from,to,ans:toS(parseInt(s,from),to)};cdone=false;
}
function viewConv(){
  const v=document.getElementById('view');if(!ctask)newConv();
  const t=ctask;
  v.innerHTML=`<div class="card">
    <div class="row"><select id="mode" aria-label="Směr převodu">${Object.entries(MODES).map(([k,l])=>`<option value="${k}"${k===cmode?' selected':''}>${l}</option>`).join('')}</select></div>
    <div class="meta"><span>správně ${cstat.ok} / ${cstat.all}</span><span>piš na papír, pak zadej výsledek</span></div>
    <p class="task">${sub(t.s,t.from)} → (?)<sub>${t.to}</sub></p>
    <input type="text" id="inp" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-label="Výsledek" placeholder="výsledek v soustavě ${t.to}" ${cdone?'disabled':''}>
    <div id="out"></div>
    <div class="row">${cdone?'<button class="btn primary" id="next">Další příklad</button>':'<button class="btn primary" id="chk">Zkontrolovat</button><button class="btn" id="giveup">Ukázat postup</button>'}</div>
  </div>`;
  document.getElementById('mode').onchange=e=>{cmode=e.target.value;try{localStorage.setItem('tzi-mode',cmode)}catch(_){}newConv();viewConv()};
  const inp=document.getElementById('inp');
  const finish=ok=>{cdone=true;cstat.all++;if(ok)cstat.ok++;
    viewConv();
    document.getElementById('out').innerHTML=`<div class="fb ${ok?'ok':'no'}">${ok?'Správně':'Správná odpověď: '+sub(t.ans,t.to)}</div><div class="ans steps">${steps(t.s,t.from,t.to)}</div>`;
    document.getElementById('inp').value=lastIn;document.getElementById('next').focus()};
  let lastIn='';
  if(cdone){return}
  const check=()=>{lastIn=inp.value;if(!inp.value.trim())return;finish(clean(inp.value)===t.ans)};
  document.getElementById('chk').onclick=check;
  inp.addEventListener('keydown',e=>{if(e.key==='Enter')check()});
  document.getElementById('giveup').onclick=()=>{lastIn=inp.value;finish(false)};
  inp.focus();
}

/* ---------- Aritmetika ---------- */
let atask=null,adone=false,astat={ok:0,all:0};
const B=n=>n.toString(2);
function newAr(){
  const op=pick(['+','+','−','×','÷']);let a,b;
  if(op==='+'){a=rnd(5,40);b=rnd(3,30)}
  else if(op==='−'){a=rnd(10,45);b=rnd(3,a-1)}
  else if(op==='×'){a=rnd(3,15);b=rnd(2,7)}
  else{b=rnd(2,7);const q=rnd(2,12);a=b*q}
  const r=op==='+'?a+b:op==='−'?a-b:op==='×'?a*b:a/b;
  atask={op,a,b,r};adone=false;
}
function arSteps(t){
  const {op,a,b,r}=t,A=B(a),Bb=B(b),R=B(r);
  let h=`<p>${a} ${op} ${b} = ${r} (v desítkové), tedy <b>${R}</b>.</p>`;
  if(op==='×'){
    const parts=[...Bb].reverse().map((c,i)=>c==='1'?A+'0'.repeat(i):null).filter(Boolean);
    h+=`<p>Dílčí součiny (posun o řád): ${parts.join(' + ')}</p>`;
  }
  if(op==='+'){h+=`<p>Sčítej zprava, 1+1 = 10 (zapiš 0, přenos 1).</p>`}
  if(op==='−'){h+=`<p>Kontrola sčítáním: ${R} + ${Bb} = ${A}</p>`}
  if(op==='÷'){h+=`<p>Kontrola násobením: ${R} · ${Bb} = ${A}</p>`}
  return h;
}
function viewAr(){
  const v=document.getElementById('view');if(!atask)newAr();
  const t=atask;
  v.innerHTML=`<div class="card">
    <div class="meta"><span>správně ${astat.ok} / ${astat.all}</span><span>výsledek zadej dvojkově</span></div>
    <p class="task">${sub(B(t.a),2)} ${t.op} ${sub(B(t.b),2)}</p>
    <input type="text" id="inp" inputmode="numeric" autocomplete="off" spellcheck="false" aria-label="Výsledek ve dvojkové soustavě" placeholder="výsledek ve dvojkové soustavě" ${adone?'disabled':''}>
    <div id="out"></div>
    <div class="row">${adone?'<button class="btn primary" id="next">Další příklad</button>':'<button class="btn primary" id="chk">Zkontrolovat</button><button class="btn" id="giveup">Ukázat postup</button>'}</div>
  </div>`;
  const inp=document.getElementById('inp');let lastIn='';
  const finish=ok=>{adone=true;astat.all++;if(ok)astat.ok++;viewAr();
    document.getElementById('out').innerHTML=`<div class="fb ${ok?'ok':'no'}">${ok?'Správně':'Správná odpověď: '+sub(B(t.r),2)}</div><div class="ans steps">${arSteps(t)}</div>`;
    document.getElementById('inp').value=lastIn;document.getElementById('next').focus()};
  if(adone){return}
  const check=()=>{lastIn=inp.value;if(!inp.value.trim())return;finish(clean(inp.value)===B(t.r))};
  document.getElementById('chk').onclick=check;
  inp.addEventListener('keydown',e=>{if(e.key==='Enter')check()});
  document.getElementById('giveup').onclick=()=>{lastIn=inp.value;finish(false)};
  inp.focus();
}

/* ---------- Tabs ---------- */
const tabs={ 't-cards':viewCards,'t-conv':viewConv,'t-arit':viewAr };
document.addEventListener('click',e=>{
  const id=e.target.id;
  if(e.target.closest('nav')&&tabs[id]){
    document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-selected',b.id===id));
    tabs[id]();
  }
  if(id==='next'){ if(document.getElementById('t-conv').getAttribute('aria-selected')==='true'){newConv();viewConv()}else{newAr();viewAr()} }
});
newDeck(true);if(!deck.length)newDeck(false);
viewCards();
</script>
"""

DIGITS = "0123456789ABCDEF"
SUBS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SAVE = Path.home() / ".tzi_trener.json"

CARDS = [
    ("Co je číselná soustava? Jak se dělí?",
     "Způsob reprezentace čísel. Čísla se tvoří z uspořádaných souborů znaků = číslic.\n"
     "Dělí se na poziční a nepoziční."),
    ("Čím se liší poziční a nepoziční soustava? Příklady?",
     "Poziční má základ Z > 1 a hodnota číslice závisí na pozici (dvojková, osmičková, desítková, šestnáctková).\n"
     "Nepoziční základ nemá, příklad: římská soustava (I, II, III, IV, V, VI...)."),
    ("Co udává základ soustavy?",
     "Max. počet číslic, které jsou v soustavě k dispozici. Soustava o základu Z má číslice 0 až Z-1.\n"
     "V osmičkové neexistují 8 a 9, po 7 následuje 10."),
    ("Napiš obecný zápis čísla v poziční soustavě o základu Z.",
     "a = a_n·Z^n + a_(n-1)·Z^(n-1) + ... + a_1·Z^1 + a_0·Z^0\n"
     "Nejvyšší mocnina = počet číslic - 1."),
    ("Rozepiš (251)₁₀ a (101)₂ podle obecného zápisu.",
     "(251)₁₀ = 2·10² + 5·10¹ + 1·10⁰ = 200 + 50 + 1 = 251\n"
     "(101)₂  = 1·2² + 0·2¹ + 1·2⁰ = 4 + 0 + 1 = 5"),
    ("Jak se zapisují číslice 10 až 15 v šestnáctkové soustavě?",
     "A=10, B=11, C=12, D=13, E=14, F=15."),
    ("Proč jde převod 2 <-> 16 po čtveřicích bitů a 2 <-> 8 po trojicích?",
     "16 = 2^4 a 8 = 2^3. Jedna hex číslice nese přesně 4 bity, jedna osmičková 3 bity.\n"
     "Např. (1010 1111)₂ = (AF)₁₆. Skupiny se dělí zprava."),
    ("Postup převodu 10 -> Z a Z -> 10?",
     "10 -> Z: dělím základem Z, zapisuji zbytky, dokud podíl není 0; zbytky čtu zdola nahoru.\n"
     "Z -> 10: rozvoj podle obecného zápisu (číslice · Z^pozice, sečíst)."),
    ("Jak se převádí 8 <-> 16?",
     "Oklikou přes dvojkovou: osmičkové číslice na trojice bitů, pak bity po čtveřicích zprava (a naopak)."),
    ("Pravidla sčítání ve dvojkové soustavě?",
     "0+0=0, 0+1=1, 1+0=1, 1+1=(10)₂ -> zapíšu 0, přenos 1 do vyššího řádu.\n"
     "1+1+1=(11)₂ -> zapíšu 1, přenos 1."),
    ("Jak se násobí a dělí ve dvojkové soustavě?",
     "Násobení jako na papíře: pro každou 1 opíšu první číslo posunuté o řád doleva, pak sečtu.\n"
     "Dělení písemně jako v desítkové (odčítám dělitele nebo 0). Dělení nulou není definováno."),
    ("Co znamená N ⊂ Z ⊂ Q ⊂ R ⊂ C?",
     "Každý obor je částí dalšího: přirozená (0, 1, 2...), celá, racionální (zlomky),\n"
     "reálná (i √2, π), komplexní (a + ib)."),
    ("Vysvětli značení n!, |x|, Σ, Π.",
     "n! = 1·2·3·...·n, 0! = 1 (5! = 120)\n"
     "|x| absolutní hodnota: |-5| = 5\n"
     "Σ součet a_1 + ... + a_n, Π součin a_1·...·a_n"),
    ("Čemu se rovná a⁰ a co je zvláštní případ?",
     "a⁰ = 1. Zvláštní případ je 0⁰ (na přednášce naznačeno na tabuli, ověřit)."),
]


# ---------- pomocné funkce ----------
def to_base(n, z):
    if n == 0:
        return "0"
    out = ""
    while n:
        out = DIGITS[n % z] + out
        n //= z
    return out


def num(s, z):
    return f"({s}){str(z).translate(SUBS)}"


def clean(s):
    s = s.upper().replace(" ", "").replace("_", "")
    return s.lstrip("0") or "0"


def groups(s, k):
    s = s.zfill(-(-len(s) // k) * k)
    return [s[i:i + k] for i in range(0, len(s), k)]


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0)


def load():
    try:
        return json.loads(SAVE.read_text())
    except (OSError, ValueError):
        return {"known": []}


def save(data):
    try:
        SAVE.write_text(json.dumps(data))
    except OSError:
        pass


# ---------- postupy ----------
def steps(s, frm, to):
    n = int(s, frm)
    lines = []
    if frm == 10:
        lines.append(f"{'dělení':>12} | {'podíl':>7} | zbytek")
        m = n
        while m > 0:
            r = m % to
            extra = f" = {DIGITS[r]}" if r > 9 else ""
            lines.append(f"{m:>7} : {to:<2} | {m // to:>7} | {r}{extra}")
            m //= to
        lines.append(f"Zbytky zdola nahoru: {to_base(n, to)}")
    elif to == 10:
        L = len(s)
        terms = [f"{DIGITS.index(c)}·{frm}^{L - 1 - i}" for i, c in enumerate(s)]
        vals = [str(DIGITS.index(c) * frm ** (L - 1 - i)) for i, c in enumerate(s)]
        lines.append(" + ".join(terms))
        lines.append("= " + " + ".join(vals) + f" = {n}")
    else:
        k = {2: 1, 8: 3, 16: 4}
        if frm == 2:
            g = groups(s, k[to])
            lines.append(f"Zprava po {k[to]} bitech: " + " | ".join(g))
            lines.append("-> " + " ".join(DIGITS[int(x, 2)] for x in g) + f" = {to_base(n, to)}")
        elif to == 2:
            g = [bin(DIGITS.index(c))[2:].zfill(k[frm]) for c in s]
            lines.append(f"Každá číslice na {k[frm]} bity: " + " | ".join(g))
            lines.append(f"= {to_base(n, 2)} (vedoucí nuly pryč)")
        else:
            b = to_base(n, 2)
            g = groups(b, k[to])
            lines.append(f"Přes dvojkovou: {s} = {b}")
            lines.append(f"Po {k[to]} bitech zprava: " + " | ".join(g) + f" -> {to_base(n, to)}")
    if to != 10:
        lines.append(f"Kontrola zpět do desítkové: {int(to_base(n, to), to)}")
    return "\n".join("   " + x for x in lines)


# ---------- režimy ----------
def mode_cards(data):
    known = set(data["known"])
    todo = [i for i in range(len(CARDS)) if i not in known] or list(range(len(CARDS)))
    if not [i for i in range(len(CARDS)) if i not in known]:
        data["known"] = []
        known = set()
        print("Všechno umíš, začínám znovu.")
    random.shuffle(todo)
    total = len(todo)
    pos = 0
    while pos < len(todo):
        idx = todo[pos]
        print(f"\n[{pos + 1}/{total}] umím: {len(known)}/{len(CARDS)}")
        print(CARDS[idx][0])
        r = ask("   (Enter = ukázat odpověď, q = konec) ")
        if r.lower() == "q":
            break
        print()
        for line in CARDS[idx][1].split("\n"):
            print("   " + line)
        r = ask("   Uměl jsem? [a/n, q = konec] ").lower()
        if r == "q":
            break
        if r.startswith("a"):
            known.add(idx)
        else:
            known.discard(idx)
            todo.append(idx)
        data["known"] = sorted(known)
        save(data)
        pos += 1
    else:
        print(f"\nBalíček hotový. Umíš {len(known)} z {len(CARDS)} kartiček.")


MODES = {
    "1": ("Všechny směry", None), "2": ("Z desítkové (2, 8, 16)", "d2z"),
    "3": ("Do desítkové", "z2d"), "4": ("2 -> 8", (2, 8)), "5": ("8 -> 2", (8, 2)),
    "6": ("2 -> 16", (2, 16)), "7": ("16 -> 2", (16, 2)), "8": ("8 -> 16", (8, 16)),
    "9": ("16 -> 8", (16, 8)),
}


def conv_task(kind):
    if kind is None:
        kind = random.choice(["d2z", "z2d", (2, 8), (8, 2), (2, 16), (16, 2), (8, 16), (16, 8)])
    if kind == "d2z":
        to = random.choice([2, 2, 8, 16])
        return str(random.randint(10, 200 if to == 2 else 900)), 10, to
    if kind == "z2d":
        frm = random.choice([2, 8, 16])
        return to_base(random.randint(10, 200 if frm == 2 else 900), frm), frm, 10
    frm, to = kind
    return to_base(random.randint(16, 250 if frm == 2 else 700), frm), frm, to


def mode_conv(data):
    print("\nSměr převodu:")
    for k, (name, _) in MODES.items():
        print(f"  {k}) {name}")
    kind = MODES.get(ask("Volba [1]: ") or "1", MODES["1"])[1]
    ok = total = 0
    print("\nPiš na papír, výsledek zadej sem. Prázdný řádek = ukázat postup, q = konec.")
    while True:
        s, frm, to = conv_task(kind)
        ans = to_base(int(s, frm), to)
        print(f"\n{num(s, frm)} -> (?){str(to).translate(SUBS)}")
        r = ask("   výsledek: ")
        if r.lower() == "q":
            break
        total += 1
        good = bool(r) and clean(r) == ans
        ok += good
        print("   Správně." if good else f"   Správná odpověď: {num(ans, to)}")
        print(steps(s, frm, to))
        print(f"   [správně {ok}/{total}]")


def mode_arit(data):
    ok = total = 0
    print("\nVýsledek zadej dvojkově. Prázdný řádek = ukázat postup, q = konec.")
    while True:
        op = random.choice(["+", "+", "-", "*", "/"])
        if op == "+":
            a, b = random.randint(5, 40), random.randint(3, 30)
            r = a + b
        elif op == "-":
            a = random.randint(10, 45)
            b = random.randint(3, a - 1)
            r = a - b
        elif op == "*":
            a, b = random.randint(3, 15), random.randint(2, 7)
            r = a * b
        else:
            b = random.randint(2, 7)
            r = random.randint(2, 12)
            a = b * r
        sym = {"+": "+", "-": "−", "*": "·", "/": ":"}[op]
        A, B, R = bin(a)[2:], bin(b)[2:], bin(r)[2:]
        print(f"\n{num(A, 2)} {sym} {num(B, 2)} = ?")
        ans = ask("   výsledek (dvojkově): ")
        if ans.lower() == "q":
            break
        total += 1
        good = bool(ans) and clean(ans) == R
        ok += good
        print("   Správně." if good else f"   Správná odpověď: {num(R, 2)}")
        print(f"   Desítkově: {a} {sym} {b} = {r}")
        if op == "*":
            parts = [A + "0" * i for i, c in enumerate(reversed(B)) if c == "1"]
            print("   Dílčí součiny (posun o řád): " + " + ".join(parts))
        elif op == "-":
            print(f"   Kontrola sčítáním: {R} + {B} = {A}")
        elif op == "/":
            print(f"   Kontrola násobením: {R} · {B} = {A}")
        else:
            print("   Sčítej zprava, 1+1 = 10 (zapiš 0, přenos 1).")
        print(f"   [správně {ok}/{total}]")


def cli_main():
    data = load()
    print("TZI Trenér: KI/TIN, 1. přednáška (číselné soustavy)")
    while True:
        print("\n1) Teorie (kartičky)\n2) Převody\n3) Aritmetika ve dvojkové soustavě\nq) Konec")
        c = ask("Volba: ").lower()
        if c == "1":
            mode_cards(data)
        elif c == "2":
            mode_conv(data)
        elif c == "3":
            mode_arit(data)
        elif c == "q":
            break


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def serve(port=8000):
    """Spustí lokální server s webovým rozhraním a otevře prohlížeč."""
    for p in range(port, port + 20):
        try:
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit("Nenašel jsem volný port (8000-8019).")
    url = f"http://127.0.0.1:{p}/"
    print(f"TZI Trenér běží na {url}\nUkončíš ho přes Ctrl+C.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKonec.")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_main()
    else:
        serve()
