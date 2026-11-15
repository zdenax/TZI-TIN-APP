#!/usr/bin/env python3
"""Vygeneruje banku 7. přednášky (12. 11. 2026) do banky/07-2026-11-12.json (id 7-N):
gramatiky (přepisovací systém, přímý přepis, odvození, minimální odvození, lemma, generativní a analytická
gramatika, L(G), Chomského typy 0–3 a automaty, Kleeneova věta, konstrukce gramatiky ke konečnému automatu).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z výpisků přednášky 12. 11. 2026 (vault TZI1: Prednasky/2026-11-12-gramatiky), včetně označených
doplňků „Doplněno z Claude“ ověřených proti Chytilovi (Automaty a gramatiky, kap. 2.3, 3.1–3.3, s. 94–132)
a Vaisovi (kap. 2.8, s. 56). Z knih jsou jen odkazy na číslo definice a stranu a krátké parafráze.
Nejistá místa rukopisu (pravidlo 5 jako C → b, číslo pravidla ve 4. kroku odvození 1100) se používají jen
v opraveném znění, které ověřuje výpočet. Odvození, jazyky a typy pravidel se počítají a ověřují zde
(prohledávání přepisů, simulace automatu), ne ručně v JSON.
Id 7-N jsou pevná (váže se na ně uložený postup): nové otázky jen na konec, pořadí skupin neměnit.
Zapisuje se JEN banky/07-2026-11-12.json.
Spuštění:  python3 build_bank_7.py
"""
import itertools
import json
import random
from collections import Counter, deque
from pathlib import Path

from build_bank_5 import run, s
from build_bank_6 import ED, EF, build

HERE = Path(__file__).parent
CHECKS = 0
P = "Přednáška 12. 11."
YN_HINT = "ano nebo ne (bez tečky)"
RULES_HINT = "čísla pravidel v pořadí použití, bez mezer, např. 312"


def check(cond, msg=""):
    global CHECKS
    assert cond, msg
    CHECKS += 1


# ── přepisy: slovo = n-tice symbolů, pravidlo = (levá, pravá) ──

def T(w):
    return tuple(w)


def steps(form, rules):
    """Všechny přímé přepisy u ⇒ z: (číslo pravidla od 1, pozice od 0, z)."""
    out = []
    for i, (x, y) in enumerate(rules, 1):
        for p in range(len(form) - len(x) + 1):
            if form[p:p + len(x)] == x:
                out.append((i, p, form[:p] + y + form[p + len(x):]))
    return out


def reach(start, rules, maxlen):
    """Všechna slova u, pro která start ⇒* u (relace ⇒* je reflexivní), délka omezená maxlen."""
    seen, todo = {start}, deque([start])
    while todo:
        f = todo.popleft()
        for _, _, z in steps(f, rules):
            if len(z) <= maxlen and z not in seen:
                seen.add(z)
                todo.append(z)
    return seen


def derivations(start, goal, rules, maxlen, maxsteps):
    """Všechna odvození start ⇒* goal jako seznamy (pravidlo, pozice, slovo), bez opakování slov (minimální)."""
    res = []

    def go(f, path, used):
        if f == goal:
            res.append(path)
            return
        if len(path) == maxsteps:
            return
        for i, p, z in steps(f, rules):
            if len(z) <= maxlen and z not in used:
                go(z, path + [(i, p, z)], used | {z})
    go(start, [], {start})
    return res


def apply_seq(start, rules, seq):
    """Použije pravidla v daném pořadí; vyžaduje, aby každé šlo použít právě na jednom místě."""
    f, forms = start, [start]
    for i in seq:
        opts = [z for j, _, z in steps(f, rules) if j == i]
        check(len(opts) == 1, f"pravidlo {i} na {f}: {opts}")
        f = opts[0]
        forms.append(f)
    return forms


# Příklad 3.1.3 (Chytil, s. 118–119): V = {0, 1}, P = {01 → 10, 10 → 01}
RS = [(T("01"), T("10")), (T("10"), T("01"))]

# Generativní gramatika z přednášky: Π = {S, B, C}, Σ = {a, b, c}
NT = set("SBC")
GR = [(T("S"), T("aBb")), (T("B"), T("aCc")), (T("C"), T("bBa")), (T("B"), T("a")), (T("C"), T("b"))]
GR_TXT = "Gramatika z přednášky: Π = {S, B, C}, Σ = {a, b, c}, pravidla (1) S → aBb, (2) B → aCc, (3) C → bBa, (4) B → a, (5) C → b."
AN = [(y, x) for x, y in GR]  # analytická: obrácené šipky
RS_TXT = "Přepisovací systém z přednášky: V = {0, 1}, pravidla (1) 01 → 10, (2) 10 → 01."

# Konečný automat z přednášky (Chytil, obr. 32, s. 130): F = {q₀}
KQ, KF = ["q0", "q1", "q2"], {"q0"}
KD = {("q0", "0"): "q0", ("q0", "1"): "q1", ("q1", "0"): "q0", ("q1", "1"): "q2",
      ("q2", "0"): "q0", ("q2", "1"): "q2"}
KA_TXT = ("Automat z přednášky: Q = {q₀, q₁, q₂}, Σ = {0, 1}, počáteční stav q₀, F = {q₀}, δ(q₀, 0) = q₀, "
          "δ(q₀, 1) = q₁, δ(q₁, 0) = q₀, δ(q₁, 1) = q₂, δ(q₂, 0) = q₀, δ(q₂, 1) = q₂.")


def dfa_grammar(D, Q, F):
    """Konstrukce z důkazu Věty 3.3.1: Π = Q, S = q₀, P = {q → aq′; δ(q, a) = q′} ∪ {q → e; q ∈ F}.
    Pořadí pravidel jako na přednášce: po stavech, nejdřív přechody (0, 1), pak q → e."""
    rules = []
    for q in Q:
        for a in "01":
            rules.append(((q,), (a, D[(q, a)])))
        if q in F:
            rules.append(((q,), ()))
    return rules


KG = dfa_grammar(KD, KQ, KF)
KG_TXT = ("Gramatika k automatu z přednášky: (1) q₀ → 0q₀, (2) q₀ → 1q₁, (3) q₀ → e, (4) q₁ → 0q₀, (5) q₁ → 1q₂, "
          "(6) q₂ → 0q₀, (7) q₂ → 1q₂.")


