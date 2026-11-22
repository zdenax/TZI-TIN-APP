#!/usr/bin/env python3
"""Vygeneruje speciální sadu „Rychlokurz: gramatiky a zásobníkové automaty“ do banky/08z-rychlokurz.json (id 8z-N).

Sada je řízený dvouhodinový kurz: projíždí se „Vše popořadě“, každá položka má pole `theory`
(krátký výklad, novy.html ho ukáže v rámečku nad otázkou) a hned za ním otázku na tu látku.
Pořadí kopíruje plán: gramatiky (0:00–0:50), pauza, zásobníkové automaty (1:00–1:55), rekapitulace.

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Opus 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z výpisků přednášek 12. 11. 2026 (gramatiky) a 19. 11. 2026 (zásobníkové automaty)
a ze cvičení 19. 11. 2026 (vault TZI1), včetně doplňků „Doplněno z Claude“, které jsou ve výpiscích
ověřené proti Chytilovi (Automaty a gramatiky, kap. 3.1–3.3 a 4.4) a Barillovi (kap. 4 a 8).
Z knih jsou jen odkazy na číslo definice a stranu a krátké parafráze.
Všechna odvození, výpočty zásobníkových automatů, jazyky a počty kroků se tu počítají a ověřují
(prohledávání přepisů, simulace všech výpočtů ZA), ne ručně v JSON.
Id 8z-N jsou pevná (váže se na ně uložený postup): nové otázky jen na konec.
Zapisuje se JEN banky/08z-rychlokurz.json.
Spuštění:  python3 build_bank_rychlokurz.py
"""
import itertools
import json
from collections import deque
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "banky" / "08z-rychlokurz.json"
CHECKS = 0
G12, Z19, CV = "Přednáška 12. 11.", "Přednáška 19. 11.", "Cvičení 19. 11."
RULES_HINT = "čísla pravidel v pořadí použití, bez mezer, např. 312"
RULES_HINT_SP = "čísla pravidel v pořadí použití oddělená mezerou, např. 2 10 9"
YN = "ano nebo ne (bez tečky)"


def check(cond, msg=""):
    global CHECKS
    assert cond, msg
    CHECKS += 1


# ── přepisy: slovo = řetězec, symboly jsou jednopísmenné ──

def steps(form, rules):
    """Všechny přímé přepisy: (číslo pravidla od 1, pozice, výsledek)."""
    out = []
    for i, (x, y) in enumerate(rules, 1):
        for p in range(len(form) - len(x) + 1):
            if form.startswith(x, p):
                out.append((i, p, form[:p] + y + form[p + len(x):]))
    return out


def follows(start, rules, seq, target):
    """Jde ze start dojít do target přesně posloupností pravidel seq (na nějakých místech)?"""
    forms = {start}
    for r in seq:
        forms = {z for f in forms for i, _, z in steps(f, rules) if i == r}
    return target in forms


def language(start, rules, terminals, maxlen, slack=4):
    """Terminální slova do délky maxlen odvoditelná ze start (formy omezené délkou maxlen + slack)."""
    seen, todo, out = {start}, deque([start]), set()
    while todo:
        f = todo.popleft()
        if all(c in terminals for c in f):
            if len(f) <= maxlen:
                out.add(f)
            continue
        for _, _, z in steps(f, rules):
            if len(z) <= maxlen + slack and z not in seen:
                seen.add(z)
                todo.append(z)
    return out


def min_steps(start, rules, target, limit=12):
    dist, todo = {start: 0}, deque([start])
    while todo:
        f = todo.popleft()
        if f == target:
            return dist[f]
        if dist[f] >= limit:
            continue
        for _, _, z in steps(f, rules):
            if z not in dist and len(z) <= len(target) + 2:
                dist[z] = dist[f] + 1
                todo.append(z)
    return None


# ── zásobníkový automat: delta[(q, a nebo "", X)] = [(q', slovo do zásobníku)], vrchol vlevo ──

def pda_runs(delta, q0, z0, w, limit=60):
    """Všechny dosažitelné situace (q, zbytek, zásobník) ze (q0, w, z0)."""
    start = (q0, w, z0)
    seen, todo = {start}, deque([start])
    while todo:
        q, rest, st = todo.popleft()
        if not st:
            continue  # prázdný zásobník: žádný krok
        nxt = [(p, rest, eta + st[1:]) for p, eta in delta.get((q, "", st[0]), [])]
        if rest:
            nxt += [(p, rest[1:], eta + st[1:]) for p, eta in delta.get((q, rest[0], st[0]), [])]
        for s in nxt:
            if s not in seen and len(s[2]) <= limit:
                seen.add(s)
                todo.append(s)
    return seen


def acc_final(delta, q0, z0, F, w):
    return any(r == "" and q in F for q, r, _ in pda_runs(delta, q0, z0, w))


def acc_empty(delta, q0, z0, w):
    return any(r == "" and st == "" for _, r, st in pda_runs(delta, q0, z0, w))


def pda_trace(delta, rules_order, q0, z0, w, seq):
    """Výpočet podle čísel instrukcí seq; vrátí seznam situací. rules_order[i-1] = (q, a, X, q', eta)."""
    sit = [(q0, w, z0)]
    for r in seq:
        q, a, X, p, eta = rules_order[r - 1]
        cq, rest, st = sit[-1]
        check(cq == q and st[:1] == X and (a == "" or rest[:1] == a), f"instrukce {r} nejde použít v {sit[-1]}")
        check((p, eta) in delta[(q, a, X)])
        sit.append((p, rest[1:] if a else rest, eta + st[1:]))
    return sit


def words(alpha, n):
    return ["".join(t) for k in range(n + 1) for t in itertools.product(alpha, repeat=k)]


def deterministic(delta, sigma):
    for (q, a, X), v in delta.items():
        if len(v) > 1:
            return False
        if a == "" and v and any(delta.get((q, b, X)) for b in sigma):
            return False
    return True


# ── zápis ──

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def sit_txt(s, z_names=None):
    q, rest, st = s
    q = q[0] + q[1:].translate(SUB) if len(q) > 1 and q[1:].isdigit() else q
    st = st.replace("Z0", "Z₀") if z_names is None else st
    return f"({q}, {rest or 'e'}, {st or 'e'})"


Q = []


def add(qd):
    Q.append(qd)


def choice(theory, text, correct, wrong, explanation):
    opts = dict(zip("ABCD", [correct] + wrong))
    add({"type": "choice", "theory": theory, "text": text, "options": opts, "correct": ["A"],
         "explanation": explanation})


def inp(theory, text, answer, hint, solution):
    add({"type": "input", "theory": theory, "text": text, "answer": answer, "hint": hint, "solution": solution})


def reveal(theory, text, solution):
    add({"type": "input", "reveal": True, "theory": theory, "text": text, "solution": solution})


# ════════════════ ČÁST 1: GRAMATIKY ════════════════

