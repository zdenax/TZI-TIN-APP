#!/usr/bin/env python3
"""Vygeneruje banku otázek pro 3. přednášku (množiny, podmnožiny, relace) do banky/.

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z autorových poznámek z přednášky 15. 10. 2026 a z učebního textu Přibyl, Tichá (kap. 4).
Příklady na výsledek se počítají zde (ne ručně). Teoretické části doplněné AI (doplněk, spočetnost) je třeba kontrolovat proti přednášce a sylabu KI/TIN.
Spuštění:  python3 build_bank_3.py
"""
import itertools
import json
import random
from pathlib import Path

# (text, [možnosti], [správné indexy], vysvětlení); správná odpověď je vždy první možnost, pořadí se zamíchá
CHOICE = [
    ("Jak se v zápisu značí množiny a jak jejich prvky?",
     ["množiny velkými písmeny, prvky malými", "množiny malými písmeny, prvky velkými",
      "množiny i prvky velkými písmeny", "množiny řeckými písmeny, prvky číslicemi"], [0],
     "Množiny zadáváme velkými písmeny (A, M, X), jejich prvky malými (a, b, c)."),
    ("Jaké závorky se používají při výčtu prvků množiny, např. M = {a, b, c}?",
     ["složené", "kulaté", "hranaté", "lomené"], [0],
     "Množina má složené závorky. Kulaté závorky patří uspořádané dvojici (x, y)."),
    ("Co říká zápis d ∉ M, kde M = {a, b, c}?",
     ["d není prvkem množiny M", "d je podmnožinou M", "d je prvkem M", "d je rovno M"], [0],
     "∉ čteme „není prvkem“. M obsahuje jen a, b, c."),
    ("Kdy je výčet prvků vhodný způsob zadání množiny?",
     ["pro konečné množiny, jejichž prvky nemají společnou vlastnost", "pro každou nekonečnou množinu",
      "jen pro prázdnou množinu", "nikdy"], [0],
     "Výčet {a₁, a₂, …, aₙ} se hodí pro konečné množiny; jinak se zadává vlastností {x ; P(x)}."),
    ("Co znamená zápis {x ; P(x)}?",
     ["množina všech x, která mají vlastnost P", "množina, která obsahuje právě jedno x",
      "množina všech x, pro něž P neplatí", "dvojice (x, P)"], [0],
     "Zadání vlastností: do množiny patří právě ta x, pro něž platí P(x)."),
    ("Jak se definuje podmnožina (inkluze) X ⊆ Y?",
     ["a ∈ X ⇒ a ∈ Y", "a ∈ X ∧ a ∈ Y", "a ∈ X ∨ a ∈ Y", "a ∈ X ⇔ a ∈ Y"], [0],
     "Podmnožina = inkluze: každý prvek množiny X leží i v Y. Zápis: X ⊆ Y ⇔ (a ∈ X ⇒ a ∈ Y)."),
    ("Kdy NEPLATÍ X ⊆ Y?",
     ["když existuje prvek a ∈ X, který není v Y",
      "když existuje prvek a ∈ Y, který není v X",
      "když X a Y nemají žádný společný prvek",
      "když X a Y mají stejné prvky"], [0],
     "X ⊆ Y je porušeno jen prvkem a ∈ X, a ∉ Y, v tabulce řádek x = 1, y = 0. Proto implikace x ⇒ y. "
     "Prvek, který v X není, nic neporušuje."),
    ("Proč se podmnožina (inkluze) X ⊆ Y definuje implikací a ne konjunkcí? (x: a ∈ X, y: a ∈ Y; řádky x,y = 11, 10, 01, 00)",
     ["x ∧ y dává 1, 0, 0, 0, ale pro prvky mimo X (řádky 01 a 00) má být X ⊆ Y splněno, tedy 1",
      "x ∧ y dává 1 i v řádku 10, ačkoli ten X ⊆ Y porušuje",
      "x ∧ y dává 0 v řádku 11, ačkoli tam X ⊆ Y platí",
      "x ∧ y se pro prvky mimo X nedá spočítat"], [0],
     "X ⊆ Y porušuje jen prvek v X, který není v Y (řádek 10). Prvek mimo X (řádky 01 a 00) nic neporušuje, "
     "takže tam má být 1. Konjunkce tam dává 0, jen implikace dává 0 právě v řádku 10."),
    ("Proč se podmnožina (inkluze) X ⊆ Y definuje implikací a ne disjunkcí? (x: a ∈ X, y: a ∈ Y; řádky x,y = 11, 10, 01, 00)",
     ["x ∨ y dává 1, 1, 1, 0: v řádku 10, který X ⊆ Y porušuje, je 1, a v řádku 00, kde nic neporušuje X ⊆ Y, je 0",
      "x ∨ y dává 0 v řádku 10, ačkoli ten X ⊆ Y neporušuje",
      "x ∨ y dává 0 v řádku 11, ačkoli tam X ⊆ Y platí",
      "x ∨ y dává 1 v řádku 00, ačkoli tam X ⊆ Y neplatí"], [0],
     "X ⊆ Y porušuje jen řádek 10, tam má být 0, a ostatní řádky mají být 1. Disjunkce dává 1 v řádku 10 "
     "a 0 v řádku 00, tedy obojí naopak. Jen implikace dává 1, 0, 1, 1."),
    ("Jaký je rozdíl mezi X ⊆ Y a X ⊂ Y (vlastní podmnožina)?",
     ["⊂ vyžaduje navíc X ≠ Y, ⊆ rovnost připouští", "⊆ vyžaduje X ≠ Y, ⊂ rovnost připouští",
      "žádný, jsou to dva zápisy téhož", "⊂ se používá jen pro konečné množiny"], [0],
     "X ⊂ Y ⇔ X ⊆ Y ∧ X ≠ Y. Podmnožina připouští rovnost, vlastní podmnožina ne."),
    ("Jak se dokáže rovnost množin A = B?",
     ["A ⊆ B a zároveň B ⊆ A", "stačí A ⊆ B", "stačí A ∩ B ≠ ∅", "stačí |A| = |B|"], [0],
     "A = B ⇔ (x ∈ A ⇒ x ∈ B) ∧ (x ∈ B ⇒ x ∈ A)."),
    ("Která množina je prázdná?",
     ["∅, neobsahuje žádný prvek", "{∅}", "{0}", "ℕ"], [0],
     "Prázdná množina ∅ nemá žádný prvek. {∅} má jeden prvek (prázdnou množinu), {0} má prvek 0."),
    ("Které z množin ℕ, ℤ, ℝ jsou nekonečné?",
     ["všechny tři", "jen ℝ", "jen ℕ", "žádná"], [0],
     "ℕ, ℤ i ℝ jsou nekonečné (příklady z rukopisu)."),
    ("Kdy je množina spočetná?",
     ["její prvky jdou očíslovat přirozenými čísly a seřadit do posloupnosti a₁, a₂, a₃, …", "má konečný počet prvků",
      "neobsahuje žádný prvek", "je podmnožinou ℝ"], [0],
     "Spočetná: prvky jdou očíslovat přirozenými čísly, tedy seřadit do posloupnosti a₁, a₂, a₃, … "
     "(Pozor, někteří autoři zahrnují mezi spočetné i konečné množiny; ověřit u vyučujícího.)"),
    ("Která z množin je nekonečná, ale nespočetná?",
     ["ℝ", "ℕ", "ℤ", "{1, 2, 3}"], [0],
     "ℝ (i interval (0, 1)) nelze očíslovat přirozenými čísly (Cantorův diagonální argument). ℕ a ℤ jsou spočetné."),
    ("Jaký je vztah pojmů „spočetná“ a „nekonečná“ množina?",
     ["každá spočetná množina je nekonečná, ale ne každá nekonečná je spočetná",
      "každá nekonečná množina je spočetná", "jsou to synonyma", "spočetná množina je vždy konečná"], [0],
     "„Nekonečná“ říká jen, že prvků není konečně mnoho. „Spočetná“ říká, že je lze očíslovat přirozenými čísly. ℝ je nekonečná, ale nespočetná."),
    ("Co je průnik A ∩ B?",
     ["množina prvků, které patří do A i do B", "množina prvků, které patří do A nebo do B",
      "prvky A, které nejsou v B", "množina všech dvojic (a, b)"], [0],
     "x ∈ A ∩ B ⇔ x ∈ A ∧ x ∈ B."),
    ("Co je sjednocení A ∪ B?",
     ["množina prvků, které patří do A nebo do B", "množina prvků, které patří do A i do B",
      "prvky A, které nejsou v B", "množina všech podmnožin"], [0],
     "x ∈ A ∪ B ⇔ x ∈ A ∨ x ∈ B."),
    ("Co je rozdíl A ∖ B?",
     ["prvky, které leží v A a neleží v B", "prvky, které leží v B a neleží v A", "prvky, které leží v A i v B",
      "prvky, které neleží ani v A, ani v B"], [0],
     "x ∈ A ∖ B ⇔ x ∈ A ∧ x ∉ B."),
    ("Platí vždy A ∖ B = B ∖ A?",
     ["ne, obecně ne", "ano, vždy", "ano, pokud A ≠ B", "ano, pokud A ∩ B = ∅"], [0],
     "Např. A = {a, b}, B = {b}: A ∖ B = {a}, ale B ∖ A = ∅."),
    ("Co je univerzum U?",
     ["množina všech uvažovaných prvků; každá množina, se kterou pracujeme, je jeho podmnožinou",
      "prázdná množina", "množina všech množin", "největší konečná množina"], [0],
     "A ⊆ U pro každou uvažovanou množinu A. (Slovní vysvětlení je doplněno z Claude, ověřit u vyučujícího.)"),
    ("Jak se definuje doplněk A′ množiny A vzhledem k univerzu U?",
     ["x ∈ A′ ⇔ x ∈ U ∧ x ∉ A", "x ∈ A′ ⇔ x ∈ A ∧ x ∈ U", "x ∈ A′ ⇔ x ∈ A ∨ x ∉ U", "A′ = A ∖ U"], [0],
     "Doplněk jsou prvky univerza, které do A nepatří: A′ = U ∖ A. (Značení v rukopisu nejasné: A′ nebo Ā; definice doplněná z Claude.)"),
    ("Čemu se rovná A ∩ A′ a A ∪ A′?",
     ["A ∩ A′ = ∅ a A ∪ A′ = U", "A ∩ A′ = U a A ∪ A′ = ∅", "obojí A", "obojí U"], [0],
     "Z definice doplňku: žádný prvek není zároveň v A a mimo A (∅), a každý prvek univerza je buď v A, nebo v A′ (U)."),
    ("Kdy jsou množiny A, B disjunktní?",
     ["A ∩ B = ∅", "A ∪ B = ∅", "A ⊆ B", "A = B"], [0],
     "Disjunktní množiny nemají žádný společný prvek."),
    ("Co je potenční množina Pot(A) (značí se i P(A))?",
     ["množina všech podmnožin množiny A", "množina všech prvků množiny A",
      "množina všech vlastních podmnožin bez ∅", "A × A"], [0],
     "P(A) = {B ; B ⊆ A}. Vždy obsahuje ∅ i samotnou A."),
    ("Kolik prvků má potenční množina množiny o n prvcích?",
     ["2ⁿ", "n²", "2n", "n!"], [0],
     "|Pot(A)| = 2ⁿ. Pro A = {a, b, c} je to 2³ = 8 podmnožin."),
    ("Jak vypadá Pot({a, b})?",
     ["{∅, {a}, {b}, {a, b}}", "{{a}, {b}}", "{∅, {a, b}}", "{a, b}"], [0],
     "Pot({a, b}) = {∅, {a}, {b}, {a, b}}, tj. 2² = 4 prvky; prvky potenční množiny jsou množiny, ne a, b."),
    ("Co je kartézský součin A × B?",
     ["množina všech uspořádaných dvojic (x, y), kde x ∈ A a y ∈ B", "množina prvků společných A a B",
      "množina všech podmnožin A a B", "A ∪ B"], [0],
     "A × B = {(x, y) ; x ∈ A ∧ y ∈ B}."),
    ("Co je uspořádaná dvojice (x, y)?",
     ["dvojice, u které záleží na pořadí; píše se do kulatých závorek", "dvojice, u které na pořadí nezáleží",
      "množina {x, y}", "dvojice s x < y"], [0],
     "x je první složka, y druhá. Množina {x, y} = {y, x}, ale (x, y) ≠ (y, x) pro x ≠ y."),
    ("Kdy platí (x, y) = (u, v)?",
     ["když x = u a zároveň y = v", "když x = v a y = u", "když {x, y} = {u, v}", "když x = u nebo y = v"], [0],
     "Dvě uspořádané dvojice se rovnají, jen když se rovnají obě složky ve stejném pořadí."),
    ("Platí obecně A × B = B × A?",
     ["ne, obecně ne", "ano, vždy", "ano, jen když |A| = |B|", "ano, jen pro disjunktní množiny"], [0],
     "(x, y) ≠ (y, x) pro x ≠ y, proto A × B ≠ B × A (rovnost jen např. když A = B nebo je některá z nich prázdná)."),
    ("Kolik prvků má kartézský součin A × B pro konečné množiny?",
     ["|A| · |B|", "|A| + |B|", "2^(|A|+|B|)", "|A|^|B|"], [0],
     "|A × B| = |A| · |B|, např. 2 · 3 = 6."),
    ("Co je relace mezi prvky množin A a B?",
     ["podmnožina kartézského součinu A × B", "prvek množiny A × B", "průnik A a B", "libovolná funkce A → B"], [0],
     "Relace R ⊆ A × B; pravidlo, které u každé uspořádané dvojice (x, y) určí, zda je v relaci či nikoli. (Dokončení věty z rukopisu doplněno z Claude.)"),
    ("Kdy je relace R na množině A reflexivní?",
     ["∀x ∈ A; xRx", "∀x, y ∈ A; xRy ⇒ yRx", "∀x ∈ A; ¬(xRx)", "∃x ∈ A; xRx"], [0],
     "Reflexivní: každý prvek je v relaci sám se sebou. Příklad: x = x."),
    ("Kdy je relace R na množině A symetrická?",
     ["∀x, y ∈ A; xRy ⇒ yRx", "∀x ∈ A; xRx", "∀x, y ∈ A; xRy ∧ yRx ⇒ x = y", "∀x, y, z ∈ A; xRy ∧ yRz ⇒ xRz"], [0],
     "Symetrická: obrátí-li se dvojice, zůstane v relaci. Příklad: x = y ⇒ y = x."),
    ("Kdy je relace R na množině A tranzitivní?",
     ["∀x, y, z ∈ A; xRy ∧ yRz ⇒ xRz", "∀x, y ∈ A; xRy ⇒ yRx", "∀x ∈ A; xRx", "∀x, y ∈ A; xRy ∧ yRx ⇒ x = y"], [0],
     "Tranzitivní: z xRy a yRz plyne xRz. Příklady z rukopisu: =, >."),
    ("Kdy je relace R na množině A (slabě) antisymetrická?",
     ["∀x, y ∈ A; xRy ∧ yRx ⇒ x = y", "∀x, y ∈ A; xRy ⇒ yRx", "∀x, y ∈ A; xRy ⇒ ¬(yRx)", "∀x ∈ A; ¬(xRx)"], [0],
     "Slabá antisymetrie (zápis z rukopisu): xRy ∧ yRx ⇒ x = y, např. ≤ nebo dělitelnost na ℕ. Silná: xRy ⇒ ¬(yRx), např. < na ℕ."),
    ("Která relace je relace ekvivalence?",
     ["symetrická, reflexivní a tranzitivní (na stejné množině)", "tranzitivní a antisymetrická",
      "jen symetrická", "reflexivní a antisymetrická"], [0],
     "Ekvivalence = reflexivní + symetrická + tranzitivní. Příklad: stejný zbytek po dělení 3 na ℕ."),
    ("Která z relací na ℕ je ekvivalence?",
     ["xRy ⇔ x a y mají stejný zbytek po dělení 3", "xRy ⇔ x < y", "xRy ⇔ x ≤ y", "xRy ⇔ x dělí y a x ≠ y"], [0],
     "Stejný zbytek po dělení 3 je reflexivní, symetrická i tranzitivní. <, ≤ a dělitelnost nejsou symetrické."),
    ("Co znamená, že relace R je antireflexivní?",
     ["žádný prvek není v relaci sám se sebou", "každý prvek je v relaci sám se sebou",
      "některý prvek je v relaci sám se sebou", "relace je prázdná"], [0],
     "∀x; ¬(xRx). Příklad: < na ℕ. Pozor, antireflexivní není totéž co „není reflexivní“."),
]

