#!/usr/bin/env python3
"""Vygeneruje dvě banky přednášky 26. 11. 2026:
  banky/09-2026-11-26.json   (id 9-N):  zásobníkové automaty a bezkontextové jazyky (Chytil, Věta 4.5.1),
  banky/09t-turinguv-stroj.json (id 9t-N): Turingův stroj (Chytil, Def. 6.1.1–6.1.4, s. 260–262 a 268).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Opus 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z výpisků přednášky 26. 11. 2026 (vault TZI1: Prednasky/2026-11-26-za-a-bezkontextove-jazyky
a Prednasky/2026-11-26-turinguv-stroj), z fotek tabule a z Chytila (Automaty a gramatiky), ověřeno podle skenu.
Výpočty (levá derivace, výpočet zásobníkového automatu, kroky Turingova stroje) se tu počítají simulací,
ne ručně v JSON. Nejisté místo rukopisu (pravidlo 2 příkladu Turingova stroje) se používá jen v opraveném
znění δ(q₁, b), které jediné dává výpočet z tabule.
Pořadí otázek = výuková posloupnost (pojmy → definice → vlastnosti → příklady → rozbor).
Zapisuje se JEN banky/09-2026-11-26.json a banky/09t-turinguv-stroj.json.
Spuštění:  python3 build_bank_9.py
"""
import json
import random
from collections import Counter
from pathlib import Path

from build_bank_6 import build

HERE = Path(__file__).parent
CHECKS = 0
P = "Přednáška 26. 11."
YN = "ano nebo ne (bez tečky)"


def check(cond, msg=""):
    global CHECKS
    assert cond, msg
    CHECKS += 1


# ── zásobníkový automat z gramatiky (Věta 4.5.1): vrchol zásobníku vlevo ──

G_RULES = [("A", "aAc"), ("A", "B"), ("B", "bBc"), ("B", "")]  # pravidla 1–4 z přednášky
TERM = {"a": 5, "b": 6, "c": 7}  # instrukce typu 2: δ(q, x, x) = {(q, e)}


def za_run(w, stack="A", rules=G_RULES, term=TERM):
    """Přijímající výpočet prázdným zásobníkem: [(č. instrukce, zbylý vstup, zásobník)], nebo None."""
    nonterm = {l for l, _ in rules}

    def go(w, st, path):
        if not w and not st:
            return path
        if not st or len(st) > len(w) + 3:  # neterminál dává nejvýš dva terminály navíc, delší zásobník nepřečte
            return None
        x = st[0]
        if x in nonterm:
            for n, (l, r) in enumerate(rules, 1):
                if l == x:
                    p = go(w, r + st[1:], path + [(n, w, r + st[1:])])
                    if p:
                        return p
            return None
        if w and w[0] == x:
            return go(w[1:], st[1:], path + [(term[x], w[1:], st[1:])])
        return None

    return go(w, stack, [])


def left_derivation(w, start="A", rules=G_RULES):
    """Čísla pravidel levé derivace start ⇒* w (prohledávání, větné formy omezené délkou)."""
    todo = [(start, [])]
    while todo:
        f, used = todo.pop(0)
        if f == w:
            return used
        i = next((k for k, ch in enumerate(f) if ch.isupper()), None)
        if i is None or len(f.replace("A", "").replace("B", "")) > len(w):
            continue
        for n, (l, r) in enumerate(rules, 1):
            if l == f[i]:
                todo.append((f[:i] + r + f[i + 1:], used + [n]))
    return None


def in_lang(w):
    """Nezávislý popis jazyka gramatiky: aⁿ bᵐ cⁿ⁺ᵐ."""
    na, nb = len(w) - len(w.lstrip("a")), 0
    rest = w[na:]
    nb = len(rest) - len(rest.lstrip("b"))
    rest = rest[nb:]
    return set(rest) <= {"c"} and len(rest) == na + nb


def fmt_conf(w, st):
    return f"(q, {w or 'e'}, {st or 'e'})"