# — 0:00–0:15 pojmy —
choice(
    "⏱ 0:00 · ČÁST 1: GRAMATIKY (do 0:50). Pojmy: přepis a odvození.\n"
    "Přepisovací systém je R = (V, P): V je konečná abeceda, P konečná množina pravidel u → v (u, v ∈ V*).\n"
    "Přímý přepis u ⇒ z: ve slově u najdu levou stranu x nějakého pravidla x → y a nahradím ji pravou stranou y. "
    "Okolí zůstane: u = v x w, z = v y w. Jedno pravidlo, jednou.",
    "Co přesně je přímý přepis u ⇒ z?",
    "Jedno použití jednoho pravidla x → y na jeden výskyt x ve slově u.",
    ["Použití všech pravidel z P najednou na celé slovo u.",
     "Nahrazení celého slova u slovem z bez ohledu na pravidla.",
     "Libovolně dlouhý řetěz použití pravidel."],
    "u = v x w a z = v y w, kde x → y ∈ P. Řetěz kroků je až ⇒*. Chytil, Def. 3.1.2, s. 118. " + G12)

inp(
    "Přepis (odvození) u ⇒* z je řetěz přímých přepisů u ⇒ u₁ ⇒ … ⇒ z. Smí mít i nula kroků (⇒* je reflexivní).\n"
    "Odvození je minimální, když se v něm žádné slovo neopakuje. Lemma: když u ⇒* z, existuje i minimální odvození "
    "(opakující se úsek se vyhodí).\n"
    "U odvození vždy podtrhni přepsanou část a nad ⇒ napiš číslo pravidla.",
    "Přepisovací systém z přednášky: V = {0, 1}, pravidla (1) 01 → 10, (2) 10 → 01. Odvození 00110 ⇒ 00101 ⇒ 00011: "
    "napiš čísla použitých pravidel.",
    "22", RULES_HINT,
    "Oba kroky pravidlem 2 (10 → 01): nejdřív poslední dvojice 10 v 00110, pak 10 na 3.–4. místě v 00101. "
    "Chytil, Př. 3.1.3, s. 118–119. " + G12)
R1 = [("01", "10"), ("10", "01")]
check(follows("00110", R1, [2, 2], "00011"))
check(min_steps("00110", R1, "00011") == 2)

inp(
    "⇒* je reflexivní: každé slovo se přepíše samo na sebe nulou kroků.",
    "Přepisovací systém: V = {0, 1}, pravidla (1) 01 → 10, (2) 10 → 01. Platí 0110 ⇒* 0110?",
    "ano", YN,
    "Ano, odvození délky 0 (žádný krok) je dovolené, ⇒* je reflexivní a tranzitivní uzávěr ⇒. Chytil, s. 118. " + G12)

choice(
    "Generativní gramatika je G = (Π, Σ, S, P):\n"
    "• Π neterminály (velká písmena), Σ terminály (malá písmena, číslice), Π ∩ Σ = ∅,\n"
    "• S ∈ Π počáteční symbol,\n"
    "• P pravidla α → β, kde levá strana α (to, co je PŘED šipkou) obsahuje aspoň jeden neterminál, tedy aspoň "
    "jedno VELKÉ písmeno z Π. Pravá strana může být cokoli, i prázdné slovo e.",
    "Gramatika má Π = {S, B}, Σ = {a, b}. Které pravidlo v generativní gramatice NENÍ dovolené?",
    "ab → ba",
    ["aB → Ba", "S → e", "B → aSb"],
    "Levá strana ab neobsahuje žádný neterminál. Proto se v úloze 2 ze cvičení prohazují aB, aC, BC, "
    "ne přímo terminály. Chytil, Def. 3.1.5, s. 119. " + G12)

choice(
    "Jazyk gramatiky: L(G) = {w ∈ Σ*; S ⇒* w}.\n"
    "Začnu slovem S a přepisuji, dokud nezůstanou jen terminály. Slovo, ve kterém ještě je neterminál, do L(G) nepatří.",
    "Gramatika z přednášky: Π = {S, B, C}, Σ = {a, b, c}, pravidla (1) S → aBb, (2) B → aCc, (3) C → bBa, "
    "(4) B → a, (5) C → b. Platí S ⇒ aBb. Patří aBb do L(G)?",
    "Ne, obsahuje neterminál B, v L(G) jsou jen slova z Σ*.",
    ["Ano, protože se odvodí z S.",
     "Ano, protože je odvozené jedním krokem.",
     "Ne, protože aBb nemá stejný počet a a b."],
    "L(G) obsahuje jen terminální slova. aBb je jen mezikrok (větná forma). " + G12)

inp(
    "Odvození v gramatice zapisuj stejně: podtrhni neterminál, který přepisuješ, a nad ⇒ napiš číslo pravidla.",
    "Gramatika z přednášky: Π = {S, B, C}, Σ = {a, b, c}, pravidla (1) S → aBb, (2) B → aCc, (3) C → bBa, "
    "(4) B → a, (5) C → b. Napiš čísla pravidel odvození S ⇒* aabaacb.",
    "1234", RULES_HINT,
    "S ⇒(1) aBb ⇒(2) aaCcb ⇒(3) aabBacb ⇒(4) aabaacb. Je to jediné odvození tohoto slova. " + G12)
G7 = [("S", "aBb"), ("B", "aCc"), ("C", "bBa"), ("B", "a"), ("C", "b")]
check(follows("S", G7, [1, 2, 3, 4], "aabaacb"))
check(all(not follows("S", G7, list(s), "aabaacb") for s in itertools.product(range(1, 6), repeat=4) if list(s) != [1, 2, 3, 4]))

choice(
    "Analytická gramatika má stejné (Π, Σ, S, P), ale neterminál musí být na PRAVÉ straně pravidla, "
    "a L(G) = {w ∈ Σ*; w ⇒* S}: slovo se „sbaluje“ zpátky na S (jako rozbor věty).\n"
    "Obrátím-li šipky generativní gramatiky, dostanu analytickou se stejným jazykem.",
    "Čím se liší analytická gramatika od generativní?",
    "Neterminál musí být na pravé straně pravidla a slovo se přepisuje na S, ne z S.",
    ["Nemá počáteční symbol S.",
     "Smí mít jen pravidla tvaru X → aY.",
     "Generuje vždy konečný jazyk."],
    "Generativní: neterminál vlevo, S ⇒* w. Analytická: neterminál vpravo, w ⇒* S. Chytil, Def. 3.1.8, s. 123–124. " + G12)

# — 0:15–0:25 cvičení, úloha 1 —
G01 = [("S", "0S1"), ("S", "01")]
choice(
    "⏱ 0:15 · Cvičení, úloha 1: gramatika pro {0ⁿ1ⁿ; n ≥ 1}.\n"
    "Nápad: pravidlo S → 0S1 přidá najednou jednu 0 vlevo a jednu 1 vpravo, počty tedy zůstanou stejné. "
    "Pravidlo S → 01 odvození ukončí (S zmizí).\n"
    "S → e místo S → 01 by do jazyka přidalo prázdné slovo, které tam při n ≥ 1 není.",
    "Která gramatika (Π = {S}, Σ = {0, 1}) generuje přesně {0ⁿ1ⁿ; n ≥ 1}?",
    "S → 0S1, S → 01",
    ["S → 0S1, S → e", "S → 0S, S → S1, S → 01", "S → 0S1"],
    "S → e přidá prázdné slovo; 0S a S1 zvlášť rozbijí počty (vznikne 001); bez ukončovacího pravidla S nezmizí "
    "a L(G) = ∅. Ověřeno výpočtem do délky 10. " + CV)