POOL = "abcdefgh"


def pick_sets(rnd, size_a, size_b, common):
    """Dvě množiny z písmen se zadaným počtem společných prvků."""
    letters = rnd.sample(POOL, size_a + size_b - common)
    a = sorted(letters[:size_a])
    b = sorted(letters[size_a - common:])
    assert len(set(a) & set(b)) == common
    return a, b


def fmt(s):
    return "{" + ",".join(s) + "}" if s else "∅"


def set_questions(rnd):
    qs = []
    hint = "napiš prvky abecedně bez čárek a mezer, např. ace"
    for kind in ("∩", "∪", "∖", "∖"):
        a, b = pick_sets(rnd, rnd.choice((3, 4)), rnd.choice((3, 4)), rnd.choice((1, 2)))
        sa, sb = set(a), set(b)
        res = {"∩": sa & sb, "∪": sa | sb, "∖": sa - sb}[kind]
        name = {"∩": "průnik", "∪": "sjednocení", "∖": "rozdíl"}[kind]
        sol = f"A = {fmt(a)}, B = {fmt(b)}\nA {kind} B = {fmt(sorted(res))} ({name})"
        qs.append({"type": "input", "text": f"Urči A {kind} B pro A = {fmt(a)}, B = {fmt(b)}.", "hint": hint,
                   "answer": "".join(sorted(res)), "solution": sol})
    # doplněk
    u = list("12345678")[:rnd.choice((5, 6))]
    a = sorted(rnd.sample(u, rnd.choice((2, 3))))
    comp = [x for x in u if x not in a]
    assert set(comp) | set(a) == set(u) and not set(comp) & set(a)
    qs.append({"type": "input", "text": f"Urči doplněk A′ vzhledem k univerzu U = {fmt(u)} pro A = {fmt(a)}.",
               "hint": "napiš prvky vzestupně bez čárek a mezer, např. 135",
               "answer": "".join(comp), "solution": f"A′ = U ∖ A = {fmt(comp)} (prvky U, které nejsou v A)"})
    # velikosti
    for n in (3, 4, 5):
        subsets = [c for r in range(n + 1) for c in itertools.combinations(range(n), r)]
        assert len(subsets) == 2 ** n
        qs.append({"type": "input", "text": f"Kolik podmnožin má množina o {n} prvcích (tj. |Pot(A)|, kde |A| = {n})?",
                   "hint": "číslo", "answer": str(len(subsets)), "solution": f"|Pot(A)| = 2^{n} = {2 ** n}"})
    for m, n in ((2, 3), (3, 4), (4, 5)):
        prod = list(itertools.product(range(m), range(n)))
        qs.append({"type": "input", "text": f"Kolik prvků má A × B, když |A| = {m} a |B| = {n}?", "hint": "číslo",
                   "answer": str(len(prod)), "solution": f"|A × B| = |A| · |B| = {m} · {n} = {len(prod)}"})
    return qs