# ── Turingův stroj: konfigurace (u, q, v), hlava na prvním symbolu v, Λ = prázdné ──

def ts_step(u, q, v, delta):
    """Bezprostředně následující konfigurace podle Def. 6.1.4 (prázdné okraje doplní Λ, Pozn. 6.1.3)."""
    x = v[0] if v else "Λ"
    q2, x2, d = delta[(q, x)]
    if d == +1:
        return u + x2, q2, v[1:]
    u = u or "Λ"
    return u[:-1], q2, u[-1] + x2 + v[1:]


TS = {("q0", "a"): ("q1", "b", +1), ("q1", "b"): ("qf", "b", -1)}  # příklad z přednášky (pravidlo 2 opraveno)


def ts_run(w, delta=TS, final=("qf",), limit=50):
    conf, out = ("", "q0", w), [("", "q0", w)]
    for _ in range(limit):
        if conf[1] in final:
            return out, True
        if (conf[1], conf[2][0] if conf[2] else "Λ") not in delta:
            return out, False
        conf = ts_step(*conf, delta)
        out.append(conf)
    raise AssertionError("výpočet neskončil")


def cs(c):
    return "".join(c)


def verify():
    # zásobníkový automat: přijímá právě jazyk gramatiky (všechna slova nad {a, b, c} do délky 7)
    import itertools
    for n in range(8):
        for t in itertools.product("abc", repeat=n):
            w = "".join(t)
            check((za_run(w) is not None) == in_lang(w), w)
    check(left_derivation("bbcc") == [2, 3, 3, 4])
    # instrukce 1–4 výpočtu jdou v pořadí levé derivace
    check([n for n, _, _ in za_run("bbcc") if n <= 4] == left_derivation("bbcc"))
    # Turingův stroj: krok +1 / −1 podle Def. 6.1.4
    check(cs(ts_step("ab", "q", "cd", {("q", "c"): ("p", "z", +1)})) == "abzpd")
    check(cs(ts_step("ab", "q", "cd", {("q", "c"): ("p", "z", -1)})) == "apbzd")
    out, ok = ts_run("abb")
    check(ok and [cs(c) for c in out] == ["q0abb", "bq1bb", "qfbbb"])