def rule_txt(x, y):
    f = lambda w: "".join(s(c) if c.startswith("q") else c for c in w) or "e"
    return f"{f(x)} → {f(y)}"


def gen_lang(rules, start, nts, maxlen):
    """Terminální slova odvoditelná ze start do délky maxlen (gramatiky zde mají nejvýš jedno e-pravidlo na konci)."""
    return {"".join(f) for f in reach(start, rules, maxlen + 1) if len(f) <= maxlen and not set(f) & nts}


# ── Chomského typ jednoho pravidla (Chytil, Def. 3.2.1) ──

def rule_type(x, y, nts):
    """Nejvyšší i ∈ {0, 1, 2, 3}, jehož tvar pravidlo splňuje (výjimku S → e u typu 1 neřeší)."""
    isn = lambda c: c in nts
    if not any(map(isn, x)):
        return None  # vůbec není pravidlo gramatiky
    if len(x) == 1:
        body, last = (y[:-1], y[-1:]) if y and isn(y[-1]) else (y, ())
        return 3 if not any(map(isn, body)) else 2
    for k, X in enumerate(x):  # αXβ → αγβ, |γ| ≥ 1
        if isn(X):
            a, b = x[:k], x[k + 1:]
            if len(y) >= len(a) + len(b) + 1 and y[:len(a)] == a and y[len(y) - len(b):] == b:
                return 1
    return 0


def verify():
    # Příklad 3.1.3: 00110 ⇒* 00011
    d = derivations(T("00110"), T("00011"), RS, 5, 2)
    check(len(d) == 1 and [i for i, _, _ in d[0]] == [2, 2] and [p for _, p, _ in d[0]] == [3, 2])
    check(not derivations(T("00110"), T("00011"), RS, 5, 1))
    check([z for _, _, z in d[0]] == [T("00101"), T("00011")])
    check(sorted("".join(z) for _, _, z in steps(T("00110"), RS)) == ["00101", "01010"])
    # systém přepíše slovo právě na slova se stejným počtem 0 a 1
    for n in range(1, 8):
        for w in itertools.product("01", repeat=n):
            r = reach(w, RS, n)
            check(r == {v for v in itertools.product("01", repeat=n) if Counter(v) == Counter(w)})
    # 00110 ⇒* 01100 přes 01010 (Chytil, s. 119)
    check(any([z for _, _, z in p] == [T("01010"), T("01100")] for p in derivations(T("00110"), T("01100"), RS, 5, 2)))

    # gramatika: S ⇒* aabaacb pravidly 1, 2, 3, 4, jediné odvození
    d = derivations(T("S"), T("aabaacb"), GR, 7, 10)
    check(len(d) == 1 and [i for i, _, _ in d[0]] == [1, 2, 3, 4])
    check(apply_seq(T("S"), GR, [1, 2, 3, 4])[1:] == [T("aBb"), T("aaCcb"), T("aabBacb"), T("aabaacb")])
    L = gen_lang(GR, T("S"), NT, 11)
    check(min(L, key=len) == "aab" and [w for w in L if len(w) == 3] == ["aab"])
    check(derivations(T("S"), T("aab"), GR, 3, 5) and len(derivations(T("S"), T("aab"), GR, 3, 5)[0]) == 2)
    check("aabcb" in L and sorted(w for w in L if len(w) == 5) == ["aabcb"])
    # analytická: aabaacb ⇒* S pravidly 4, 3, 2, 1, jediné
    d = derivations(T("aabaacb"), T("S"), AN, 7, 10)
    check(len(d) == 1 and [i for i, _, _ in d[0]] == [4, 3, 2, 1] and d[0][0][1] == 3)
    check(all(set(y) & NT for _, y in AN) and all(set(x) & NT for x, _ in GR))
    check(not all(set(y) & NT for _, y in GR))  # generativní pravidla B → a, C → b nemají neterminál vpravo
    # typ gramatiky z příkladu: 2 (a 1), ne 3
    check([rule_type(x, y, NT) for x, y in GR] == [2, 2, 2, 3, 3])
    check(min(rule_type(x, y, NT) for x, y in GR) == 2)

    # Věta 3.3.1: gramatika k automatu
    KN = set(KQ)
    check(len(KG) == 7 and [rule_txt(x, y) for x, y in KG] ==
          ["q₀ → 0q₀", "q₀ → 1q₁", "q₀ → e", "q₁ → 0q₀", "q₁ → 1q₂", "q₂ → 0q₀", "q₂ → 1q₂"])
    check(all(rule_type(x, y, KN) == 3 for x, y in KG))
    check(run(KD, "q0", "1100") == ["q0", "q1", "q2", "q0", "q0"])
    d = derivations(("q0",), T("1100"), KG, 5, 10)
    check(len(d) == 1 and [i for i, _, _ in d[0]] == [2, 5, 6, 1, 3])
    d = derivations(("q0",), T("10"), KG, 3, 10)
    check(len(d) == 1 and [i for i, _, _ in d[0]] == [2, 4, 3])
    LG = gen_lang(KG, ("q0",), KN, 10)
    for n in range(11):
        for w in map("".join, itertools.product("01", repeat=n)):
            acc = run(KD, "q0", w)[-1] in KF
            check((w in LG) == acc == (w == "" or w.endswith("0")), w)
            if acc and n <= 6:  # odvození slova délky n má n + 1 kroků
                check(all(len(p) == n + 1 for p in derivations(("q0",), T(w), KG, n + 1, n + 2)))
    check(sum(w.endswith("0") for w in map("".join, itertools.product("01", repeat=3))) == 4)
    check("" in LG and ("q0",) in [x for x, y in KG if y == ()])

    # dveře (5. 11.): F = {q₁}, gramatika podle téže konstrukce
    DG = dfa_grammar(ED, ["q0", "q1"], EF)
    check([rule_txt(x, y) for x, y in DG] == ["q₀ → 0q₀", "q₀ → 1q₁", "q₁ → 0q₀", "q₁ → 1q₁", "q₁ → e"])
    d = derivations(("q0",), T("101"), DG, 4, 10)
    check(len(d) == 1 and [rule_txt((), z)[4:] for _, _, z in d[0]] == ["1q₁", "10q₀", "101q₁", "101"])
    check("" not in gen_lang(DG, ("q0",), {"q0", "q1"}, 4))

    # typy jednotlivých pravidel pro otázky (X, Y, Z ∈ Π; a, b ∈ Σ)
    N3 = set("XYZ")
    for r, t in RULE_TYPES:
        x, y = r.split(" → ")
        check(rule_type(T(x), T("" if y == "e" else y), N3) == t, r)