def rel_props(r, m):
    refl = all((x, x) in r for x in m)
    sym = all((y, x) in r for x, y in r)
    trans = all((x, w) in r for x, y in r for z, w in r if y == z)
    anti = all(x == y for x, y in r if (y, x) in r)
    return refl, sym, trans, anti


def relation_questions():
    qs = []
    cases = [
        ([(1, 1), (2, 2), (3, 3), (1, 2), (2, 1)], [1, 2, 3]),
        ([(1, 1), (2, 2), (3, 3), (1, 2), (2, 3), (1, 3)], [1, 2, 3]),
        ([(1, 2), (2, 3), (1, 3)], [1, 2, 3]),
        ([(1, 1), (2, 1), (1, 2), (2, 3), (3, 4), (4, 3), (4, 4), (5, 5)], [1, 2, 3, 4, 5]),
        ([(1, 1), (2, 2), (3, 3)], [1, 2, 3]),
        ([(1, 2), (2, 1)], [1, 2]),
    ]
    yn = lambda v: "ano" if v else "ne"
    for pairs, m in cases:
        r = set(pairs)
        props = rel_props(r, m)
        a = "".join(str(int(v)) for v in props)
        rs = "{" + ", ".join(f"({x},{y})" for x, y in pairs) + "}"
        ms = "{" + ",".join(map(str, m)) + "}"
        sol = (f"reflexivní: {yn(props[0])}\nsymetrická: {yn(props[1])}\ntranzitivní: {yn(props[2])}\n"
               f"(slabě) antisymetrická: {yn(props[3])}\nOdpověď: {a}")
        qs.append({"type": "input",
                   "text": f"Relace R = {rs} na M = {ms}. Zjisti, zda je reflexivní, symetrická, tranzitivní a (slabě) antisymetrická. Výsledek napiš jako čtyři cifry v tomto pořadí.",
                   "hint": "1 = ano, 0 = ne; pořadí reflexivní, symetrická, tranzitivní, antisymetrická, např. 1010",
                   "answer": a, "solution": sol})
    # ověření tvrzení, na kterých stojí výběrové otázky (skript spadne, kdyby neplatila)
    z = range(-3, 4)
    eq = {(x, y) for x in z for y in z if x == y}
    gt = {(x, y) for x in z for y in z if x > y}
    le = {(x, y) for x in z for y in z if x <= y}
    assert rel_props(eq, z) == (True, True, True, True)
    assert rel_props(gt, z) == (False, False, True, True)
    assert rel_props(le, z) == (True, False, True, True)
    m12 = range(1, 13)
    mod3 = {(x, y) for x in m12 for y in m12 if x % 3 == y % 3}
    assert rel_props(mod3, m12)[:3] == (True, True, True)
    m5 = range(1, 6)
    lt = {(x, y) for x in m5 for y in m5 if x < y}
    assert rel_props(lt, m5) == (False, False, True, True) and not any((x, x) in lt for x in m5)
    # podmnožina: implikace dává 0 právě v řádku (1,0), ∧ a ∨ ne
    rows = list(itertools.product((1, 0), repeat=2))
    assert [int((not x) or y) for x, y in rows] == [1, 0, 1, 1]
    assert [int(x and y) for x, y in rows] != [1, 0, 1, 1]
    assert [int(x or y) for x, y in rows] != [1, 0, 1, 1]
    return qs