target = {"0" * n + "1" * n for n in range(1, 6)}
check(language("S", G01, "01", 10) == target)
check(language("S", [("S", "0S1"), ("S", "")], "01", 10) == target | {""})
check("001" in language("S", [("S", "0S"), ("S", "S1"), ("S", "01")], "01", 6))
check(language("S", [("S", "0S1")], "01", 10) == set())

inp(
    "Gramatika z úlohy 1: (1) S → 0S1, (2) S → 01. Každé použití pravidla 1 přidá jednu dvojici 0…1, pravidlo 2 přidá "
    "poslední dvojici 01 doprostřed.",
    "Gramatika: Π = {S}, Σ = {0, 1}, pravidla (1) S → 0S1, (2) S → 01. Napiš čísla pravidel odvození S ⇒* 000111.",
    "112", RULES_HINT,
    "S ⇒(1) 0S1 ⇒(1) 00S11 ⇒(2) 000111. Tedy S ⇒* 000111 a 000111 ∈ L(G). " + CV)
check(follows("S", G01, [1, 1, 2], "000111"))

inp(
    "Na 0ⁿ1ⁿ je potřeba (n − 1)× pravidlo 1 a jednou pravidlo 2.",
    "Gramatika: Π = {S}, Σ = {0, 1}, pravidla (1) S → 0S1, (2) S → 01. Kolik kroků má odvození slova 0000011111?",
    "5", "číslo",
    "4× pravidlo 1 a 1× pravidlo 2: S ⇒ 0S1 ⇒ 00S11 ⇒ 000S111 ⇒ 0000S1111 ⇒ 0000011111. " + CV)
check(min_steps("S", G01, "0000011111") == 5)

choice(
    "Častá varianta zadání: změní se dolní mez nebo poměr počtů. Ukončovací pravidlo odpovídá nejmenšímu slovu jazyka, "
    "opakující se pravidlo přidává „jednu jednotku“.",
    "Jak upravit gramatiku, aby generovala {0ⁿ1²ⁿ; n ≥ 1} (za každou nulu dvě jedničky)?",
    "S → 0S11, S → 011",
    ["S → 0S1, S → 011", "S → 00S1, S → 001", "S → 0S11, S → e"],
    "Každá 0 musí přinést dvě 1 a nejmenší slovo je 011. Ověřeno výpočtem do délky 12. " + CV)
check(language("S", [("S", "0S11"), ("S", "011")], "01", 12) == {"0" * n + "1" * (2 * n) for n in range(1, 5)})
check("0011" not in language("S", [("S", "0S11"), ("S", "011")], "01", 12))

reveal(
    "Na papír: odvoď sám 000111 v gramatice S → 0S1 | 01. U každého kroku podtrhni přepisované S, nad ⇒ napiš číslo "
    "pravidla a urči v, x, w (okolí a přepsanou část). Až pak odkryj řešení.",
    "Gramatika: (1) S → 0S1, (2) S → 01. Rozepiš odvození S ⇒* 000111 po přímých přepisech (u = v x w, z = v y w).",
    "krok 1: S, v = e, x = S, w = e, pravidlo 1 → 0S1\n"
    "krok 2: 0S1, v = 0, x = S, w = 1, pravidlo 1 → 00S11\n"
    "krok 3: 00S11, v = 00, x = S, w = 11, pravidlo 2 → 000111\n"
    "S ⇒(1) 0S1 ⇒(1) 00S11 ⇒(2) 000111, tedy 000111 ∈ L(G). " + CV)

# — 0:25–0:40 cvičení, úloha 2 —
G3 = [("S", "SaBC"), ("S", "aBC"), ("aB", "Ba"), ("Ba", "aB"), ("aC", "Ca"), ("Ca", "aC"),
      ("BC", "CB"), ("CB", "BC"), ("B", "b"), ("C", "c")]
G3TXT = ("Gramatika úlohy 2: Π = {S, B, C}, Σ = {a, b, c}, pravidla (1) S → SaBC, (2) S → aBC, (3) aB → Ba, "
         "(4) Ba → aB, (5) aC → Ca, (6) Ca → aC, (7) BC → CB, (8) CB → BC, (9) B → b, (10) C → c.")
choice(
    "⏱ 0:25 · Cvičení, úloha 2: slova se stejným počtem a, b, c.\n"
    "1. Počty: pravidla 1 a 2 vyrobí n trojic aBC, každá přidá jedno a, jedno B, jedno C.\n"
    "2. Pořadí: pravidla 3–8 prohazují sousední a, B, C oběma směry (jako bubble sort), takže jde dostat libovolné pořadí.\n"
    "3. Dokončení: pravidla 9 a 10 přepíšou B → b, C → c.",
    "Proč gramatika úlohy 2 pracuje s neterminály B a C, a ne rovnou s terminály b a c?",
    "Levá strana pravidla musí obsahovat neterminál, pravidlo ab → ba by nebylo dovolené.",
    ["Terminály se v gramatice nesmí opakovat.",
     "Neterminály jsou kratší na zápis.",
     "Jinak by gramatika byla regulární."],
    "V generativní gramatice musí mít každé pravidlo vlevo neterminál (Chytil, Def. 3.1.5, s. 119). Dvojice aB, aC, BC "
    "ho obsahují. Gramatika je Chytilův Př. 3.1.6 bod 2, s. 120–121. " + CV)
L3 = language("S", G3, "abc", 6, slack=0)
check(L3 == {w for w in words("abc", 6) if w and w.count("a") == w.count("b") == w.count("c")})
check(len(L3) == 96)

inp(
    "Postup na krátké slovo: nejdřív pravidly 1 a 2 vyrob správný počet trojic, pak prohazuj, nakonec přepiš B a C. "
    "Prohazovat smíš jen dvojice, ve kterých je neterminál.",
    G3TXT + " Napiš čísla pravidel odvození S ⇒* cab (S ⇒ aBC ⇒ aCB ⇒ CaB ⇒ caB ⇒ cab).",
    "2 7 5 10 9", RULES_HINT_SP,
    "S ⇒(2) aBC ⇒(7) aCB ⇒(5) CaB ⇒(10) caB ⇒(9) cab. " + CV)
check(follows("S", G3, [2, 7, 5, 10, 9], "cab"))

inp(
    "Nejkratší odvození: kolik trojic je ve slově, tolik pravidel 1 a 2 dohromady; každé b a c stojí jeden krok "
    "(pravidla 9 a 10); prohazování jen tam, kde pořadí aBC nesedí.",
    G3TXT + " Kolik kroků má nejkratší odvození slova abcabc?",
    "6", "číslo",
    "S ⇒(1) SaBC ⇒(2) aBCaBC ⇒(9) abCaBC ⇒(10) abcaBC ⇒(9) abcabC ⇒(10) abcabc. Prohazovat netřeba. Ověřeno "
    "prohledáním všech odvození. " + CV)
check(min_steps("S", G3, "abcabc") == 6)
check(follows("S", G3, [1, 2, 9, 10, 9, 10], "abcabc"))