RULE_TYPES = [("X → aY", 3), ("X → aYb", 2), ("aXb → aYZb", 1), ("XY → YX", 0), ("X → e", 3), ("XY → e", 0)]


# ── výběrové otázky: (text, [správná, špatná, špatná, špatná], [0], vysvětlení) ──

def choice():
    c = []
    add = lambda t, o, e: c.append((t, o, [0], e))

    add("Přepisovací systém je dvojice R = (V, P). Co je V a co P?",
        ["V je konečná abeceda, P konečná množina přepisovacích pravidel.",
         "V je množina stavů, P množina koncových stavů automatu.",
         "V je nekonečná množina slov, P libovolná relace na ní.",
         "V je množina neterminálů gramatiky, P je její počáteční symbol."],
        "Každé pravidlo je dvojice (u, v), u, v ∈ V*, píše se u → v. "
        f"Chytil, Def. 3.1.1, s. 118 (doplněno z Claude, ověřeno). {P}")
    add("Co znamená přímý přepis u ⇒ z?",
        ["Jedno pravidlo x → y použité jednou: u = vxw, z = vyw.",
         "Libovolný počet použití libovolných pravidel, klidně i žádné.",
         "Každé pravidlo z P se použije právě jednou.",
         "Všechny výskyty x ve slově u se nahradí naráz za y."],
        "u ⇒ z ⇔ ∃ v, w, x, y ∈ V*: u = vxw, z = vyw, x → y ∈ P. Jedno pravidlo, jedenkrát. "
        f"Chytil, Def. 3.1.2 bod 1, s. 118. {P}")
    add("Co znamená zápis u ⇒* z (přepis, odvození)?",
        ["z vznikne z u konečnou posloupností přímých přepisů.",
         "z vznikne z u právě jedním použitím jednoho pravidla.",
         "u vznikne ze z obrácením všech pravidel systému.",
         "u a z mají stejnou délku a stejná písmena."],
        "u = u₁ ⇒ u₂ ⇒ … ⇒ uₙ = z; posloupnost je odvození (derivace) délky n. "
        f"Šipka s hvězdičkou se čte „se přepíše“. Chytil, Def. 3.1.2 bod 2, s. 118. {P}")
    add("Kdy je odvození u₁ ⇒ u₂ ⇒ … ⇒ uₙ minimální?",
        ["Když se v něm žádné slovo neopakuje: uᵢ ≠ uⱼ pro i ≠ j.",
         "Když má nejmenší možný počet kroků ze všech odvození.",
         "Když se v něm každé pravidlo z P použije nejvýš jednou.",
         "Když je výsledné slovo nejkratší, jaké jde odvodit."],
        f"Laicky: dvě slova se tam nebudou opakovat. Chytil, s. 118. {P}")
    add("Co říká lemma o minimálním odvození?",
        ["Když u ⇒* z, existuje i minimální odvození z ze slova u.",
         "Každé odvození v přepisovacím systému je minimální.",
         "Minimální odvození má vždy právě jeden krok.",
         "Když u ⇒* z, platí i z ⇒* u v každém přepisovacím systému."],
        "Důsledek: o odvození lze bez újmy na obecnosti předpokládat, že je minimální. "
        f"Chytil, Lemma 3.1.4, s. 119. {P}")
    add("Jak se dokáže lemma o minimálním odvození?",
        ["Úsek mezi dvěma stejnými slovy uᵢ = uⱼ se vypustí.",
         "Indukcí podle počtu pravidel v množině P.",
         "Sporem: předpokládá se, že odvození neexistuje.",
         "Sestrojí se k systému konečný automat se stejným jazykem."],
        "Není-li odvození minimální, obsahuje úsek uᵢ ⇒ … ⇒ uⱼ s uᵢ = uⱼ; ten je zbytečný a nahradí se slovem uᵢ. "
        f"Po konečně mnoha krocích zbude minimální odvození. Chytil, s. 119. {P}")
    add("Jaké vlastnosti má relace ⇒* (přepis)?",
        ["Je reflexivní a tranzitivní.",
         "Je symetrická, ale ne reflexivní.",
         "Je antireflexivní a tranzitivní.",
         "Je to vždy ekvivalence."],
        "⇒* je reflexivní a tranzitivní uzávěr relace ⇒ (u ⇒* u nulou kroků). Doplněno z Claude, "
        f"Chytil, Def. 3.1.2, s. 118. Symetrická obecně není, symetrický je jen systém z příkladu. {P}")
    add("Generativní gramatika G = (Π, Σ, S, P). Co je Π?",
        ["Množina neterminálů (proměnných).", "Množina terminálů (písmen slov).",
         "Množina přepisovacích pravidel gramatiky.", "Množina koncových stavů automatu."],
        "Π a Σ jsou disjunktní konečné abecedy (Π ∩ Σ = ∅), S ∈ Π je počáteční symbol, P pravidla. "
        f"Neterminály se píšou velkými písmeny. Chytil, Def. 3.1.5, s. 119. {P}")
    add("Generativní gramatika G = (Π, Σ, S, P). Co je Σ?",
        ["Množina terminálů (písmen slov jazyka).", "Množina neterminálů (proměnných).",
         "Počáteční symbol gramatiky.", "Množina všech slov nad abecedou Π."],
        "Terminály se píšou malými písmeny a číslicemi (a, b, 0, 1); ze slov jen z terminálů se skládá L(G). "
        f"Chytil, Def. 3.1.5, s. 119. {P}")
    add("Generativní gramatika G = (Π, Σ, S, P). Co je S?",
        ["Počáteční symbol, S ∈ Π.", "Množina terminálů.", "Počáteční symbol, S ∈ Σ.", "Množina pravidel."],
        f"Každé odvození začíná slovem S; S je jeden z neterminálů. Chytil, Def. 3.1.5, s. 119. {P}")
    add("Jakou podmínku musí splňovat pravidlo α → β generativní gramatiky?",
        ["Levá strana α obsahuje aspoň jeden neterminál.",
         "Pravá strana β obsahuje aspoň jeden neterminál.",
         "Levá strana α je právě jeden neterminál.",
         "Pravá strana β je neprázdné slovo terminálů."],
        "α = uXv, X ∈ Π, u, v, β ∈ (Π ∪ Σ)*. Neterminál vpravo požaduje analytická gramatika. "
        f"Chytil, Def. 3.1.5, s. 119. {P}")
    add("Jak je definován jazyk L(G) generovaný gramatikou G?",
        ["L(G) = {w ∈ Σ*; S ⇒* w}", "L(G) = {w ∈ (Π ∪ Σ)*; S ⇒* w}",
         "L(G) = {w ∈ Σ*; w ⇒* S}", "L(G) = {w ∈ Π*; S ⇒ w}"],
        "Všechna slova jen z terminálů, která jde odvodit z počátečního symbolu. Varianta w ⇒* S je jazyk "
        f"analytické gramatiky. Chytil, s. 119. {P}")
    add(f"{GR_TXT} Platí S ⇒* aBb. Patří aBb do L(G)?",
        ["Ne, obsahuje neterminál B.", "Ano, odvodí se z S jedním krokem.",
         "Ano, každé odvozené slovo patří do L(G).", "Ne, protože končí terminálem b."],
        "Do L(G) patří jen slova z Σ*. Slovo s neterminálem se odvozuje dál, dokud nezůstanou jen terminály. "
        f"{P}")
    add("Jakou podmínku musí splňovat pravidlo α → β analytické gramatiky?",
        ["Pravá strana β obsahuje aspoň jeden neterminál.",
         "Levá strana α obsahuje aspoň jeden neterminál.",
         "Pravá strana β je vždy jediný terminál.",
         "Obě strany pravidla mají vždy stejnou délku."],
        "β = uXv, X ∈ Π. U generativní gramatiky musí neterminál obsahovat levá strana. "
        f"Chytil, Def. 3.1.8, s. 123. {P}")
    add("Jak je definován jazyk L(G) analytické gramatiky?",
        ["L(G) = {w ∈ Σ*; w ⇒* S}", "L(G) = {w ∈ Σ*; S ⇒* w}",
         "L(G) = {w ∈ Π*; w ⇒* S}", "L(G) = {S}"],
        "Slova z terminálů, která jde přepsat (zredukovat) na počáteční symbol. "
        f"Chytil, Def. 3.1.8, s. 123. {P}")
    add("V čem se liší generativní a analytická gramatika?",
        ["Generativní slovo z S vytváří, analytická ho redukuje na S.",
         "Generativní má jen terminály, analytická jen neterminály.",
         "Analytická nemá počáteční symbol, generativní ho mít musí.",
         "Generativní je vždy regulární, analytická bezkontextová."],
        "Analytická gramatika postupuje pozpátku jako rozbor věty nebo programu. Obrácením šipek ve všech pravidlech "
        f"se z jedné stane druhá se stejným jazykem. Chytil, s. 123–124. {P}")
    add("Jak z generativní gramatiky G dostat analytickou gramatiku G′ s L(G′) = L(G)?",
        ["Obrátit šipky ve všech pravidlech.",
         "Prohodit terminály a neterminály.",
         "Přidat pravidlo S → e.",
         "Vypustit pravidla s terminálem vpravo."],
        f"Pojmy jsou rovnocenné, proto se dál pracuje jen s generativními gramatikami. Chytil, s. 124. {P}")
    # Chomského typy
    add("Jak se jmenuje gramatika typu 0 v Chomského rozdělení?",
        ["Obecná", "Kontextová", "Bezkontextová", "Regulární"],
        "Typ 0 obecná, 1 kontextová, 2 bezkontextová, 3 regulární. Jediná podmínka typu 0: levá strana obsahuje "
        f"neterminál. Chytil, Def. 3.2.1, s. 124. {P}")
    add("Jak se jmenuje gramatika typu 1 v Chomského rozdělení?",
        ["Kontextová", "Obecná", "Bezkontextová", "Regulární"],
        f"Pravidla αXβ → αγβ, X se přepíše jen v kontextu α, β. Chytil, Def. 3.2.1 bod 2, Pozn. 3.2.3, s. 124–125. {P}")
    add("Jak se jmenuje gramatika typu 2 v Chomského rozdělení?",
        ["Bezkontextová", "Kontextová", "Obecná", "Regulární (pravá lineární)"],
        f"Pravidla X → γ, vlevo jediný neterminál bez ohledu na okolí. Chytil, Def. 3.2.1 bod 3, s. 124. {P}")
    add("Jak se jmenuje gramatika typu 3 v Chomského rozdělení?",
        ["Regulární", "Bezkontextová", "Kontextová", "Obecná"],
        f"Pravidla X → wY nebo X → w, w ∈ Σ* (pravá lineární). Chytil, Def. 3.2.1 bod 4, s. 125. {P}")
    add("Jaký tvar mají pravidla kontextové gramatiky (typ 1)?",
        ["αXβ → αγβ, X ∈ Π, γ ∈ (Π ∪ Σ)⁺", "X → γ, X ∈ Π, γ ∈ (Π ∪ Σ)*",
         "X → wY nebo X → w, X, Y ∈ Π, w ∈ Σ*", "α → β, α obsahuje aspoň jeden neterminál"],
        "γ je neprázdné: neterminál se nesmí přepsat na prázdné slovo (jediná výjimka S → e). "
        f"Chytil, Def. 3.2.1 bod 2, Pozn. 3.2.4, s. 124–125. {P}")
    add("Jaký tvar mají pravidla bezkontextové gramatiky (typ 2)?",
        ["X → γ, X ∈ Π, γ ∈ (Π ∪ Σ)*", "αXβ → αγβ, X ∈ Π, γ ∈ (Π ∪ Σ)⁺",
         "X → wY nebo X → w, w ∈ Σ*", "α → β, β obsahuje neterminál"],
        f"Pravá strana smí být i prázdná (X → e). Chytil, Def. 3.2.1 bod 3, s. 124. {P}")
    add("Jaký tvar mají pravidla regulární gramatiky (typ 3)?",
        ["X → wY nebo X → w, X, Y ∈ Π, w ∈ Σ*", "X → γ, X ∈ Π, γ ∈ (Π ∪ Σ)*",
         "αXβ → αγβ, X ∈ Π, γ ∈ (Π ∪ Σ)⁺", "X → YZ nebo X → a, Y, Z ∈ Π, a ∈ Σ"],
        f"Vpravo je nejvýš jeden neterminál, a to úplně vpravo. Chytil, Def. 3.2.1 bod 4, s. 125. {P}")
    add("Kontextová gramatika obsahuje pravidlo S → e. Co z toho plyne?",
        ["S se nesmí vyskytovat na pravé straně žádného pravidla.",
         "Gramatika už nesmí mít žádné další pravidlo s S vlevo.",
         "Každý neterminál smí mít pravidlo X → e.",
         "Jazyk gramatiky obsahuje jen prázdné slovo e."],
        "S → e je jediná výjimka z neprázdnosti γ; je v definici jen kvůli hierarchii L₂ ⊆ L₁. "
        f"Chytil, Def. 3.2.1, Pozn. 3.2.4, s. 124–125. {P}")
    add("Jak zní Chomského hierarchie tříd jazyků?",
        ["𝓛₃ ⊆ 𝓛₂ ⊆ 𝓛₁ ⊆ 𝓛₀", "𝓛₀ ⊆ 𝓛₁ ⊆ 𝓛₂ ⊆ 𝓛₃", "𝓛₃ ⊆ 𝓛₁ ⊆ 𝓛₂ ⊆ 𝓛₀", "𝓛₁ ⊆ 𝓛₀ ⊆ 𝓛₂ ⊆ 𝓛₃"],
        "Čím vyšší typ, tím přísnější tvar pravidel a menší třída jazyků; regulární jazyky jsou nejmenší třída. "
        f"Chytil, Tvrzení 3.2.6, s. 125. {P}")
    add("Proč 𝓛₂ ⊆ 𝓛₁ neplyne přímo z definice gramatik?",
        ["Bezkontextová smí mít víc pravidel X → e, kontextová jen S → e.",
         "Kontextová gramatika nesmí mít na pravé straně terminály.",
         "Bezkontextová gramatika nemá žádný počáteční symbol S.",
         "Kontextová gramatika má vlevo jen jeden neterminál."],
        "Plyne až z Věty 3.2.8: bezkontextovou gramatiku jde upravit na nevypouštějící se stejným jazykem. "
        f"𝓛₁ ⊆ 𝓛₀ a 𝓛₃ ⊆ 𝓛₂ plynou přímo z definice. Chytil, s. 125–126. {P}")
    autos = ["Konečný automat", "Nedeterministický zásobníkový automat", "Lineárně omezený Turingův stroj",
             "Turingův stroj"]
    zdroj = ["Chytil, Věty 3.3.1 a 3.3.5, s. 130–132", "Chytil, čl. 4.5, s. 172",
             "Vais, kap. 2.8, s. 56 (z rukopisu nevyplývá, jestli to na přednášce zaznělo)",
             "Chytil, Důsledek 6.1.10, s. 267"]
    for t, nazev in ((3, "regulární"), (2, "bezkontextové"), (1, "kontextové"), (0, "typu 0")):
        k = 3 - t
        add(f"Co rozpoznává jazyky typu {t} ({nazev}) v Chomského hierarchii?",
            [autos[k]] + autos[:k] + autos[k + 1:],
            f"Typ 3 konečný automat, 2 nedeterministický zásobníkový automat, 1 lineárně omezený Turingův stroj, "
            f"0 Turingův stroj. Zdroj: {zdroj[k]}. {P}")
    add("Co říká Kleeneova věta?",
        ["Jazyk je regulární, právě když je rozpoznatelný konečným automatem.",
         "Každý bezkontextový jazyk je rozpoznatelný konečným automatem.",
         "Ke každé gramatice typu 0 existuje konečný automat se stejným jazykem.",
         "Jazyk je regulární, právě když je generován kontextovou gramatikou."],
        "Spojuje Věty 2.3.4 (regulární ⇒ rozpoznatelný KA) a 2.3.6 (rozpoznatelný KA ⇒ regulární). "
        f"Chytil, Věta 2.3.7, s. 96; Habiballa, Věta 3, s. 67–68. {P}")
    add("Platí: jazyk je typu 3, právě když je rozpoznatelný konečným automatem?",
        ["Ano, podle Vět 3.3.1 a 3.3.5.",
         "Ne, jen každý jazyk typu 3 je rozpoznatelný KA.",
         "Ne, jen každý jazyk rozpoznatelný KA je typu 3.",
         "Ano, ale jen pro abecedu {0, 1}."],
        "Věta 3.3.5: jazyk typu 3 je rozpoznatelný KA; Věta 3.3.1: jazyk rozpoznatelný KA je typu 3. "
        f"„Regulární jazyk“ z kap. 2.3 je tedy tatáž třída. Chytil, s. 130–132. {P}")
    add("Konstrukce gramatiky ke konečnému automatu A = (Q, Σ, δ, q₀, F) (Věta 3.3.1): co jsou neterminály a počáteční symbol?",
        ["Π = Q a S = q₀.", "Π = Σ a S = q₀.", "Π = F a S = q₀.", "Π = Q a S je nový symbol."],
        "Stavy automatu jsou neterminály, vstupní abeceda zůstává jako terminály, počáteční stav je počáteční symbol. "
        f"Chytil, Věta 3.3.1 a důkaz, s. 130. {P}")
    add("Konstrukce gramatiky ke konečnému automatu: jaké pravidlo odpovídá přechodu δ(q, a) = q′?",
        ["q → aq′", "q′ → aq", "q → q′a", "a → qq′"],
        "Pravidlo zapíše přečtený znak a na konec slova a za něj nový stav; neterminál vpravo je aktuální stav. "
        f"Chytil, důkaz Věty 3.3.1, s. 130. {P}")
    add("Konstrukce gramatiky ke konečnému automatu: kdy je v P pravidlo q → e?",
        ["Právě když q ∈ F (q je koncový stav).", "Právě když q = q₀ (počáteční stav).",
         "Pro každý stav q ∈ Q bez výjimky.", "Právě když q ∉ F (q není koncový)."],
        "P = {q → aq′; δ(q, a) = q′} ∪ {q → e; q ∈ F}: odvození smí skončit jen v koncovém stavu. "
        f"Chytil, důkaz Věty 3.3.1, s. 130. {P}")
    add("Gramatika sestrojená k automatu: co říká neterminál na konci odvozeného slova a₁…aₙq?",
        ["Ve kterém stavu je automat po přečtení a₁…aₙ.", "Kolik znaků slova automat ještě musí přečíst.",
         "Které pravidlo se použije jako poslední.", "Jestli je slovo a₁…aₙ prázdné, nebo neprázdné."],
        "q₀ ⇒* a₁…aₙq, právě když automat ze q₀ přejde po a₁…aₙ do stavu q. "
        f"Chytil, důkaz Věty 3.3.1, s. 130. {P}")
    add("Kdy gramatika sestrojená ke konečnému automatu generuje prázdné slovo e?",
        ["Právě když q₀ ∈ F.", "Vždy, každá gramatika generuje e.", "Nikdy, typ 3 e negeneruje.",
         "Právě když má automat jen jeden stav."],
        f"e ∈ L(A) ⇔ q₀ ∈ F ⇔ q₀ → e ∈ P ⇔ e ∈ L(G). Chytil, důkaz Věty 3.3.1, s. 130. {P}")
    add(f"{GR_TXT} Jakého typu je tato gramatika?",
        ["Bezkontextová (typ 2), regulární není.", "Regulární (typ 3).",
         "Jen obecná (typ 0), kontextová ani bezkontextová není.", "Žádného, není to gramatika."],
        "Všechna pravidla mají tvar X → γ. V aBb, aCc, bBa stojí za neterminálem terminál, takže typ 3 ne. "
        f"Pravé strany jsou neprázdné, je tedy i kontextová (typ 1). Doplněno z Claude, ověřeno výpočtem. {P}")
    add(f"{RS_TXT} Co tento systém zachovává?",
        ["Počet nul a počet jedniček ve slově.", "Pořadí znaků ve slově.",
         "První a poslední znak slova.", "Počet výskytů dvojice 01 ve slově."],
        "Pravidla jen prohazují sousední 0 a 1, takže slovo jde přepsat na libovolné jiné se stejným počtem nul "
        f"a jedniček (ověřeno výčtem do délky 7). Chytil, Př. 3.1.3, s. 118–119. {P}")
    add("Jak se v přepisovacím systému značí slova u, z v zápisu u ⇒ z?",
        ["Malými písmeny, jsou to slova z V*.", "Velkými písmeny, jsou to neterminály.",
         "Řeckými písmeny, jsou to pravidla.", "Indexy, jsou to stavy automatu."],
        "Velká písmena jsou pro R, V, P, Π, Σ, S a neterminály. Otázka z přednášky, odpověď z Chytila, "
        f"Def. 3.1.2, s. 118. {P}")
    return c