def za_bank():
    run = za_run("bbcc")
    instr = "".join(str(n) for n, _, _ in run)
    trace = " ⊢ ".join([fmt_conf("bbcc", "A")] + [fmt_conf(w, s) for _, w, s in run])
    check(instr == "23636477" and len(run) == 8)
    G = ("Gramatika z přednášky: Π = {A, B}, Σ = {a, b, c}, pravidla (1) A → aAc, (2) A → B, (3) B → bBc, "
         "(4) B → e. Počáteční symbol S = A.")
    expl_kon = "Chytil, Věta 4.5.1, s. 172 (ověřeno podle skenu)."
    choice = [
        ("Co tvrdí věta, kterou přednáška začala (Chytil, Věta 4.5.1)?",
         ["Ke každému bezkontextovému jazyku L existuje nedeterministický ZA s jediným stavem, L = N(ℳ).",
          "Ke každému bezkontextovému jazyku existuje deterministický ZA s jediným stavem a L = L(ℳ) koncovým stavem.",
          "Ke každému bezkontextovému jazyku existuje konečný automat s jediným stavem.",
          "Ke každému zásobníkovému automatu existuje regulární gramatika se stejným jazykem."],
         [0], f"ℳ rozpoznává L prázdným zásobníkem. Opačný směr (ze ZA gramatika) je Věta 4.5.5. {expl_kon} {P}"),
        ("Jakým způsobem rozpoznává jazyk automat sestrojený z gramatiky podle Věty 4.5.1?",
         ["Prázdným zásobníkem: slovo je přečtené a zásobník prázdný.",
          "Koncovým stavem: po přečtení slova je ve stavu z F.",
          "Tím, že na zásobníku zůstane počáteční symbol S.",
          "Tím, že přečte celé slovo a na vrcholu zásobníku zůstane nějaký terminál."],
         [0], f"Proto L = N(ℳ) a F = ∅. {expl_kon} {P}"),
        ("Kolik stavů má zásobníkový automat z konstrukce podle Věty 4.5.1?",
         ["Jediný stav q; všechnu potřebnou informaci nese zásobník.",
          "Tolik stavů, kolik má gramatika neterminálů; každý neterminál má svůj stav.",
          "Dva stavy: počáteční q₀ a koncový stav, do kterého přejde po přečtení.",
          "Tolik stavů, kolik má gramatika pravidel."],
         [0], f"ℳ = ({{q}}, Σ, Π ∪ Σ, δ, q, S, ∅). {expl_kon} {P}"),
        ("Jaká je zásobníková abeceda Γ automatu sestrojeného z gramatiky (Π, Σ, S, P)?",
         ["Γ = Π ∪ Σ: do zásobníku se píšou neterminály i terminály.",
          "Γ = Π: do zásobníku se píšou jen neterminály, terminály se čtou ze vstupu.",
          "Γ = Σ: do zásobníku se píšou jen terminály.",
          "Γ = Π × Σ: v zásobníku jsou uspořádané dvojice neterminál a terminál."],
         [0], f"Pravé strany pravidel obsahují obojí. {expl_kon} {P}"),
        ("Co je počáteční symbol zásobníku Z₀ automatu sestrojeného z gramatiky (Π, Σ, S, P)?",
         ["Počáteční symbol gramatiky S.",
          "Prázdné slovo e.",
          "Stav q.",
          "První symbol vstupního slova."],
         [0], f"Výpočet začíná se S v zásobníku, tak jako derivace začíná od S. {expl_kon} {P}"),
        ("Proč má automat z Věty 4.5.1 množinu koncových stavů F = ∅?",
         ["Rozpoznává prázdným zásobníkem, takže F je nepodstatná.",
          "Automat s F = ∅ nepřijímá žádné slovo, jazyk je prázdný.",
          "F = ∅ znamená, že přijímá každé slovo nad Σ.",
          "Jediný stav nesmí být současně počáteční a koncový."],
         [0], f"U rozpoznávání prázdným zásobníkem se F obvykle klade ∅ (přednáška 19. 11.). {expl_kon} {P}"),
        ("Co dělá instrukce typu 1, δ(q, e, D) = {(q, η); D → η je pravidlo z P}?",
         ["Bez čtení vstupu nahradí neterminál D na vrcholu pravou stranou η některého pravidla.",
          "Přečte ze vstupu symbol D a ze zásobníku ho odebere, stav se nemění.",
          "Přidá neterminál D pod vrchol zásobníku a vstup přitom vůbec nečte.",
          "Přečte ze vstupu celé slovo η a neterminál D nechá v zásobníku."],
         [0], f"V každém kroku se buď nahrazuje vrchní symbol řetězcem (typ 1), nebo se odebírá (typ 2). "
              f"Chytil, s. 172. {P}"),
        ("Co dělá instrukce typu 2, δ(q, a, a) = {(q, e)} pro a ∈ Σ?",
         ["Je-li na vrcholu terminál a a na vstupu také a, přečte ho a ze zásobníku odebere.",
          "Je-li na vrcholu a, přidá na zásobník další a a přečte symbol ze vstupu.",
          "Nahradí terminál a pravou stranou pravidla, ve kterém a vystupuje.",
          "Přeskočí a na vstupu bez čtení a obsah zásobníku nechá beze změny."],
         [0], f"Jde o „odškrtnutí“ už vygenerovaného terminálu proti vstupu. Chytil, s. 172. {P}"),
        ("Proč je automat sestrojený podle Věty 4.5.1 nedeterministický?",
         ["Pro jeden neterminál může být víc pravidel, δ(q, e, D) má pak víc dvojic.",
          "Protože má jediný stav, a ten se během celého výpočtu nemůže změnit na jiný stav.",
          "Protože instrukce typu 2 nečtou vstup a zásobník mění bez čtení.",
          "Protože F = ∅, takže automat neví, kdy má výpočet ukončit."],
         [0], f"Automat si „vybírá“, kterým pravidlem neterminál přepíše; přijme, když aspoň jedna volba vede "
              f"k prázdnému zásobníku. {expl_kon} {P}"),
        ("Čemu odpovídá výpočet automatu sestrojeného podle Věty 4.5.1?",
         ["Levé derivaci podle gramatiky: krok typu 1 = přepis nejlevějšího neterminálu.",
          "Pravé derivaci: přepisuje se vždy nejpravější neterminál.",
          "Derivaci pozpátku: od přečteného slova postupně zpět až k počátečnímu symbolu gramatiky S.",
          "Žádné derivaci, automat jen porovnává počty symbolů ve slově."],
         [0], f"Přečtená část vstupu + obsah zásobníku je vždy větná forma levé derivace. "
              f"Chytil, důkaz Věty 4.5.1, s. 172–173. {P}"),
    ]
    inputs = [
        (f"{G} Kolik instrukcí typu 1 a typu 2 dohromady vznikne konstrukcí podle Věty 4.5.1? "
         f"(Každou dvojici v δ(q, e, D) počítej zvlášť.)", "číslo", "7",
         "Typ 1: čtyři dvojice, jedna z každého pravidla, δ(q, e, A) = {(q, aAc), (q, B)}, "
         "δ(q, e, B) = {(q, bBc), (q, e)}. Typ 2: jedna pro každý terminál, δ(q, a, a), δ(q, b, b), δ(q, c, c), "
         f"vše = {{(q, e)}}. Celkem 4 + 3 = 7. {P}"),
        (f"{G} Levá derivace A ⇒* bbcc: napiš čísla použitých pravidel.",
         "čísla pravidel v pořadí použití, bez mezer, např. 312", "2334",
         f"A ⇒ B (2) ⇒ bBc (3) ⇒ bbBcc (3) ⇒ bbcc (4). Ověřeno výpočtem. {P}"),
        (f"{G} Instrukce jsou číslované 1–4 podle pravidel a 5, 6, 7 = δ(q, a, a), δ(q, b, b), δ(q, c, c). "
         f"Kolik kroků má výpočet automatu, který přijme slovo bbcc?", "číslo", "8",
         f"{trace}. Čtyři kroky typu 1 (pravidla derivace) a čtyři typu 2 (jeden na každé písmeno). "
         f"Ověřeno simulací. {P}"),
        (f"{G} Instrukce jsou číslované 1–4 podle pravidel a 5, 6, 7 = δ(q, a, a), δ(q, b, b), δ(q, c, c). "
         f"Napiš čísla instrukcí výpočtu, který přijme slovo bbcc.", "čísla instrukcí v pořadí, bez mezer",
         instr,
         f"{trace}. Instrukce 1–4 jdou v pořadí levé derivace (2, 3, 3, 4). Na tabuli jsou poslední dva kroky "
         f"označené jako 4, správně je 7 (na vrcholu je c). Ověřeno simulací. {P}"),
        (f"{G} Přijme automat sestrojený podle Věty 4.5.1 slovo abcc?", YN,
         "ano" if za_run("abcc") else "ne",
         "Ano: A ⇒ aAc ⇒ aBc ⇒ abBcc ⇒ abcc, tedy pravidla 1, 2, 3, 4, a automat výpočet napodobí. "
         f"Jazyk gramatiky je aⁿbᵐcⁿ⁺ᵐ. Ověřeno simulací. {P}"),
        (f"{G} Přijme automat sestrojený podle Věty 4.5.1 slovo abc?", YN,
         "ano" if za_run("abc") else "ne",
         "Ne: každé a i každé b přidá jedno c, takže c musí být tolik, kolik je a a b dohromady (abcc). "
         f"Žádná volba instrukcí nevede k prázdnému zásobníku. Ověřeno simulací. {P}"),
    ]
    check(inputs[4][2] == "ano" and inputs[5][2] == "ne")
    reveal = [
        (f"{G} Zapiš výpočet automatu nad slovem bbcc krok po kroku a u každého kroku vysvětli, "
         f"proč je použita právě ta instrukce.",
         "\n".join(
             [f"Vrchol zásobníku je vlevo. Situace (q, zbylý vstup, zásobník)."]
             + [f"{i}. {fmt_conf(*( (run[i-2][1], run[i-2][2]) if i > 1 else ('bbcc', 'A')))} ⊢({n}) {fmt_conf(w, s)}"
                for i, (n, w, s) in enumerate(run, 1)]
             + ["Krok 1: vstup začíná b; pravidlo 1 by dalo navrch a, které se s b nikdy neshoduje, proto pravidlo 2.",
                "Kroky 2 a 4: B → bBc, protože vstup začíná b.",
                "Krok 6: vstup začíná c, pravidlo 3 by dalo navrch b, proto B → e.",
                "Kroky 3, 5, 7, 8: na vrcholu terminál shodný se vstupem, přečíst a odebrat (6, 6, 7, 7).",
                f"Konec (q, e, e): slovo přečtené, zásobník prázdný, bbcc ∈ N(ℳ). Ověřeno simulací. {P}"])),
        ("Gramatika: Π = {S}, Σ = {a, b}, pravidla (1) S → aSb, (2) S → e, (3) S → ab. "
         "Sestroj podle Věty 4.5.1 zásobníkový automat a zapiš jeho výpočet nad slovem aabb.",
         "ℳ = ({q}, {a, b}, {S, a, b}, δ, q, S, ∅)\n"
         "Typ 1: δ(q, e, S) = {(q, aSb), (q, e), (q, ab)}\n"
         "Typ 2: δ(q, a, a) = {(q, e)}, δ(q, b, b) = {(q, e)}\n"
         "Výpočet: (q, aabb, S) ⊢ (q, aabb, aSb) ⊢ (q, abb, Sb) ⊢ (q, abb, abb) ⊢ (q, bb, bb) ⊢ (q, b, b) ⊢ (q, e, e)\n"
         f"(třetí krok použil S → ab; šlo by i S → aSb a pak S → e). Ověřeno simulací. Úloha na procvičení konstrukce "
         f"z přednášky 26. 11. (doplněno z Claude)."),
    ]
    # ověření druhé úlohy na rozbor
    check(za_run("aabb", "S", [("S", "aSb"), ("S", ""), ("S", "ab")], {"a": 4, "b": 5}) is not None)
    return [("choice", choice), ("input", inputs), ("reveal", reveal)]