CAA = [1, 1, 2, 7, 5, 10, 4, 9, 9, 10, 3, 10, 9]
check(follows("S", G3, CAA, "caabbcbac"))
reveal(
    "Na papír (hlavní úloha cvičení, ~10 minut): odvoď caabbcbac. Tři trojice (1, 1, 2), pak prohazuj a přepisuj zleva. "
    "Podtrhávej a čísluj. Až pak odkryj řešení.",
    G3TXT + " Odvoď S ⇒* caabbcbac.",
    "S ⇒(1) SaBC ⇒(1) SaBCaBC ⇒(2) aBCaBCaBC\n"
    "⇒(7) aCBaBCaBC ⇒(5) CaBaBCaBC ⇒(10) caBaBCaBC\n"
    "⇒(4) caaBBCaBC ⇒(9) caabBCaBC ⇒(9) caabbCaBC\n"
    "⇒(10) caabbcaBC ⇒(3) caabbcBaC ⇒(10) caabbcBac ⇒(9) caabbcbac\n"
    "13 kroků, výsledek jen z terminálů, tedy caabbcbac ∈ L(G). Pořadí kroků je Chytilovo (Př. 3.1.6, s. 120–121), "
    "každý krok ověřen výpočtem. " + CV)

# — 0:40–0:50 Chomského hierarchie —
choice(
    "⏱ 0:40 · Chomského hierarchie (bude zkoušet!). Typ podle tvaru pravidel, X, Y ∈ Π, w ∈ Σ*:\n"
    "• typ 0 obecná: α → β, vlevo aspoň jeden neterminál,\n"
    "• typ 1 kontextová: αXβ → αγβ, γ neprázdné (jediná výjimka S → e, pak S není na žádné pravé straně),\n"
    "• typ 2 bezkontextová: X → γ (vlevo jediný neterminál, γ libovolné, i e),\n"
    "• typ 3 regulární: X → wY nebo X → w (nejvýš jeden neterminál, úplně vpravo).\n"
    "𝓛₃ ⊆ 𝓛₂ ⊆ 𝓛₁ ⊆ 𝓛₀.",
    "Která gramatika má pravidla tvaru X → γ, kde X je jeden neterminál a γ ∈ (Π ∪ Σ)*?",
    "Bezkontextová (typ 2)",
    ["Regulární (typ 3)", "Kontextová (typ 1)", "Analytická"],
    "Vlevo jediný neterminál, přepíše se bez ohledu na okolí. Chytil, Def. 3.2.1 bod 3, s. 124. " + G12)


def typ(left, right, N="SXYZB C".replace(" ", "")):
    """Nejvyšší typ jednoho pravidla podle Chytila, Def. 3.2.1 (bez speciálního S → e)."""
    isN = lambda c: c in N
    t = 0
    if any(isN(c) for c in left):
        for i, c in enumerate(left):
            if isN(c):
                a, b = left[:i], left[i + 1:]
                if right.startswith(a) and right.endswith(b) and len(right) - len(a) - len(b) >= 1:
                    t = 1
    if len(left) == 1 and isN(left):
        t = 2
        nn = [i for i, c in enumerate(right) if isN(c)]
        if not nn or (len(nn) == 1 and nn[0] == len(right) - 1):
            t = 3
    return t


for l, r, ans, why in [
    ("S", "0S1", "2", "vlevo jeden neterminál, ale vpravo stojí za neterminálem terminál 1, regulární tedy ne"),
    ("X", "aY", "3", "neterminál je jen jeden a úplně vpravo"),
    ("aB", "Ba", "0", "vlevo dva symboly (bezkontextové ne) a mění se obě pozice, tvar αXβ → αγβ to není"),
    ("aXb", "aYZb", "1", "X v kontextu a…b se přepíše na neprázdné YZ, okolí zůstane"),
]:
    check(typ(l, r) == int(ans), (l, r))
    inp(
        "Postup: 1) je vlevo jediný neterminál? ne → zkus typ 1 (okolí α, β zůstane, přepíše se jeden neterminál na neprázdné), "
        "jinak typ 0. 2) ano → typ 2; navíc je vpravo nejvýš jeden neterminál úplně na konci → typ 3.",
        f"X, Y, Z, B, S ∈ Π, a, b, 0, 1 ∈ Σ. Jaký je nejvyšší typ Chomského hierarchie, jehož tvar splňuje pravidlo {l} → {r}?",
        ans, "číslo 0 až 3",
        f"Typ {ans}: {why}. Chytil, Def. 3.2.1, s. 124–125. " + G12)

choice(
    "Typ gramatiky = nejvyšší typ, který splňují VŠECHNA její pravidla.\n"
    "Úloha 1: S → 0S1, S → 01. Úloha 2 má prohazovací pravidla aB → Ba, BC → CB.",
    "Jakého typu jsou gramatiky ze cvičení (úloha 1, úloha 2)?",
    "Úloha 1 typ 2 (bezkontextová), úloha 2 typ 0 (obecná).",
    ["Obě typ 2.", "Úloha 1 typ 3, úloha 2 typ 1.", "Obě typ 0."],
    "Úloha 1: obě pravidla X → γ, regulární není (0S1). Úloha 2: prohození aB → Ba nemá tvar αXβ → αγβ, formálně "
    "typ 0 (jestli jde jazyk generovat vyšším typem, je jiná otázka). Chytil, Def. 3.2.1, s. 124. " + CV)
check(min(typ(l, r) for l, r in G01) == 2)
check(min(typ(l, r) for l, r in G3) == 0)

choice(
    "Gramatiky a automaty (tabulka ze zkoušky):\n"
    "• typ 3 regulární ↔ konečný automat (Kleeneova věta: regulární ⇔ rozpoznatelný KA),\n"
    "• typ 2 bezkontextové ↔ (nedeterministický) zásobníkový automat,\n"
    "• typ 1 kontextové ↔ lineárně omezený Turingův stroj,\n"
    "• typ 0 ↔ Turingův stroj.\n"
    "Gramatiku ke KA: stavy = neterminály, S = q₀, za δ(q, a) = q' pravidlo q → aq', za koncový q pravidlo q → e.",
    "Jaký automat rozpoznává jazyk {0ⁿ1ⁿ; n ≥ 1} z úlohy 1, když konečný automat na něj nestačí?",
    "Zásobníkový automat (jazyk je bezkontextový, typ 2).",
    ["Konečný automat s více stavy.", "Jen Turingův stroj.", "Žádný automat."],
    "Jazyk není regulární (Chytil, 1.3.6), je bezkontextový; bezkontextové jazyky rozpoznávají zásobníkové automaty "
    "(Chytil, čl. 4.5, s. 172). Na to navazuje část 2. " + G12)

# ════════════════ ČÁST 2: ZÁSOBNÍKOVÉ AUTOMATY ════════════════