# ── otázky na výsledek: (text, nápověda, odpověď, postup) ──

def inputs():
    out = []
    d = derivations(T("00110"), T("00011"), RS, 5, 2)  # v verify(): jediné o 2 krocích, o 1 kroku žádné
    check(len(d) == 1 and not derivations(T("00110"), T("00011"), RS, 5, 1))
    out.append((f"{RS_TXT} Kolik kroků (přímých přepisů) má nejkratší odvození 00110 ⇒* 00011?", "číslo",
                str(len(d[0])),
                "00110 ⇒ 00101 ⇒ 00011, oba kroky pravidlem 2 (10 → 01): poprvé na poslední dvojici, podruhé na 3.–4. "
                f"místě. Jedním krokem to nejde. Chytil, Př. 3.1.3, s. 118–119. {P}"))
    out.append((f"{RS_TXT} Odvození 00110 ⇒ 00101 ⇒ 00011: napiš čísla použitých pravidel.", RULES_HINT,
                "".join(str(i) for i, _, _ in d[0]),
                f"V obou krocích se přepisuje dvojice 10 na 01, tedy pravidlo 2 dvakrát. {P}"))
    out.append((f"{RS_TXT} Jakou délku má odvození 00110 ⇒ 00101 ⇒ 00011 v Chytilově počítání?", "číslo",
                str(len(d[0]) + 1),
                "Chytil bere u = u₁ ⇒ u₂ ⇒ … ⇒ uₙ = z, odvození délky n má n slov a n − 1 kroků. Tady 3 slova, 2 kroky. "
                f"Doplněno z Claude, Chytil, Def. 3.1.2 bod 2, s. 118. {P}"))
    one = sorted("".join(z) for _, _, z in steps(T("00110"), RS))
    out.append((f"{RS_TXT} Na kolik různých slov se 00110 přímo přepíše (jedním krokem)?", "číslo", str(len(one)),
                f"Dvojice 01 na 2.–3. místě dá {one[1]} (pravidlo 1), dvojice 10 na 4.–5. místě dá {one[0]} (pravidlo 2). {P}"))
    allw = reach(T("00110"), RS, 5)
    check(len(allw) == 10)
    out.append((f"{RS_TXT} Kolik různých slov z splňuje 00110 ⇒* z? (Počítá se i 00110 samo, ⇒* je reflexivní.)", "číslo", str(len(allw)),
                "Systém přepíše slovo právě na slova se stejným počtem nul a jedniček: 5 míst, 2 jedničky, "
                f"5! ÷ (2! · 3!) = 10 slov. Chytil, Př. 3.1.3, s. 119. {P}"))
    check(T("00111") not in reach(T("00110"), RS, 5))
    out.append((f"{RS_TXT} Platí 00110 ⇒* 00111?", YN_HINT, "ne",
                f"Pravidla nemění počet jedniček: 00110 má dvě, 00111 tři. {P}"))
    # gramatika S → aBb …
    d = derivations(T("S"), T("aabaacb"), GR, 7, 10)[0]
    out.append((f"{GR_TXT} Napiš čísla pravidel odvození S ⇒* aabaacb v pořadí použití.", RULES_HINT,
                "".join(str(i) for i, _, _ in d),
                "S ⇒ aBb (1) ⇒ aaCcb (2) ⇒ aabBacb (3) ⇒ aabaacb (4). Je to jediné odvození tohoto slova. "
                f"Ověřeno výpočtem. {P}"))
    out.append((f"{GR_TXT} Kolik kroků má odvození S ⇒* aabaacb?", "číslo", str(len(d)),
                f"S ⇒ aBb ⇒ aaCcb ⇒ aabBacb ⇒ aabaacb: čtyři přímé přepisy. {P}"))
    used = {i for i, _, _ in d}
    unused = [i for i in range(1, 6) if i not in used]
    check(unused == [5])
    out.append((f"{GR_TXT} Které pravidlo se v odvození S ⇒* aabaacb nepoužije?", "číslo pravidla", str(unused[0]),
                f"Použijí se pravidla 1, 2, 3, 4; C → b ne, C se přepíše pravidlem 3 na bBa. {P}"))
    form = T("aaCcb")
    nxt = [i for i, _, z in steps(form, GR) if T("aabaacb") in reach(z, GR, 7)]
    check(nxt == [3] and sorted(i for i, _, _ in steps(form, GR)) == [3, 5])
    out.append((f"{GR_TXT} V odvození S ⇒* aabaacb máme slovo aaCcb. Které pravidlo se musí použít dál?",
                "číslo pravidla", "3",
                f"Pravidlo 5 by dalo aabcb, z něj aabaacb nevznikne. Pravidlo 3 dá aabBacb a pravidlo 4 pak aabaacb. {P}"))
    L = gen_lang(GR, T("S"), NT, 11)
    out.append((f"{GR_TXT} Napiš nejkratší slovo jazyka L(G).", "slovo z písmen a, b, c bez mezer",
                min(L, key=len), f"S ⇒ aBb (1) ⇒ aab (4). Kratší slovo bez neterminálu odvodit nejde. Ověřeno výčtem. {P}"))
    d = derivations(T("aabaacb"), T("S"), AN, 7, 10)[0]
    out.append((f"{GR_TXT} Analytická verze má obrácené šipky (1) aBb → S, (2) aCc → B, (3) bBa → C, (4) a → B, "
                "(5) b → C. Napiš čísla pravidel redukce aabaacb ⇒* S v pořadí použití.", RULES_HINT,
                "".join(str(i) for i, _, _ in d),
                "aabaacb ⇒ aabBacb (4, na 4. symbol a) ⇒ aaCcb (3) ⇒ aBb (2) ⇒ S (1). Je to generativní odvození "
                f"pozpátku. Chytil, Def. 3.1.8, s. 123. {P}"))
    # Chomského typ jednotlivých pravidel
    for r, t in RULE_TYPES:
        why = {3: "jeden neterminál vlevo, vpravo terminály a nejvýš jeden neterminál úplně vpravo",
               2: "vlevo jediný neterminál, ale vpravo je za neterminálem terminál, takže ne typ 3",
               1: "tvar αXβ → αγβ s α = a, β = b, X přepsáno na neprázdné γ = YZ; vlevo víc symbolů, takže ne typ 2",
               0: "vlevo víc symbolů a nejde o tvar αXβ → αγβ s neprázdným γ"}[t]
        if r == "X → e":  # tvary typů nejsou vnořené: X → e splňuje typ 3 i 2, ale typ 1 ne
            why = ("X → w s w = e ∈ Σ*, takže typ 3 (i typ 2). Kontextové pravidlo to není: γ musí být neprázdné, "
                   "výjimka je jen S → e")
        out.append((f"X, Y, Z ∈ Π, a, b ∈ Σ. Jaký je nejvyšší typ Chomského hierarchie (0 až 3), jehož tvar splňuje "
                    f"pravidlo {r}?", "číslo 0 až 3", str(t),
                    f"Typ {t}: {why}. Chytil, Def. 3.2.1, s. 124–125. {P}"))
    # gramatika ke konečnému automatu
    out.append((f"{KA_TXT} Kolik pravidel má gramatika sestrojená podle Věty 3.3.1?", "číslo", str(len(KG)),
                "Za každý přechod (3 stavy · 2 znaky = 6) jedno pravidlo q → aq′ a za koncový stav q₀ pravidlo q₀ → e: 7. "
                f"Chytil, Př. 3.3.2, s. 131. {P}"))
    d = derivations(("q0",), T("1100"), KG, 5, 10)[0]
    out.append((f"{KA_TXT} {KG_TXT} Napiš čísla pravidel odvození q₀ ⇒* 1100 v pořadí použití.", RULES_HINT,
                "".join(str(i) for i, _, _ in d),
                "q₀ ⇒ 1q₁ (2) ⇒ 11q₂ (5) ⇒ 110q₀ (6) ⇒ 1100q₀ (1) ⇒ 1100 (3). Každý krok je jeden přechod automatu "
                f"q₀ → q₁ → q₂ → q₀ → q₀, poslední q₀ → e jde jen proto, že q₀ ∈ F. Chytil, Př. 3.3.2, s. 131. {P}"))
    d = derivations(("q0",), T("10"), KG, 3, 10)[0]
    out.append((f"{KA_TXT} {KG_TXT} Napiš čísla pravidel odvození q₀ ⇒* 10 v pořadí použití.", RULES_HINT,
                "".join(str(i) for i, _, _ in d),
                f"q₀ ⇒ 1q₁ (2) ⇒ 10q₀ (4) ⇒ 10 (3). Automat: q₀ → q₁ → q₀ ∈ F. Ověřeno výpočtem. {P}"))
    out.append((f"{KA_TXT} {KG_TXT} Kolik kroků má odvození q₀ ⇒* 1100?", "číslo", "5",
                f"Čtyři kroky za čtyři přečtené znaky a jeden krok q₀ → e na konci: n + 1 = 5. {P}"))
    LG = gen_lang(KG, ("q0",), set(KQ), 10)
    out.append((f"{KA_TXT} Patří slovo 1101 do jazyka gramatiky sestrojené k automatu?", YN_HINT,
                "ano" if "1101" in LG else "ne",
                "Automat: q₀ → q₁ → q₂ → q₀ → q₁ ∉ F. V gramatice zůstane na konci q₁ a pravidlo q₁ → e neexistuje. "
                f"Jazyk je {{e}} ∪ slova končící 0 (doplněno z Claude, ověřeno do délky 10). {P}"))
    out.append((f"{KA_TXT} Kolik slov délky 3 generuje gramatika sestrojená k automatu?", "číslo",
                str(sum(len(w) == 3 for w in LG)),
                f"Generuje e a slova končící 0; délky 3 jsou to 000, 010, 100, 110. Ověřeno výčtem. {P}"))
    return out