def main():
    rnd = random.Random(7)  # pevné pořadí, aby správná odpověď nebyla pořád A
    qs = []
    for text, opts, correct, expl in CHOICE:
        order = list(range(len(opts)))
        rnd.shuffle(order)
        opts = [opts[i] for i in order]
        correct = sorted(order.index(c) for c in correct)
        qs.append({"type": "choice", "text": text,
                   "options": {"ABCD"[i]: o for i, o in enumerate(opts)},
                   "correct": ["ABCD"[i] for i in correct], "explanation": expl})
    qs += set_questions(random.Random(11))
    qs += relation_questions()
    # uspořádaná dvojice se musí vysvětlit dřív než kartézský součin, který z ní vychází
    assert qs[27]["text"].startswith("Co je kartézský součin") and qs[28]["text"].startswith("Co je uspořádaná dvojice")
    qs[27], qs[28] = qs[28], qs[27]
    for i, q in enumerate(qs, 1):
        q["number"] = i
        q["id"] = f"3-{i}"
    out = {"title": "Množiny, podmnožiny (inkluze) a relace", "lecture": 3, "date": "2026-10-15", "questions": qs}
    path = Path(__file__).parent / "banky" / "03-2026-10-15.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_c = sum(q["type"] == "choice" for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({n_c} výběrových, {len(qs) - n_c} na výsledek)")


if __name__ == "__main__":
    main()