choice(
    "⏸ 0:50–1:00 PAUZA 10 minut, odejdi od obrazovky. Pak pokračuj.\n"
    "⏱ 1:00 · ČÁST 2: ZÁSOBNÍKOVÉ AUTOMATY. Zásobníkový automat (ZA) = konečný automat + zásobník "
    "(čte a píše se jen nahoře). Je to sedmice M = (Q, Σ, Γ, δ, q₀, Z₀, F):\n"
    "Q stavy, Σ vstupní abeceda, Γ zásobníková abeceda, δ přechodová funkce, q₀ počáteční stav, "
    "Z₀ ∈ Γ počáteční zásobníkový symbol (na začátku je v zásobníku jen on), F ⊆ Q koncové stavy.",
    "Co je v sedmici zásobníkového automatu Γ?",
    "Zásobníková abeceda: symboly, které smí být v zásobníku.",
    ["Množina koncových stavů.", "Vstupní abeceda.", "Počáteční obsah zásobníku."],
    "Γ (gama) je zásobníková abeceda, Σ vstupní, F koncové stavy, Z₀ počáteční symbol zásobníku. "
    "Chytil, Def. 4.4.1, s. 164. " + Z19)

choice(
    "δ : Q × (Σ ∪ {e}) × Γ → konečné podmnožiny Q × Γ*.\n"
    "δ(q, a, X) = {(q₁, η₁), …, (qₘ, ηₘ)}: ve stavu q, při čtení a, s X nahoře MŮŽE přejít do qᵢ a X nahradit slovem ηᵢ.\n"
    "Hodnota je MNOŽINA možností, proto je ZA obecně nedeterministický. δ = ∅ znamená „není definováno“, výpočet "
    "v té větvi skončí.",
    "Proč je zásobníkový automat obecně nedeterministický?",
    "δ vrací množinu dvojic (stav, slovo do zásobníku), možností může být víc.",
    ["Protože má zásobník.", "Protože nemá koncové stavy.", "Protože čte vstup zprava doleva."],
    "Chytil, s. 164. Deterministický ZA je zvláštní případ (viz dál). " + Z19)

inp(
    "Jak se mění zásobník (zápis zleva, VRCHOL VLEVO): vrchní X se vždy nahradí slovem η.\n"
    "• η = e → X se odebere (pop),\n"
    "• η = X → beze změny,\n"
    "• η = YX → nad X přibude Y (push),\n"
    "• η = Y → X se vymění za Y.",
    "Pravidlo (q', AZ) ∈ δ(q, 0, Z), v zásobníku je jen Z. Co je po kroku na vrcholu zásobníku?",
    "A", "jeden symbol",
    "Z se nahradí slovem AZ: první symbol slova je nahoře, tedy nahoře A, pod ním Z (push). Chytil, s. 164. " + Z19)

choice(
    "e-krok: δ(q, e, X) = {…}. Automat změní stav a vrchol zásobníku, ale nic nepřečte, hlava na pásce stojí.",
    "Co udělá krok podle (q', e) ∈ δ(q, e, Z)?",
    "Nic nepřečte, přejde do q' a odebere Z ze zásobníku.",
    ["Přečte symbol e ze vstupu a Z nechá.", "Přečte jeden symbol a zásobník vyprázdní celý.",
     "Ukončí výpočet a slovo odmítne."],
    "e na místě vstupu = nečte se; e jako nové slovo do zásobníku = pop. Chytil, s. 165. " + Z19)

choice(
    "Situace (konfigurace) je trojice (q, w, η): stav, ZBÝVAJÍCÍ část vstupu, obsah zásobníku (vrchol vlevo).\n"
    "Počáteční situace je (q₀, w, Z₀).",
    "Co je ve situaci (q, w, η) druhá složka w?",
    "Úsek vstupního slova, který automat ještě nepřečetl.",
    ["Celé vstupní slovo.", "Již přečtená část vstupu.", "Obsah zásobníku."],
    "Chytil, Def. 4.4.2, s. 165–166. " + Z19)

D_EX = {("q1", "0", "A"): [("q1", "AA")]}
check(pda_trace(D_EX, [("q1", "0", "A", "q1", "AA")], "q1", "AZ", "011", [1])[-1] == ("q1", "11", "AAZ"))
inp(
    "Krok ⊢: (q, aw, Yη) ⊢ (q', w, νη), když (q', ν) ∈ δ(q, a, Y), a ∈ Σ ∪ {e}.\n"
    "Krok se dívá jen na tři věci: stav, první symbol zbytku vstupu, vrchol zásobníku. Zbytek pásky w a zbytek "
    "zásobníku η se nemění.",
    "Pravidlo δ(q₁, 0, A) = {(q₁, AA)}. Situace (q₁, 011, AZ) vede jedním krokem k (q₁, 11, ?). Co je na místě otazníku "
    "(obsah zásobníku)?",
    "AAZ", "obsah zásobníku, vrchol vlevo, např. ABZ",
    "(q₁, 011, AZ) ⊢ (q₁, 11, AAZ): přečte 0 (zbude 11), vrchol A se nahradí AA, pod ním zůstane Z. "
    "Chytil, Def. 4.4.2, s. 166. " + Z19)

inp(
    "⊢* = řetěz kroků (i nula). Důležité: ze situace s PRÁZDNÝM zásobníkem už žádný krok nevede, každý krok "
    "potřebuje vrchní symbol (ani e-krok nejde).",
    "Může ze situace (q, 01, e) vést nějaký krok?",
    "ne", YN,
    "Zásobník je prázdný, není vrchol Y, žádná instrukce nejde použít. Chytil, Pozn. 4.4.3, s. 166. " + Z19)

choice(
    "Dva způsoby přijetí slova:\n"
    "• koncovým stavem: L(M) = {w; (q₀, w, Z₀) ⊢* (q, e, η), q ∈ F}: celé přečteno, stav koncový, zásobník cokoli,\n"
    "• prázdným zásobníkem: N(M) = {w; (q₀, w, Z₀) ⊢* (q, e, e)}: celé přečteno, zásobník prázdný, stav libovolný.\n"
    "Stačí JEDEN takový výpočet. U prázdného zásobníku se klade F = ∅.",
    "Kdy je slovo přijato prázdným zásobníkem?",
    "Když existuje výpočet, po kterém je celé slovo přečtené a zásobník prázdný.",
    ["Když automat skončí v koncovém stavu.", "Když je vstupní slovo prázdné.",
     "Když všechny výpočty skončí s prázdným zásobníkem."],
    "N(M), stav je libovolný (proto F = ∅). Chytil, Def. 4.4.4, s. 166–167. " + Z19)

# — 1:15 příklady aba —
P1 = [("q0", "a", "Z0", "q0", "AZ0"), ("q0", "b", "A", "q1", "B"), ("q1", "a", "B", "q2", "A")]
P2 = [("q0", "a", "Z0", "q0", "A"), ("q0", "b", "A", "q1", "B"), ("q1", "a", "B", "q2", "")]


def as_delta(rs):
    d = {}
    for q, a, X, p, eta in rs:
        d.setdefault((q, a, X), []).append((p, eta))
    return d


def tok(rs):
    """Zásobník po symbolech: Z0 jako jeden znak 'Z'."""
    return [(q, a, X.replace("Z0", "Z"), p, eta.replace("Z0", "Z")) for q, a, X, p, eta in rs]