# ── rozbor (reveal): (text, řešení) ──

def reveal():
    return [
        (f"{RS_TXT} Ukaž odvození 00110 ⇒* 00011 a u každého kroku uveď číslo pravidla a přepsanou část.",
         "00110 ⇒ 00101 (pravidlo 2 na poslední dvojici 10)\n00101 ⇒ 00011 (pravidlo 2 na dvojici 10 na 3.–4. místě)\n"
         "Odvození je minimální (slova se neopakují) a nejkratší. Z 00110 jde přímo také na 01010, "
         f"ta cesta kratší není. Chytil, Př. 3.1.3, s. 118–119. {P}"),
        (f"{GR_TXT} Ukaž, že aabaacb ∈ L(G).",
         "S ⇒ aBb (1)\n⇒ aaCcb (2, na B)\n⇒ aabBacb (3, na C)\n⇒ aabaacb (4, na B)\n"
         f"Výsledné slovo obsahuje jen terminály, proto aabaacb ∈ L(G). Ověřeno výpočtem (jediné odvození). {P}"),
        (f"{GR_TXT} Obrať šipky ve všech pravidlech a ukaž v analytické gramatice, že aabaacb ⇒* S.",
         "Pravidla: (1) aBb → S, (2) aCc → B, (3) bBa → C, (4) a → B, (5) b → C (vpravo vždy neterminál).\n"
         "aabaacb ⇒ aabBacb (4, na 4. symbol a)\n⇒ aaCcb (3, na bBa)\n⇒ aBb (2, na aCc)\n⇒ S (1)\n"
         f"Je to generativní odvození přečtené pozpátku. Chytil, Def. 3.1.8, s. 123–124. {P}"),
        ("Vypiš Chomského rozdělení gramatik: typ 0 až 3, název, tvar pravidel a co jazyky daného typu rozpoznává.",
         "Typ 0, obecná: α → β, α = uXv, X ∈ Π; Turingův stroj.\n"
         "Typ 1, kontextová: αXβ → αγβ, γ ∈ (Π ∪ Σ)⁺ (výjimka S → e, pak S není vpravo); lineárně omezený Turingův stroj (Vais).\n"
         "Typ 2, bezkontextová: X → γ, γ ∈ (Π ∪ Σ)*; nedeterministický zásobníkový automat.\n"
         "Typ 3, regulární: X → wY nebo X → w, w ∈ Σ*; konečný automat.\n"
         f"Hierarchie 𝓛₃ ⊆ 𝓛₂ ⊆ 𝓛₁ ⊆ 𝓛₀. Chytil, Def. 3.2.1, Tvrzení 3.2.6, s. 124–125; Vais, kap. 2.8, s. 56. {P}"),
        (f"{KA_TXT} Sestroj k automatu regulární gramatiku a ukaž, že automat slovo 1100 rozpozná a gramatika ho vygeneruje.",
         "Π = Q = {q₀, q₁, q₂}, Σ = {0, 1}, S = q₀.\n"
         "P: q₀ → 0q₀ | 1q₁ | e, q₁ → 0q₀ | 1q₂, q₂ → 0q₀ | 1q₂ (q₀ → e, protože q₀ ∈ F).\n"
         "Automat: q₀ –1→ q₁ –1→ q₂ –0→ q₀ –0→ q₀ ∈ F.\n"
         "Gramatika: q₀ ⇒ 1q₁ ⇒ 11q₂ ⇒ 110q₀ ⇒ 1100q₀ ⇒ 1100.\n"
         f"Neterminál na konci je vždy aktuální stav automatu. Chytil, Věta 3.3.1, Př. 3.3.2, s. 130–131. {P}"),
        ("Dveře z přednášky 5. 11.: Q = {q₀, q₁}, Σ = {0, 1}, počáteční q₀, F = {q₁}, δ(q₀, 0) = q₀, δ(q₀, 1) = q₁, "
         "δ(q₁, 0) = q₀, δ(q₁, 1) = q₁. Sestroj podle Věty 3.3.1 gramatiku a odvoď v ní slovo 101.",
         "Π = {q₀, q₁}, S = q₀, P: q₀ → 0q₀ | 1q₁, q₁ → 0q₀ | 1q₁ | e (q₁ → e, protože q₁ ∈ F; q₀ → e ne).\n"
         "q₀ ⇒ 1q₁ ⇒ 10q₀ ⇒ 101q₁ ⇒ 101.\n"
         "Prázdné slovo gramatika negeneruje, protože q₀ ∉ F. Ověřeno výpočtem. "
         f"Úloha k procvičení z přednášky 12. 11. použitá na automat z 5. 11."),
        ("Dokaž lemma: když u ⇒* z, existuje minimální odvození z ze slova u.",
         "Vezmi libovolné odvození u = u₁ ⇒ … ⇒ uₙ = z. Není-li minimální, existují i < j s uᵢ = uⱼ. "
         "Úsek uᵢ ⇒ … ⇒ uⱼ vypustíme a nahradíme slovem uᵢ; dostaneme kratší odvození téhož z. "
         "Odvození je konečné, takže po konečně mnoha krocích zbude odvození bez opakování, tedy minimální. "
         f"Chytil, Lemma 3.1.4, s. 119. {P}"),
    ]


def main():
    verify()
    groups = [("choice", choice()), ("input", inputs()), ("reveal", reveal())]
    qs, longest = build(groups, random.Random(112), "7")
    other = {q["id"] for p in (HERE / "banky").glob("*.json") if p.name != "07-2026-11-12.json"
             for q in json.loads(p.read_text(encoding="utf-8"))["questions"]}
    check(not {q["id"] for q in qs} & other, "id otázek musí být unikátní napříč přednáškami")
    for q in qs:
        if q["type"] == "input" and not q.get("reveal"):
            check(q["answer"] == "0" or not q["answer"].startswith("0"), q["id"])
    out = {"title": "Gramatiky", "lecture": 7, "date": "2026-11-12", "questions": qs}
    path = HERE / "banky" / "07-2026-11-12.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter("reveal" if q.get("reveal") else q["type"] for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({c['choice']} výběrových, {c['input']} na výsledek, {c['reveal']} na rozbor)")
    print(f"správná možnost nejdelší: {longest} z {c['choice']}")
    print(f"kontrol (assert): {CHECKS}")


if __name__ == "__main__":
    main()