def ts_bank():
    D = "Chytil, Def. 6.1.1, s. 261 (ověřeno podle skenu)."
    choice = [
        ("Z čeho se skládá Turingův stroj (model z přednášky)?",
         ["Z konečné řídicí jednotky a nekonečné pásky z políček; hlava čte jedno políčko.",
          "Z řídicí jednotky, vstupní pásky určené jen pro čtení a zásobníku na mezivýsledky.",
          "Z konečné pásky, kterou hlava čte jen zleva doprava.",
          "Ze dvou zásobníků a řídicí jednotky, která nemá žádné vnitřní stavy."],
         [0], f"Chytil, čl. 6.1 a obr. 45, s. 260. {P}"),
        ("Turingův stroj je pětice ℳ = (Q, Σ, δ, q₀, F). Co je F?",
         ["Množina koncových stavů, F ⊆ Q.",
          "Prázdný symbol pásky.",
          "Množina symbolů, které smí být na pásce.",
          "Počáteční stav stroje."],
         [0], f"Q stavy, Σ symboly stroje, δ přechodová funkce, q₀ počáteční stav, F cílová (koncová) množina. {D} {P}"),
        ("Jaký je definiční obor přechodové funkce Turingova stroje?",
         ["(Q − F) × Σ: dvojice nekoncový stav a symbol.",
          "Q × Σ: všechny dvojice stav a symbol.",
          "Q × Σ × {−1, +1}: trojice stav, symbol, směr.",
          "F × Σ: jen koncové stavy a symboly."],
         [0], f"δ: (Q − F) × Σ → Q × Σ × {{−1, +1}} je parciální funkce. {D} {P}"),
        ("Proč je v definici Turingova stroje δ: (Q − F) × Σ → … právě Q − F? (bude u zkoušky)",
         ["Z koncového stavu není definován další přechod, takže výpočet v okamžiku přijetí skončí.",
          "Koncové stavy nesmí číst žádný symbol, protože páska je v nich už celá prázdná.",
          "Aby stroj nemohl začít výpočet v koncovém stavu q₀ ∈ F.",
          "Aby δ byla totální funkce definovaná na všech dvojicích stav a symbol."],
         [0], f"Chytil, s. 268: „Podle definice 6.1.1 není z takového stavu další přechod definován, a výpočet "
              f"proto v okamžiku přijetí končí.“ (ověřeno podle skenu). {P}"),
        ("Co znamená δ(q, x) = (q′, x′, d) u Turingova stroje?",
         ["Ve stavu q na políčku s x přepíše x na x′, přejde do q′ a posune se o d.",
          "Ve stavu q přečte x′, zapíše x, přejde do q′ a posune se o d.",
          "Posune se o d políček, teprve tam přečte symbol x a přejde do stavu q.",
          "Přepíše stav q na x′ a symbol x na q′, hlava stojí."],
         [0], f"{D} {P}"),
        ("Co u Turingova stroje znamená posun d = +1 a d = −1?",
         ["d = +1 posun o políčko doprava, d = −1 doleva.",
          "d = +1 posun doleva, d = −1 doprava.",
          "d = +1 přidá symbol na pásku, d = −1 ho smaže.",
          "d = +1 přejde do dalšího stavu, d = −1 do předchozího."],
         [0], f"„… a potom se posune o d políček doprava.“ {D} {P}"),
        ("Turingův stroj chce symbol x na čteném políčku nechat beze změny. Co udělá?",
         ["Přepíše ho stejným symbolem, tedy x′ = x.",
          "Políčko nepřepíše, instrukce může zápis vynechat.",
          "Zapíše na políčko prázdný symbol Λ.",
          "Posune se bez čtení a symbol přeskočí."],
         [0], f"Políčko, na kterém stojí, musí vždy přepsat (δ vždy vrací x′). {P}"),
        ("Co znamená symbol Λ na pásce Turingova stroje?",
         ["Prázdné políčko (Chytil místo něj píše b).",
          "Prázdné slovo e, tedy slovo délky nula.",
          "Koncový stav, ve kterém stroj zastaví.",
          "Značku začátku vstupního slova na pásce."],
         [0], f"Chytil, s. 261: symbol b ∈ Σ znamená prázdné políčko. {P}"),
        ("Co popisuje konfigurace uqv Turingova stroje (u, v ∈ Σ*, q ∈ Q)?",
         ["Na pásce je uv, jinde prázdno, stav je q, hlava čte první symbol v.",
          "Na pásce je uv, stav je q, hlava čte poslední symbol u.",
          "Na pásce je jen slovo v, slovo u už stroj během výpočtu smazal a jeho políčka jsou prázdná.",
          "Slovo u je stav, q symbol pod hlavou a v zbytek pásky."],
         [0], f"Chytil, Def. 6.1.2, s. 261 (ověřeno podle skenu). {P}"),
        ("Konfigurace K = uyqxv a δ(q, x) = (q′, x′, +1). Která konfigurace bezprostředně následuje po K?",
         ["uyx′q′v",
          "uq′yx′v",
          "uyq′x′v",
          "uyxq′v"],
         [0], f"Při +1 se stav zapíše za přepsaný symbol, hlava je na prvním symbolu v. Chytil, Def. 6.1.4, "
              f"s. 261. {P}"),
        ("Konfigurace K = uyqxv a δ(q, x) = (q′, x′, −1). Která konfigurace bezprostředně následuje po K?",
         ["uq′yx′v",
          "uyx′q′v",
          "uyq′x′v",
          "q′uyx′v"],
         [0], f"Při −1 se stav zapíše před y, hlava je na y. Chytil, Def. 6.1.4, s. 262. {P}"),
        ("Proč se v definici bezprostředně následující konfigurace píše K = uyqxv se symbolem y vlevo od hlavy?",
         ["Při posunu −1 se hlava přesune na y, musí být kam couvnout.",
          "y je symbol přímo pod hlavou, který stroj v tomto kroku přepíše.",
          "y je nový symbol, který stroj na pásku zapíše místo x.",
          "y označuje stav, do kterého stroj po kroku přejde."],
         [0], f"Pod hlavou je x, vlevo od něj y. Chytil, Def. 6.1.4, s. 261. {P}"),
        ("Co znamená E ⊢*ℳ E′ u Turingova stroje?",
         ["Existují E₁, …, Eₘ, E₁ = E, Eₘ = E′, Eᵢ ⊢ Eᵢ₊₁: z E se dá dojít do E′.",
          "Konfigurace E′ následuje po E bezprostředně, tedy vždy právě jedním krokem výpočtu.",
          "Z konfigurace E stroj nikdy neskončí.",
          "E a E′ jsou stejné konfigurace."],
         [0], f"Reflexivní a tranzitivní uzávěr relace ⊢ℳ. Chytil, s. 262. {P}"),
        ("Jak vypadá počáteční konfigurace Turingova stroje?",
         ["q₀w, kde w ∈ (Σ − {Λ})*: hlava na začátku vstupu, stav q₀.",
          "wq₀: hlava za koncem vstupního slova.",
          "uqv s libovolným q ∈ F.",
          "q₀ na úplně prázdné pásce; vstupní slovo se na pásku načte až během výpočtu."],
         [0], f"Chytil, s. 262 (ověřeno podle skenu). {P}"),
        ("Jak vypadá koncová konfigurace Turingova stroje?",
         ["uqv, kde u, v ∈ Σ* a q ∈ F.",
          "q₀w, kde w ∈ (Σ − {Λ})*.",
          "uqv s prázdnou páskou a libovolným q.",
          "uqv, kde v je prázdné slovo a q ∈ Q − F."],
         [0], f"Chytil, s. 262 (ověřeno podle skenu). {P}"),
        ("Kdy Turingův stroj ℳ přijímá slovo w?",
         ["Když q₀w ⊢* uqv pro nějakou koncovou konfiguraci, q ∈ F.",
          "Když po přečtení slova w zůstane páska úplně prázdná.",
          "Když hlava přečte celé slovo w zleva doprava až na konec.",
          "Když se výpočet zastaví, v libovolném stavu z Q."],
         [0], f"L(ℳ) = {{w ∈ (Σ − {{Λ}})*; q₀w ⊢* uqv, q ∈ F}}. Chytil, s. 262. {P}"),
    ]
    TSZ = ("Turingův stroj z přednášky: Q = {q₀, q₁, q_f}, Σ = {a, b, Λ}, F = {q_f}, "
           "pravidla (1) δ(q₀, a) = (q₁, b, +1), (2) δ(q₁, b) = (q_f, b, −1).")
    out, ok = ts_run("abb")
    conf = [cs(c) for c in out]
    inputs = [
        ("Konfigurace K = ab q cd (u = a, y = b, x = c, v = d) a δ(q, c) = (p, z, +1). "
         "Napiš konfiguraci bezprostředně následující po K.", "konfigurace bez mezer, např. abqcd", "abzpd",
         f"uyx′q′v = a b z p d: c přepsáno na z, hlava doprava na d. Chytil, Def. 6.1.4. Ověřeno výpočtem. {P}"),
        ("Konfigurace K = ab q cd (u = a, y = b, x = c, v = d) a δ(q, c) = (p, z, −1). "
         "Napiš konfiguraci bezprostředně následující po K.", "konfigurace bez mezer, např. abqcd", "apbzd",
         f"uq′yx′v = a p b z d: c přepsáno na z, hlava doleva na b. Chytil, Def. 6.1.4. Ověřeno výpočtem. {P}"),
        (f"{TSZ} Napiš konfiguraci po prvním kroku z počáteční konfigurace q₀abb.",
         "konfigurace bez mezer, stav jako q0, q1, qf", conf[1],
         f"q₀abb ⊢ bq₁bb: a přepsáno na b, stav q₁, hlava doprava. Ověřeno simulací. {P}"),
        (f"{TSZ} Napiš konfiguraci, ve které výpočet nad abb skončí.",
         "konfigurace bez mezer, stav jako q0, q1, qf", conf[-1],
         f"q₀abb ⊢ bq₁bb ⊢ q_f bbb: v q₁ se b přepíše na b, stav q_f, hlava doleva. Ověřeno simulací. {P}"),
        (f"{TSZ} Přijme stroj slovo abb?", YN, "ano" if ok else "ne",
         f"Ano: výpočet skončí v q_f ∈ F (koncová konfigurace q_f bbb); z q_f už δ definovaná není. "
         f"Ověřeno simulací. {P}"),
    ]
    check(conf == ["q0abb", "bq1bb", "qfbbb"] and inputs[4][2] == "ano")
    reveal = [
        ("Vysvětli, proč je v definici Turingova stroje δ: (Q − F) × Σ → Q × Σ × {−1, +1} právě Q − F "
         "(otázka ke zkoušce).",
         "δ je definována jen pro nekoncové stavy; pro q ∈ F žádné δ(q, x) neexistuje. Když stroj vstoupí do "
         "koncového stavu, nemá jak pokračovat a výpočet skončí; tím je slovo přijato.\n"
         "Proč to je potřeba: stroj se může pohybovat oběma směry a páska nemá konec, takže výpočet sám od sebe "
         "skončit nemusí. Koncový stav je signál „hotovo, přijato“.\n"
         f"Chytil, s. 268: „Podle definice 6.1.1 není z takového stavu další přechod definován, a výpočet proto "
         f"v okamžiku přijetí končí.“ {P}"),
        (f"{TSZ} Zapiš výpočet nad abb krok po kroku a u každého kroku vysvětli, co stroj udělá.",
         "q₀abb ⊢ bq₁bb ⊢ q_f bbb\n"
         "Krok 1 (pravidlo 1): stav q₀, hlava na a; přepíše a → b, stav q₁, posun doprava (+1): uyx′q′v.\n"
         "Krok 2 (pravidlo 2): stav q₁, hlava na b; přepíše b → b (symbol zůstane, ale přepsat se musí), "
         "stav q_f, posun doleva (−1): uq′yx′v.\n"
         f"q_f ∈ F, takže q_f bbb je koncová konfigurace a abb je přijato. Ověřeno simulací. {P}"),
    ]
    return [("choice", choice), ("input", inputs), ("reveal", reveal)]


def write(groups, prefix, name, title, seed):
    qs, longest = build(groups, random.Random(seed), prefix)
    for i, q in enumerate(qs, 1):
        q["number"], q["id"] = i, f"{prefix}-{i}"
    other = {q["id"] for p in (HERE / "banky").glob("*.json") if p.name != name
             for q in json.loads(p.read_text(encoding="utf-8"))["questions"]}
    check(not {q["id"] for q in qs} & other, "id otázek musí být unikátní napříč přednáškami")
    path = HERE / "banky" / name
    path.write_text(json.dumps({"title": title, "lecture": 9, "date": "2026-11-26", "questions": qs},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter("reveal" if q.get("reveal") else q["type"] for q in qs)
    print(f"{name}: {len(qs)} otázek ({c['choice']} výběrových, {c['input']} na výsledek, {c['reveal']} na rozbor), "
          f"správná nejdelší {longest}×")


def main():
    verify()
    write(za_bank(), "9", "09-2026-11-26.json", "Zásobníkové automaty a bezkontextové jazyky", 1126)
    write(ts_bank(), "9t", "09t-turinguv-stroj.json", "Turingův stroj", 11262)
    print(f"kontrol (assert): {CHECKS}")


if __name__ == "__main__":
    main()