D1, D2 = as_delta(tok(P1)), as_delta(tok(P2))
check({w for w in words("ab", 8) if acc_final(D1, "q0", "Z", {"q2"}, w)} == {"aba"})
check({w for w in words("ab", 8) if acc_empty(D1, "q0", "Z", w)} == set())
check({w for w in words("ab", 8) if acc_empty(D2, "q0", "Z", w)} == {"aba"})
check(deterministic(D1, "ab") and deterministic(D2, "ab"))
T1 = pda_trace(D1, tok(P1), "q0", "Z", "aba", [1, 2, 3])
T2 = pda_trace(D2, tok(P2), "q0", "Z", "aba", [1, 2, 3])
check(T1[-1] == ("q2", "", "AZ") and T2[-1] == ("q2", "", ""))
fmtsit = lambda s: sit_txt((s[0], s[1], s[2].replace("Z", "Z₀")), z_names=1)

P1TXT = ("Q = {q₀, q₁, q₂}, Σ = {a, b}, Γ = {Z₀, A, B}, F = {q₂}, pravidla (1) δ(q₀, a, Z₀) = (q₀, AZ₀), "
         "(2) δ(q₀, b, A) = (q₁, B), (3) δ(q₁, a, B) = (q₂, A).")
P2TXT = ("Q = {q₀, q₁, q₂}, Σ = {a, b}, Γ = {Z₀, A, B}, F = ∅, pravidla (1) δ(q₀, a, Z₀) = (q₀, A), "
         "(2) δ(q₀, b, A) = (q₁, B), (3) δ(q₁, a, B) = (q₂, e).")
reveal(
    "⏱ 1:15 · Příklad z přednášky 1 (koncový stav). Vyučující píše hodnoty δ bez závorek: δ(q₀, a, Z₀) = (q₀, AZ₀) "
    "znamená {(q₀, AZ₀)}, nenapsané hodnoty jsou ∅.\n"
    "Postup krokování: v každém kroku stav + první symbol zbytku + vrchol → najdi pravidlo → nová situace. "
    "Na papír si udělej tabulku krok | situace | pravidlo. Až pak odkryj.",
    "Zásobníkový automat z přednášky: " + P1TXT + " Odkrokuj slovo aba a rozhodni, jestli je přijato koncovým stavem.",
    " ⊢ ".join(fmtsit(s) for s in T1) + "\n"
    "krok 1: pravidlo 1, přečte a, nad Z₀ přidá A (push)\n"
    "krok 2: pravidlo 2, přečte b, A vymění za B\n"
    "krok 3: pravidlo 3, přečte a, B vymění za A\n"
    "Celé slovo přečteno a q₂ ∈ F, tedy aba ∈ L(M). V zásobníku zůstalo AZ₀, na tom u koncového stavu nezáleží. "
    "Ověřeno simulací: L(M) = {aba}. " + Z19)

inp(
    "U koncového stavu na zásobníku nezáleží. Ale co prázdným zásobníkem? Podívej se, jestli nějaké pravidlo "
    "vůbec něco ze zásobníku odebírá.",
    "Zásobníkový automat z přednášky: " + P1TXT + " Přijme tento automat slovo aba prázdným zásobníkem?",
    "ne", YN,
    "Výpočet skončí v (q₂, e, AZ₀), zásobník není prázdný a další krok nevede. Žádné pravidlo neodebírá, "
    "N(M) = ∅ (ověřeno simulací do délky 8). " + Z19)

reveal(
    "Příklad z přednášky 2 (prázdný zásobník). Rozdíly proti příkladu 1: pravidlo 1 Z₀ NAHRADÍ symbolem A "
    "(nepřidává), pravidlo 3 B ODEBERE (η = e), F = ∅.\n"
    "Odkrokuj na papír, pak odkryj.",
    "Zásobníkový automat z přednášky: " + P2TXT + " Odkrokuj slovo aba a rozhodni, jestli je přijato prázdným zásobníkem.",
    " ⊢ ".join(fmtsit(s) for s in T2) + "\n"
    "krok 1: pravidlo 1, přečte a, Z₀ → A\n"
    "krok 2: pravidlo 2, přečte b, A → B\n"
    "krok 3: pravidlo 3, přečte a, B → e (pop), zásobník prázdný\n"
    "Celé slovo přečteno a zásobník prázdný, tedy aba ∈ N(M); stav q₂ stačí libovolný (q₂ ∈ Q). "
    "Ověřeno simulací: N(M) = {aba}, L(M) = ∅. " + Z19)

choice(
    "Srovnání obou příkladů: stejné Q, Σ, Γ i slovo, liší se pravidla 1 a 3 a F.",
    "Čím se liší pravidlo 1 v příkladu 1 a v příkladu 2 (δ(q₀, a, Z₀) = (q₀, AZ₀) vs. (q₀, A))?",
    "V příkladu 1 se A přidá nad Z₀, v příkladu 2 Z₀ nahradí, takže dno zmizí.",
    ["Nijak, AZ₀ a A znamenají totéž.", "V příkladu 2 se A přidá pod Z₀.",
     "V příkladu 1 je to e-krok, v příkladu 2 ne."],
    "Vrchol se vždy nahrazuje slovem η; AZ₀ = push A, A = výměna. Proto v příkladu 2 může zásobník na konci zůstat "
    "prázdný. " + Z19)

# — 1:30 0ⁿ1ⁿ —
PN = [("q1", "0", "Z", "q1", "AZ"), ("q1", "0", "A", "q1", "AA"), ("q1", "1", "A", "q2", ""),
      ("q2", "1", "A", "q2", ""), ("q2", "", "Z", "q2", "")]
DN = as_delta(PN)
check({w for w in words("01", 10) if acc_empty(DN, "q1", "Z", w)} == {"0" * n + "1" * n for n in range(1, 6)})
check(deterministic(DN, "01"))
PNTXT = ("M = ({q₁, q₂}, {0, 1}, {Z, A}, δ, q₁, Z, ∅), pravidla (1) δ(q₁, 0, Z) = (q₁, AZ), (2) δ(q₁, 0, A) = (q₁, AA), "
         "(3) δ(q₁, 1, A) = (q₂, e), (4) δ(q₂, 1, A) = (q₂, e), (5) δ(q₂, e, Z) = (q₂, e).")
TN = pda_trace(DN, PN, "q1", "Z", "000111", [1, 2, 2, 3, 4, 4, 5])
check(TN[-1] == ("q2", "", ""))
inp(
    "⏱ 1:30 · Stejný jazyk jako v úloze 1, teď automatem: ZA pro {0ⁿ1ⁿ; n ≥ 1} prázdným zásobníkem.\n"
    "Nápad: za každou 0 dej do zásobníku A, za každou 1 jedno A odeber; když zbude jen dno Z, e-krokem ho odeber.\n"
    "Pravidla: 1 první 0 (push A nad Z), 2 další 0 (push A), 3 první 1 (pop A, přechod do q₂), "
    "4 další 1 (pop A), 5 e-krok, odebere dno Z.",
    "Zásobníkový automat " + PNTXT + " Napiš čísla pravidel výpočtu pro slovo 000111.",
    "1223445", RULES_HINT,
    " ⊢ ".join(sit_txt(s) for s in TN) + ". Celé přečteno, zásobník prázdný: 000111 ∈ N(M). "
    "Chytil, Pozn. 4.4.9 bod 2, s. 171; Barilla, kap. 8, úkol 1. " + Z19)

inp(
    "Počet kroků: každý přečtený symbol je jeden krok, plus e-kroky.",
    "Zásobníkový automat " + PNTXT + " Kolik kroků ⊢ má přijímající výpočet pro 000111?",
    "7", "číslo",
    "6 symbolů = 6 kroků se čtením, plus 1 e-krok (pravidlo 5) na odebrání Z. " + Z19)
check(len(TN) - 1 == 7)

inp(
    "Nepřijetí: výpočet se zasekne, když pro (stav, symbol, vrchol) není pravidlo, nebo dojde vstup a zásobník "
    "není prázdný.",
    "Zásobníkový automat " + PNTXT + " Přijme slovo 001?",
    "ne", YN,
    "(q₁, 001, Z) ⊢ (q₁, 01, AZ) ⊢ (q₁, 1, AAZ) ⊢ (q₂, e, AZ). Vstup došel, nahoře A, pravidlo 5 jde jen se Z nahoře. "
    "Zásobník není prázdný, nepřijato. Ověřeno simulací. " + Z19)
check(not acc_empty(DN, "q1", "Z", "001"))
check(not acc_empty(DN, "q1", "Z", "0101") and not acc_empty(DN, "q1", "Z", ""))

choice(
    "Proč je v automatu pravidlo 5 (e-krok)? Po poslední 1 zbude v zásobníku dno Z a vstup je přečtený. "
    "Bez kroku, který Z odebere, by zásobník nikdy nebyl prázdný.",
    "K čemu slouží pravidlo δ(q₂, e, Z) = (q₂, e) v automatu pro 0ⁿ1ⁿ?",
    "Po přečtení všech jedniček odebere dno Z, aby byl zásobník prázdný a slovo přijato.",
    ["Přečte prázdné slovo na začátku vstupu.", "Přidá Z zpět na zásobník.",
     "Umožní přijmout prázdné slovo e."],
    "Jen ve stavu q₂, takže prázdné slovo přijato není: (q₁, e, Z) žádný krok nemá. " + Z19)
check(not acc_empty(DN, "q1", "Z", ""))

reveal(
    "Na papír (Barilla kap. 8, úkol 1, typ úlohy ke zkoušce): sestroj ZA pro {0ⁿ1ⁿ; n ≥ 1} prázdným zásobníkem "
    "a rozpoznej 000111. Zkus pravidla napsat z hlavy, pak tabulku krok | situace | co se stalo.",
    "Sestrojte ZA, který rozpoznává L = {0ⁿ1ⁿ; n ≥ 1} pomocí prázdného zásobníku, a rozpoznejte slovo 000111.",
    "M = ({q₁, q₂}, {0, 1}, {Z, A}, δ, q₁, Z, ∅):\n"
    "(1) δ(q₁, 0, Z) = {(q₁, AZ)}, (2) δ(q₁, 0, A) = {(q₁, AA)}, (3) δ(q₁, 1, A) = {(q₂, e)}, "
    "(4) δ(q₂, 1, A) = {(q₂, e)}, (5) δ(q₂, e, Z) = {(q₂, e)}\n"
    + "\n".join(f"krok {i}: {sit_txt(s)}" for i, s in enumerate(TN)) +
    "\nCelé slovo přečteno, zásobník prázdný: 000111 ∈ N(M). Automat je deterministický. " + Z19)

# — 1:40 determinismus a palindromy —
choice(
    "⏱ 1:40 · Deterministický ZA (Chytil, Def. 4.4.7):\n"
    "1. Jestliže δ(q, e, Z) ≠ ∅, potom δ(q, a, Z) = ∅ pro všechna a ∈ Σ (volba „číst, nebo nečíst“ je zakázaná).\n"
    "2. Každé δ(q, a, Z) má nejvýš jeden prvek.\n"
    "Pak má automat v každé situaci nejvýš jeden možný krok. Na zkoušce může chtít oba druhy.",
    "Je automat pro 0ⁿ1ⁿ (pravidla 1–5 výše) deterministický?",
    "Ano: každé δ má nejvýš jeden prvek a pro (q₂, Z) s e-krokem neexistuje krok se čtením.",
    ["Ne, protože má e-krok.", "Ne, protože má dva stavy.", "Ano, protože nemá koncové stavy."],
    "e-krok sám o sobě nevadí, vadí jen e-krok a čtení pro tutéž dvojici (stav, vrchol). Ověřeno podle obou podmínek. " + Z19)

PP = [("p", "0", "A", "p", "BA"), ("p", "1", "A", "p", "CA"), ("p", "0", "B", "p", "BB"), ("p", "0", "B", "q", ""),
      ("p", "0", "C", "p", "BC"), ("p", "1", "B", "p", "CB"), ("p", "1", "C", "p", "CC"), ("p", "1", "C", "q", ""),
      ("q", "0", "B", "q", ""), ("q", "1", "C", "q", ""), ("p", "", "A", "q", ""), ("q", "", "A", "q", "")]
DP = as_delta(PP)
check({w for w in words("01", 8) if acc_empty(DP, "p", "A", w)} == {w for w in words("01", 8) if len(w) % 2 == 0 and w == w[::-1]})
check(not deterministic(DP, "01"))
check(acc_empty(DP, "p", "A", "01011010"))
PPTXT = ("M = ({p, q}, {0, 1}, {A, B, C}, δ, p, A, ∅): (1) δ(p, 0, A) = {(p, BA)}, (2) δ(p, 1, A) = {(p, CA)}, "
         "(3) δ(p, 0, B) = {(p, BB), (q, e)}, (4) δ(p, 0, C) = {(p, BC)}, (5) δ(p, 1, B) = {(p, CB)}, "
         "(6) δ(p, 1, C) = {(p, CC), (q, e)}, (7) δ(q, 0, B) = {(q, e)}, (8) δ(q, 1, C) = {(q, e)}, "
         "(9) δ(p, e, A) = {(q, e)}, (10) δ(q, e, A) = {(q, e)}.")
choice(
    "Barilla kap. 8, úkol 2: ZA pro {wwᴿ; w ∈ {0, 1}*} (palindromy sudé délky) prázdným zásobníkem.\n"
    "Ve stavu p ukládá první polovinu (0 jako B, 1 jako C). Když „usoudí“, že je v polovině, přejde do q a už jen "
    "odebírá a porovnává. Dno A odebere e-krok.",
    "Automat pro wwᴿ má pro (p, 0, B) i (p, 1, C) dvě instrukce: (p, BB) a (q, e), resp. (p, CC) a (q, e). Proč není deterministický?",
    "Pravidla 3 a 6 mají dvě možnosti: ukládat dál, nebo přejít do q a začít odebírat.",
    ["Protože má e-kroky 9 a 10.", "Protože má dva stavy.", "Protože zásobníková abeceda má tři symboly."],
    "Porušená podmínka 2 (víc prvků v δ). Automat „hádá“ střed slova; stačí, že jeden výpočet vede k přijetí. "
    "Chytil, Př. 4.4.5, s. 167–168. Ověřeno simulací do délky 8. " + Z19)

reveal(
    "Na papír: odkrokuj 01011010 = 0101 · 1010. Prvních 4 symbolů ukládej, u 5. symbolu zvol přechod do q, "
    "pak odebírej. Až pak odkryj.",
    "Automat " + PPTXT + " Rozpoznejte slovo 01011010 (najdi přijímající výpočet).",
    "krok 0: (p, 01011010, A)\n"
    "krok 1: (p, 1011010, BA), pravidlo 1\n"
    "krok 2: (p, 011010, CBA), pravidlo 5\n"
    "krok 3: (p, 11010, BCBA), pravidlo 4\n"
    "krok 4: (p, 1010, CBCBA), pravidlo 5\n"
    "krok 5: (q, 010, BCBA), pravidlo 6, druhá možnost (střed slova)\n"
    "krok 6: (q, 10, CBA), pravidlo 7\n"
    "krok 7: (q, 0, BA), pravidlo 8\n"
    "krok 8: (q, e, A), pravidlo 7\n"
    "krok 9: (q, e, e), pravidlo 10 (e-krok)\n"
    "Přečteno a zásobník prázdný: 01011010 ∈ N(M). Chytil, Př. 4.4.5, s. 167; Barilla, kap. 8, úkol 2. " + Z19)
PSEQ = [(1, 0), (5, 0), (4, 0), (5, 0), (6, 1), (7, 0), (8, 0), (7, 0), (10, 0)]
PNUM = {1: ("p", "0", "A"), 2: ("p", "1", "A"), 3: ("p", "0", "B"), 4: ("p", "0", "C"), 5: ("p", "1", "B"),
        6: ("p", "1", "C"), 7: ("q", "0", "B"), 8: ("q", "1", "C"), 9: ("p", "", "A"), 10: ("q", "", "A")}
s = ("p", "01011010", "A")
for r, k in PSEQ:
    q_, a_, X_ = PNUM[r]
    check(s[0] == q_ and s[2][:1] == X_ and (a_ == "" or s[1][:1] == a_))
    p_, eta = DP[(q_, a_, X_)][k]
    s = (p_, s[1][1:] if a_ else s[1], eta + s[2][1:])
check(s == ("q", "", ""))

choice(
    "Závěr přednášky 19. 11. (Chytil, Lemma 4.4.8):\n"
    "1. Ke každému deterministickému ZA M₁ jde sestrojit deterministický ZA M₂ s N(M₁) = L(M₂).\n"
    "2. Existuje regulární jazyk, který žádný deterministický ZA prázdným zásobníkem nerozpozná, např. {a, aa}: "
    "po přijetí a by musel mít prázdný zásobník, a pak už aa nedočte.\n"
    "U deterministických ZA je tedy koncový stav silnější; u nedeterministických jsou oba způsoby rovnocenné.",
    "Proč deterministický ZA nerozpozná jazyk {a, aa} prázdným zásobníkem?",
    "Po přečtení a musí mít prázdný zásobník, a z té situace už žádný krok nevede, takže aa nedočte.",
    ["Protože jazyk {a, aa} není regulární.", "Protože deterministický ZA nemá e-kroky.",
     "Protože {a, aa} je nekonečný jazyk."],
    "Prázdný zásobník = konec výpočtu (Pozn. 4.4.3) a deterministický automat má pro a i aa stejný začátek výpočtu. "
    "Chytil, Lemma 4.4.8 a důkaz, s. 170–171. " + Z19)

choice(
    "Propojení obou částí: jazyk {0ⁿ1ⁿ; n ≥ 1} generuje gramatika S → 0S1 | 01 (typ 2) a rozpoznává ZA s pravidly 1–5. "
    "Gramatika přidává páry 0…1 kolem středu, automat páry počítá v zásobníku (push za 0, pop za 1).",
    "Co platí o jazyce {0ⁿ1ⁿ; n ≥ 1}?",
    "Je bezkontextový, není regulární a rozpozná ho i deterministický ZA prázdným zásobníkem.",
    ["Je regulární, stačí na něj konečný automat.", "Je typu 0, ale ne typu 2.",
     "Rozpozná ho jen nedeterministický ZA."],
    "Chytil, Pozn. 4.4.9 bod 2, s. 171 (deterministický ZA prázdným zásobníkem) a 1.3.6 (není regulární). " + Z19)

reveal(
    "⏱ 1:55 · REKAPITULACE. Bez výpisků napiš na půl stránky: definici gramatiky a L(G), Chomského typy 0–3 s tvarem "
    "pravidel, sedmici ZA, situaci a krok ⊢, L(M) vs. N(M), podmínky determinismu a jak spolu souvisí typ 2 a ZA. "
    "Pak odkryj a porovnej.",
    "Shrň gramatiky a zásobníkové automaty z hlavy, pak porovnej.",
    "• G = (Π, Σ, S, P), pravidla s neterminálem vlevo; L(G) = {w ∈ Σ*; S ⇒* w}, jen terminální slova.\n"
    "• ⇒ = jedno pravidlo jednou, ⇒* = řetěz (i 0 kroků); u odvození podtrhávat a číslovat pravidla.\n"
    "• Typ 0 α → β; typ 1 αXβ → αγβ, γ ≠ e (výjimka S → e); typ 2 X → γ; typ 3 X → wY | w. 𝓛₃ ⊆ 𝓛₂ ⊆ 𝓛₁ ⊆ 𝓛₀.\n"
    "• Typ 3 ↔ KA (Kleene), typ 2 ↔ ZA, typ 1 ↔ LOTS, typ 0 ↔ TS.\n"
    "• ZA M = (Q, Σ, Γ, δ, q₀, Z₀, F), δ(q, a nebo e, X) = množina (q', η), vrchol vlevo, X se nahradí η.\n"
    "• Situace (q, zbytek, zásobník), krok (q, aw, Yη) ⊢ (q', w, νη); prázdný zásobník = konec.\n"
    "• L(M): přečteno + koncový stav; N(M): přečteno + prázdný zásobník (F = ∅).\n"
    "• Deterministický: nejvýš 1 prvek v δ a e-krok vylučuje čtení pro stejné (q, Z).\n"
    "• {0ⁿ1ⁿ}: gramatika S → 0S1 | 01, ZA push za 0, pop za 1, e-krok odebere Z.")

# ── zápis ──
for i, q in enumerate(Q, 1):
    q["number"], q["id"] = i, f"8z-{i}"
    if q["type"] == "choice":
        check(len(q["options"]) == 4 and len(set(q["options"].values())) == 4, q["id"])
        bad = ("druhá možnost", "A i B", "žádná z uvedených")
        check(not any(b in q["explanation"] for b in bad[1:]), q["id"])
    check("_" not in q["text"] + q["theory"], f"podtržítko by fmt změnil na index: {q['id']}")

OUT.write_text(json.dumps({"title": "Rychlokurz: gramatiky a zásobníkové automaty", "lecture": 8, "date": "2026-11-19",
                           "questions": Q}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{OUT.name}: {len(Q)} otázek, {CHECKS} kontrol OK")
