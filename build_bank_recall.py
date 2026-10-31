#!/usr/bin/env python3
"""Vygeneruje banku pro režim „Doplňovačka (na paměť)“ do banky/doplnovacka/.

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Opus 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Otázky typu recall: odpověď se píše z hlavy, bez možností ABCD. accept = uznávané varianty
(první je kanonická), words = očekávaný počet slov kanonické odpovědi (číslo nebo "1-2"),
category = tematická kategorie napříč přednáškami. Velká/malá písmena, diakritiku a interpunkci
sjednocuje UI, proto se varianty bez diakritiky nepíšou zvlášť.
Obsah vychází z výpisků přednášek 1 až 5 (vault TZI1: Prednasky/*.md, Glosar.md) a z bank 1 až 5.
Kde se zdroje liší (podílová × faktorová množina, spočetná × spočetně nekonečná, slabá
antisymetrie, neostré uspořádání), uznávají se obě varianty. Teorii kontrolovat proti sylabu KI/TIN.
Banka je v podsložce, běžné režimy (banky/*.json) ji vůbec nenačtou.
Spuštění:  python3 build_bank_recall.py
"""
import json
from itertools import combinations_with_replacement, permutations, product
from math import comb, factorial
from pathlib import Path


def q(text, accept, words, explanation):
    return {"text": text, "accept": accept, "words": words, "explanation": explanation}


P1, P2, P3, P4 = "Přednáška 1. 10.", "Přednáška 8. 10.", "Přednáška 15. 10.", "Přednáška 22. 10."
P5 = "Přednáška 29. 10."
BINOM3 = [comb(3, k) for k in range(4)]  # koeficienty (a+b)^3
AUT_STATES, AUT_SYMBOLS = 4, 2  # automat z přednášky 29. 10.: Q = {q0, q1, q2, q3}, Σ = {0, 1}

CATS = [
    ("Matematický zápis", [
        q("Co označuje symbol ℕ?", ["přirozená čísla", "přirozená", "množina přirozených čísel",
          "obor přirozených čísel", "natural numbers"], 2,
          f"ℕ jsou přirozená čísla (na přednášce 0, 1, 2, 3, …). Platí ℕ ⊂ ℤ ⊂ ℚ ⊂ ℝ ⊂ ℂ. {P1}"),
        q("Co označuje symbol ℤ?", ["celá čísla", "celá", "množina celých čísel", "obor celých čísel",
          "integers"], 2, f"ℤ jsou celá čísla (…, −2, −1, 0, 1, 2, …). {P1}"),
        q("Co označuje symbol ℚ?", ["racionální čísla", "racionální", "množina racionálních čísel",
          "obor racionálních čísel", "zlomky", "rational numbers"], 2,
          f"ℚ jsou racionální čísla (ve výpiscích „zlomky“, např. 1/2, −3/4, 5). {P1}"),
        q("Co označuje symbol ℝ?", ["reálná čísla", "reálná", "množina reálných čísel", "obor reálných čísel",
          "real numbers"], 2, f"ℝ jsou reálná čísla, všechna čísla na ose, i √2 a π. {P1}"),
        q("Co označuje symbol ℂ?", ["komplexní čísla", "komplexní", "množina komplexních čísel",
          "obor komplexních čísel", "complex numbers"], 2, f"ℂ jsou komplexní čísla tvaru a + ib. {P1}"),
        q("Jak se nazývá n! = 1 · 2 · 3 · … · n?", ["faktoriál", "n faktoriál", "faktoriál n", "factorial"], 1,
          f"n! je faktoriál, 0! = 1. {P1}"),
        q("Kolik je 0! (nula faktoriál)?", [str(factorial(0)), "jedna"], 1, f"0! = 1. {P1}"),
        q("Co znamená symbol Σ v zápisu Σ_(i=1)^n a_i?", ["součet", "suma", "sumace", "sum"], 1,
          f"Σ_(i=1)^n a_i = a_1 + a_2 + … + a_n je součet. {P1}"),
        q("Co znamená symbol Π v zápisu Π_(i=1)^n a_i?", ["součin", "produkt", "product"], 1,
          f"Π_(i=1)^n a_i = a_1 · a_2 · … · a_n je součin. {P1}"),
        q("Jak se nazývá |x|, např. |−5| = 5?", ["absolutní hodnota", "absolutní hodnota x", "absolute value"], 2,
          f"|5| = 5 a |−5| = 5: absolutní hodnota. {P1}"),
    ]),
    ("Číselné soustavy", [
        q("Jak se nazývá číselná soustava, která není charakterizovaná základem (např. římská)?",
          ["nepoziční", "nepoziční soustava", "nepoziční číselná soustava"], 1,
          f"Soustavy jsou poziční (mají základ Z > 1) a nepoziční (základ nemají), např. římská. {P1}"),
        q("Uveď příklad nepoziční číselné soustavy.", ["římská", "římská soustava", "římská číselná soustava",
          "římské číslice", "římská čísla"], 1, f"Římská soustava (I, II, III, IV, V, VI, …) je nepoziční. {P1}"),
        q("Jak se nazývá číslo Z > 1, které charakterizuje poziční soustavu?", ["základ", "základ soustavy",
          "základ číselné soustavy", "báze", "radix", "base"], 1,
          f"Základ Z udává maximální počet číslic, které jsou v soustavě k dispozici. {P1}"),
        q("Jak se nazývají znaky, ze kterých se tvoří čísla dané soustavy?", ["číslice", "cifry", "cifra",
          "číslice soustavy", "digits", "digit"], 1,
          f"Čísla se tvoří z uspořádaných souborů znaků, které se nazývají číslice (cifry). {P1}"),
        q("Jak se jinak nazývá osmičková soustava?", ["oktalová", "oktalová soustava", "oktální",
          "oktální soustava", "octal"], 1, f"Z = 8, číslice 0 až 7: osmičková (oktalová). {P1}"),
        q("Jak se jinak nazývá desítková soustava?", ["dekadická", "dekadická soustava", "decimální",
          "decimální soustava", "decimal"], 1, f"Z = 10, číslice 0 až 9: desítková (dekadická). {P1}"),
        q("Jak se jinak nazývá šestnáctková soustava?", ["hexadecimální", "hexadecimální soustava", "hexa",
          "hex", "hexadecimal"], 1, f"Z = 16, číslice 0 až 9 a A až F: šestnáctková (hexadecimální). {P1}"),
        q("Jakou hodnotu má hexadecimální číslice F (v desítkové soustavě)?", [str(int("F", 16)), "patnáct"], 1,
          f"A = 10, B = 11, C = 12, D = 13, E = 14, F = 15. {P1}"),
        q("Kolik bitů odpovídá jedné šestnáctkové (hexadecimální) číslici?", ["4", "čtyři", "4 bity",
          "čtyři bity"], 1, f"16 = 2^4, proto se při převodu 2 ↔ 16 dělí po čtveřicích bitů (váhy 8 4 2 1). {P1}"),
        q("Převod z desítkové soustavy opakovaným dělením základem: v jakém pořadí se čtou zbytky?",
          ["zdola nahoru", "odspodu nahoru", "zespodu nahoru", "odspoda nahoru", "zespoda nahoru",
           "od spodu nahoru", "v opačném pořadí", "pozpátku", "od posledního k prvnímu"], 2,
          f"Dělím celočíselně základem a zbytky čtu zdola nahoru, např. (26)_10 = (11010)_2. {P1}"),
        q("Přes kterou soustavu se ve výpiscích převádí osmičková soustava na šestnáctkovou?",
          ["dvojkovou", "dvojková", "přes dvojkovou", "dvojková soustava", "přes dvojkovou soustavu",
           "oklikou přes dvojkovou", "binární", "přes binární", "binární soustava", "přes binární soustavu"], "1-2",
          f"8 ↔ 16 oklikou přes dvojkovou: osmičkové číslice na trojice bitů, pak po čtveřicích zprava. {P1}"),
        q("Kolik je 1 + 1 ve dvojkové soustavě (výsledek zapiš dvojkově)?", [bin(1 + 1)[2:]], 1,
          f"1 + 1 = (10)_2: zapíšu 0 a 1 přenesu do vyššího řádu. {P1}"),
        q("Jak se nazývá jednička, kterou při sčítání 1 + 1 ve dvojkové soustavě posunu do vyššího řádu?",
          ["přenos", "carry"], 1, f"V tabulce sčítání je u 1 + 1 výsledek 0 a přenos 1. {P1}"),
    ]),
    ("Symboly a logika", [
        q("Co je to za symbol: ∨ ?", ["disjunkce", "OR", "nebo", "logické nebo", "logický součet",
          "logická disjunkce"], "1-2",
          f"x ∨ y je disjunkce, čteme „x nebo y“; pravdivá, když je pravdivý aspoň jeden výrok. {P2}"),
        q("Co je to za symbol: ∧ ?", ["konjunkce", "AND", "a", "a zároveň", "logické a", "logický součin",
          "logická konjunkce"], "1-2",
          f"x ∧ y je konjunkce, čteme „x a zároveň y“; pravdivá, když jsou pravdivé oba výroky. {P2}"),
        q("Co je to za symbol: ¬ ?", ["negace", "NOT", "ne", "není pravda, že", "logická negace", "non"], 1,
          f"¬x je negace, čteme „není pravda, že x“; obrací pravdivostní hodnotu. {P2}"),
        q("Co je to za symbol: ⇒ ?", ["implikace", "logická implikace", "jestliže … pak", "jestliže x pak y",
          "když … pak", "plyne", "z toho plyne", "implies"], 1,
          f"x ⇒ y je implikace, čteme „jestliže x, pak y“; nepravdivá jen pro x = 1, y = 0. {P2}"),
        q("Co je to za symbol: ⇔ ?", ["ekvivalence", "logická ekvivalence", "právě tehdy, když", "právě když",
          "tehdy a jen tehdy, když", "tehdy a jen tehdy", "iff"], 1,
          f"x ⇔ y je ekvivalence, čteme „x právě tehdy, když y“; pravdivá, když mají x a y stejnou hodnotu. {P2}"),
        q("Co je to za symbol: ∀ ?", ["obecný kvantifikátor", "pro každé", "pro všechna", "pro všechny",
          "velký kvantifikátor", "univerzální kvantifikátor", "for all"], 2,
          f"∀ je obecný (velký) kvantifikátor, čteme „pro každé / pro všechna“, např. ∀x ∈ ℝ; x² ≥ 0. {P2}"),
        q("Co je to za symbol: ∃ ?", ["existenční kvantifikátor", "existuje", "existuje aspoň jedno",
          "existuje alespoň jedno", "existuje aspoň jeden", "existuje alespoň jeden", "malý kvantifikátor",
          "exists", "there exists"], "1-2",
          f"∃ je existenční kvantifikátor, čteme „existuje (aspoň jedno)“, např. ∃x ∈ ℝ; x > 5. {P2}"),
        q("Co znamená zápis ∃! ?", ["existuje právě jedno", "existuje právě jeden", "existuje právě jedna",
          "existuje jediné", "existuje jediný", "existuje jediná", "kvantifikátor jednoznačné existence",
          "jednoznačná existence"], 3, f"∃! čteme „existuje právě jedno“, např. ∃! x ∈ ℝ; x = 5. {P2}"),
        q("Jak se nazývá ¬y ⇒ ¬x vzhledem k implikaci x ⇒ y?", ["obměna", "obměna implikace", "kontrapozice",
          "kontrapozice implikace"], 1,
          f"¬y ⇒ ¬x je obměna implikace x ⇒ y; obě mají vždy stejnou pravdivostní hodnotu. {P2}"),
        q("Jak se nazývá y ⇒ x vzhledem k implikaci x ⇒ y?", ["obrácení", "obrácení implikace",
          "obrácená implikace", "obrácená"], "1-2",
          f"y ⇒ x je obrácení (obrácená implikace); na rozdíl od obměny nemusí mít stejnou hodnotu jako x ⇒ y. {P2}"),
        q("Jak se nazývá výroková formule, která je po dosazení výroků jakýchkoli pravdivostních hodnot "
          "vždy pravdivá?", ["tautologie"], 1, f"Tautologie, např. x ∨ ¬x nebo (x ⇒ y) ≡ (¬y ⇒ ¬x). {P2}"),
        q("Jak se nazývá zápis z písmen, logických spojek a závorek, ze kterého se po dosazení výroků za "
          "písmena stane výrok?", ["výroková formule", "formule"], 2,
          f"Výroková formule, např. (x ∧ ¬y) ⇒ z. Neplést s výrokovou formou (věta s proměnnou). {P2}"),
        q("Jak se nazývá věta s proměnnou, např. V(x): x > 0, která se stane výrokem až po dosazení?",
          ["výroková forma", "forma"], 2,
          f"Výroková forma obsahuje proměnnou, značí se V(x), V(x, y). Neplést s výrokovou formulí. {P2}"),
        q("Jak se nazývá podmnožina definičního oboru výrokové formy V(x), pro jejíž prvky c je V(c) "
          "pravdivý výrok?", ["obor pravdivosti"], 2,
          "Obor pravdivosti (pro √x = 5 je to {25}). V definičním oboru stačí, aby V(c) byl výrok. "
          "Výpisky 8. 10."),
        q("Jak se nazývají pravidla ¬(x ∧ y) ≡ ¬x ∨ ¬y a ¬(x ∨ y) ≡ ¬x ∧ ¬y?", ["De Morganovy zákony",
          "De Morganův zákon", "De Morganova pravidla", "De Morganovo pravidlo", "De Morgan"], 3,
          "De Morganovy zákony: negace „a“ je „nebo“ z negací a naopak. První zákon byl úkol "
          "z přednášky 8. 10. (důkaz tabulkou)."),
    ]),
    ("Důkazy a výstavba matematiky", [
        q("Jak se nazývá důkaz implikace x ⇒ y řetězem implikací x ⇒ y₁, y₁ ⇒ y₂, …, yₙ ⇒ y?",
          ["přímý důkaz", "přímý", "přímo"], 2, f"Přímý důkaz: z předpokladu x se po krocích dojde k y. {P2}"),
        q("Jak se nazývá důkaz, při kterém místo x ⇒ y dokážeme ¬y ⇒ ¬x?", ["nepřímý důkaz", "nepřímý",
          "nepřímo", "důkaz obměnou", "obměnou", "důkaz kontrapozicí", "kontrapozicí"], 2,
          f"Nepřímý důkaz dokazuje obměnu ¬y ⇒ ¬x, která má stejnou pravdivostní hodnotu jako x ⇒ y. {P2}"),
        q("Jak se nazývá důkaz, při kterém předpokládáme x ∧ ¬y a odvodíme nepravdivé tvrzení Z?",
          ["důkaz sporem", "sporem", "spor", "reductio ad absurdum"], 2,
          f"Důkaz sporem: (x ∧ ¬y) ⇒ Z, kde Z je nepravda; předpoklad tedy neplatí a x ⇒ y platí. {P2}"),
        q("Jak se nazývá důkaz tvrzení pro všechna n ≥ n₀ pomocí základního a indukčního kroku?",
          ["matematická indukce", "indukce", "důkaz matematickou indukcí", "matematickou indukcí",
           "důkaz indukcí", "indukcí"], 2,
          f"Matematická indukce: ověří se φ(n₀) a dokáže se φ(k) ⇒ φ(k+1). {P3}"),
        q("Jak se v matematické indukci nazývá krok, ve kterém ověříme φ(n₀)?", ["základní krok", "základ",
          "základ indukce"], 2, f"Základní krok φ(n₀), potom indukční krok φ(k) ⇒ φ(k+1). {P3}"),
        q("Jak se v matematické indukci nazývá krok, ve kterém dokazujeme φ(k) ⇒ φ(k+1)?", ["indukční krok"], 2,
          f"Indukční krok: z platnosti φ(k) se dokáže φ(k+1). {P3}"),
        q("Jak se v matematické indukci nazývá předpoklad, že φ(k) platí pro nějaké pevné k?",
          ["indukční předpoklad"], 2,
          "Indukční předpoklad: φ(k) platí, z něj se v indukčním kroku dokáže φ(k+1). "
          "Výpisky 8. 10. (podle učebního textu Přibyl, Tichá)."),
        q("Co musíme dokázat, když dokazujeme ekvivalenci x ⇔ y?", ["obě implikace", "dvě implikace",
          "obě implikace x ⇒ y a y ⇒ x", "implikaci tam i zpět", "oba směry"], 2,
          f"(x ⇔ y) ⇔ (x ⇒ y) ∧ (y ⇒ x): dokazují se obě implikace. {P2}"),
        q("Jak se nazývá tvrzení, jehož platnost předpokládáme a nedokazujeme?", ["axiom"], 1,
          f"Na počátku logické výstavby matematiky jsou axiomy; předpokládáme, že platí. {P2}"),
        q("Jak se nazývá pojem z axiomů, který nedefinujeme (např. bod, přímka, čas)?", ["primitivní pojem",
          "primitivní pojmy", "primitivní"], 2, f"Primitivní pojmy se nedefinují, jsou výchozí. {P2}"),
        q("Jak se nazývá pravdivý výrok, který lze odvodit pravidly logiky z axiomů nebo z dříve dokázaných "
          "tvrzení?", ["věta", "matematická věta", "teorém"], 1,
          f"Věta je pravdivý výrok odvoditelný z axiomů nebo z vět již dokázaných; věty se zpravidla dokazují. {P2}"),
        q("Jak se nazývá věta, která se dokazuje, ale slouží spíš jako pomocná pro důkaz dalších vět?",
          ["lemma", "pomocná věta"], 1, f"Lemma; rozdíl proti větě je často nevýrazný. {P2}"),
        q("Čím se zavádějí další pojmy, např. rychlost nebo zrychlení?", ["definice", "definicí", "definicemi",
          "pomocí definic", "pomocí definice"], 1,
          f"Další pojmy se zavádějí definicemi (definice rychlosti, zrychlení). {P2}"),
    ]),
    ("Množiny", [
        q("Jak se nazývá množina, která neobsahuje žádný prvek?", ["prázdná množina", "prázdná", "empty set"], 2,
          f"Prázdná množina ∅. {P3}"),
        q("Jak se nazývá vztah X ⊆ Y, tedy a ∈ X ⇒ a ∈ Y?", ["podmnožina", "inkluze", "X je podmnožinou Y",
          "je podmnožinou", "X je podmnožina Y", "subset"], 1,
          f"X ⊆ Y: X je podmnožinou Y (inkluze), definice implikací; rovnost připouští. {P3}"),
        q("Jak se nazývá X, pokud X ⊆ Y a zároveň X ≠ Y?", ["vlastní podmnožina", "vlastní podmnožina Y",
          "X je vlastní podmnožinou Y", "je vlastní podmnožinou", "proper subset"], 2,
          "Vlastní podmnožina rovnost nepřipouští (na přednášce X ⊂ Y; jinde se značí X ⊊ Y, proto se ptám "
          f"definicí). {P3}"),
        q("Jak se nazývá množina prvků, které patří do A i do B (A ∩ B)?", ["průnik", "průnik množin",
          "průnik A a B", "průnik množin A a B", "intersection"], 1, f"x ∈ A ∩ B ⇔ x ∈ A ∧ x ∈ B. {P3}"),
        q("Jak se nazývá množina prvků, které patří do A nebo do B (A ∪ B)?", ["sjednocení", "sjednocení množin",
          "sjednocení A a B", "sjednocení množin A a B", "union"], 1, f"x ∈ A ∪ B ⇔ x ∈ A ∨ x ∈ B. {P3}"),
        q("Jak se nazývá A ∖ B, tedy prvky A, které neleží v B?", ["rozdíl", "rozdíl množin", "množinový rozdíl",
          "rozdíl A a B", "rozdíl množin A a B", "A mínus B", "difference"], 1,
          f"x ∈ A ∖ B ⇔ x ∈ A ∧ x ∉ B. {P3}"),
        q("Jak se nazývá A′, tedy prvky univerza U, které nepatří do A?", ["doplněk", "doplněk množiny",
          "doplněk množiny A", "doplněk A", "komplement", "complement"], 1,
          f"x ∈ A′ ⇔ x ∈ U ∧ x ∉ A. {P3}"),
        q("Jak se nazývá množina U všech uvažovaných prvků, jejíž podmnožinou je každá množina, se kterou "
          "pracujeme?", ["univerzum", "universum", "univerzální množina"], 1, f"Univerzum U, A ⊆ U. {P3}"),
        q("Jak se nazývají množiny A, B, pro které A ∩ B = ∅?", ["disjunktní", "disjunktní množiny",
          "navzájem disjunktní", "disjoint"], 1, f"Disjunktní množiny nemají žádný společný prvek. {P3}"),
        q("Jak se nazývá množina všech podmnožin množiny A, značená P(A) nebo Pot(A)?", ["potenční množina",
          "potenční", "potenční množina A", "power set"], 2, f"Potenční množina, |Pot(A)| = 2^n. {P3}"),
        q("Kolik prvků má potenční množina množiny {a, b, c}?", [str(2 ** len("abc")), "osm"], 1,
          f"|Pot(A)| = 2^n, pro n = 3 je to 8 (od ∅ po {{a, b, c}}). {P3}"),
        q("Jak se nazývá množina všech uspořádaných dvojic (x, y), kde x ∈ A a y ∈ B?", ["kartézský součin",
          "kartézský součin A a B", "kartézský součin množin", "kartézský součin množin A a B", "A krát B",
          "cartesian product"], 2, f"Kartézský součin A × B = {{(x, y) ; x ∈ A ∧ y ∈ B}}. {P3}"),
        q("Jak se podle přednášky nazývá množina, mezi kterou a ℕ existuje vzájemně jednoznačné zobrazení?",
          ["spočetná", "spočetná množina", "spočetně nekonečná", "spočetně nekonečná množina",
           "nekonečně spočetná"], 1,
          "Spočetná: prvky jde očíslovat přirozenými čísly. Někteří autoři řadí mezi spočetné i konečné "
          f"množiny a tuto nazývají spočetně nekonečná, proto se uznává obojí. {P3}"),
        q("Která z množin ℕ, ℤ, ℝ je nespočetná?", ["ℝ", "R", "reálná čísla", "množina reálných čísel",
          "reálná"], 1, "ℝ je nekonečná, ale nespočetná (nejde očíslovat); ℕ a ℤ jsou spočetné. Výpisky 15. 10."),
    ]),
    ("Relace", [
        q("Jak se nazývá podmnožina kartézského součinu A × B?", ["relace", "binární relace",
          "relace mezi A a B", "relation"], 1,
          f"Relace mezi prvky A a B je podmnožina A × B (nebo pravidlo, které o každé dvojici určí, "
          f"zda je v relaci). {P3}"),
        q("Jak se nazývá vlastnost relace R na A: ∀x ∈ A; xRx?", ["reflexivní", "reflexivita",
          "reflexivní relace", "reflexive"], 1, f"Reflexivní, např. x = x. {P3}"),
        q("Jak se nazývá vlastnost relace: xRy ⇒ yRx?", ["symetrická", "symetrie", "symetrická relace",
          "symmetric"], 1, f"Symetrická, např. x = y ⇒ y = x. {P3}"),
        q("Jak se nazývá vlastnost relace: xRy ∧ yRz ⇒ xRz?", ["tranzitivní", "tranzitivita",
          "tranzitivní relace", "transitive"], 1, f"Tranzitivní, např. x > y ∧ y > z ⇒ x > z. {P3}"),
        q("Jak se nazývá vlastnost relace: xRy ∧ yRx ⇒ x = y?", ["antisymetrická", "antisymetrie",
          "slabě antisymetrická", "slabá antisymetrie", "antisymetrická relace", "antisymmetric"], 1,
          f"Antisymetrická (učebnice Přibyl, Tichá: slabá antisymetrie), např. ≤. {P3}"),
        q("Jak se nazývá relace, která je reflexivní, symetrická a tranzitivní?", ["ekvivalence",
          "relace ekvivalence", "equivalence", "equivalence relation"], 1,
          f"Relace ekvivalence (na stejné množině), např. = nebo „stejný zbytek po dělení 3“. {P3}"),
        q("Jak se podle učebnice (Přibyl, Tichá) nazývá relace reflexivní, antisymetrická a tranzitivní, "
          "např. ≤?", ["neostré uspořádání", "uspořádání", "relace uspořádání", "částečné uspořádání",
          "neostré"], 2,
          "Neostré uspořádání (učebnice, s. 107). Tištěná poznámka z přednášky uvádí u uspořádání jen "
          "„tranzitivní a antisymetrická“. Výpisky 15. 10."),
        q("Jak se podle učebnice (Přibyl, Tichá) nazývá relace antireflexivní, antisymetrická a tranzitivní, "
          "např. <?", ["ostré uspořádání", "ostré"], 2, "Ostré uspořádání (učebnice, s. 107). Výpisky 15. 10."),
        q("Jak se nazývá vlastnost relace, kdy žádný prvek není v relaci sám se sebou?", ["antireflexivní",
          "antireflexivita", "ireflexivní", "irreflexive"], 1,
          "Antireflexivní: ∀x; (x, x) ∉ R, např. <. Učebnice Přibyl, Tichá (výpisky 15. 10.)."),
        q("Jak se nazývá systém neprázdných podmnožin A, které jsou po dvou disjunktní a jejich sjednocením "
          "je A?", ["disjunktní rozklad", "rozklad", "rozklad množiny", "rozklad množiny A",
          "disjunktní rozklad množiny A", "partition"], "1-2",
          f"Disjunktní rozklad: a) sjednocením je A, b) každé dvě různé části jsou disjunktní. {P4}"),
        q("Jak se nazývá skupina všech prvků, které jsou spolu navzájem ekvivalentní?", ["třída ekvivalence",
          "třída", "ekvivalenční třída", "třída rozkladu"], 2,
          f"Třída ekvivalence; třídy ekvivalence tvoří rozklad množiny. {P4}"),
        q("Jak se nazývá množina všech tříd ekvivalence množiny A, značená A/∼?", ["podílová množina",
          "faktorová množina", "kvocientní množina", "podílová", "faktorová", "quotient set"], 2,
          f"Na přednášce podílová množina, v učebnici Přibyl, Tichá faktorová množina (M/E); uznává se obojí. {P4}"),
        q("Jak se nazývá prvek třídy ekvivalence, kterým třídu zastupujeme (např. [1] = [4] = [7])?",
          ["reprezentant", "reprezentant třídy", "zástupce", "zástupce třídy"], 1,
          "Každý prvek třídy je její reprezentant; třída se nezmění, když vezmeš jiný. "
          "Učebnice Přibyl, Tichá (výpisky 22. 10.)."),
        q("Kolik tříd ekvivalence má relace „stejný zbytek po dělení 3“ na M = {1, …, 8}?",
          [str(len({x % 3 for x in range(1, 9)})), "tři"], 1,
          "{1, 4, 7}, {2, 5, 8}, {3, 6}: zbytky 1, 2 a 0. Výpisky 22. 10. (příklad z učebnice)."),
    ]),
    ("Zobrazení", [
        q("Jak se nazývá předpis f, který každému prvku x z neprázdné množiny M přiřazuje právě jeden prvek y "
          "z P?", ["zobrazení", "zobrazení M do P", "zobrazení z M do P", "funkce", "mapping"], 1,
          f"Zobrazení množiny M do P, f: M → P. Pro zobrazení se často používá i pojem funkce "
          f"(učebnice, s. 113). {P4}"),
        q("Jak se nazývá x v zápisu f(x) = y?", ["vzor", "vzor prvku y", "vzor y"], 1,
          f"x je vzor prvku y, y je obraz prvku x. {P4}"),
        q("Jak se nazývá y v zápisu f(x) = y?", ["obraz", "obraz prvku x", "obraz x"], 1,
          f"y je obraz prvku x, x je vzor prvku y. {P4}"),
        q("Jak se nazývá D_f u zobrazení f: M → P?", ["definiční obor", "obor definice",
          "definiční obor zobrazení", "domain"], 2, f"D_f je definiční obor, u f: M → P je D_f = M. {P4}"),
        q("Jak se nazývá H_f u zobrazení f: M → P?", ["obor hodnot", "obor hodnot zobrazení", "range"], 2,
          f"H_f je obor hodnot, H_f ⊆ P. {P4}"),
        q("Jak se nazývá zobrazení f: M → P, u kterého obrazy leží v P, ale nemusí pokrýt celé P?",
          ["zobrazení do", "do", "zobrazení do P", "zobrazení do množiny P", "zobrazení do množiny"], 2,
          f"Zobrazení do množiny P: H_f ⊆ P. Je-li H_f = P, je to zobrazení na. {P4}"),
        q("Jak se nazývá zobrazení f: M → P, pro které H_f = P (každý prvek P je obrazem)?",
          ["zobrazení na", "na", "zobrazení na P", "zobrazení na množinu P", "surjektivní", "surjekce",
           "surjektivní zobrazení", "surjective"], "1-2", f"Zobrazení na množinu P (surjektivní): H_f = P. {P4}"),
        q("Jak se nazývá zobrazení, pro které x₁ ≠ x₂ ⇒ f(x₁) ≠ f(x₂)?", ["prosté", "prosté zobrazení",
          "injektivní", "injekce", "injektivní zobrazení", "injective"], 1,
          f"Prosté (injektivní): různé prvky mají různé obrazy. {P4}"),
        q("Jak se nazývá zobrazení, které je prosté a zároveň na?", ["bijekce", "bijektivní",
          "bijektivní zobrazení", "vzájemně jednoznačné", "vzájemně jednoznačné zobrazení", "bijection"], "1-2",
          f"Vzájemně jednoznačné (bijektivní) zobrazení: každé y má právě jeden vzor. {P4}"),
        q("Jak se nazývá zobrazení f⁻¹, pro které platí f⁻¹(y) = x ⇔ f(x) = y?", ["inverzní zobrazení",
          "inverzní", "inverze", "inverzní funkce"], 2,
          f"Inverzní zobrazení f⁻¹ (čteme „f na mínus prvou“), D_(f⁻¹) = H_f a H_(f⁻¹) = D_f. {P4}"),
        q("Jaké musí být zobrazení f, aby k němu existovalo inverzní zobrazení f⁻¹?", ["bijekce", "bijektivní",
          "bijektivní zobrazení", "vzájemně jednoznačné", "vzájemně jednoznačné zobrazení", "prosté a na",
          "prosté a zároveň na", "f je bijekce", "musí být bijekce"], "1-2",
          f"f musí být vzájemně jednoznačné (bijekce), tedy prosté a zároveň na. {P4}"),
        q("Jak se nazývá zobrazení f ∘ g: K → Q, kde z = f(g(x))?", ["složené zobrazení", "složení",
          "složení zobrazení", "složená funkce", "kompozice", "kompozice zobrazení"], 2,
          "Složené zobrazení (značka ∘, „kolečko“). Pozor, učebnice Přibyl, Tichá zapisuje pořadí opačně "
          f"(F ∘ G = nejdřív F), na přednášce f ∘ g = f(g(x)). {P4}"),
    ]),
    ("Kombinatorika", [
        q("Jak se nazývá skupina prvků vybraných ze základní množiny M, u níž nezáleží na pořadí?",
          ["kombinace", "combination"], 1, f"Kombinace: (a, b) a (b, a) zastupuje tutéž skupinu. {P4}"),
        q("Jak se nazývá skupina prvků ze základní množiny, ve které záleží na pořadí, tedy (a, b) a (b, a) "
          "jsou dvě různé skupiny?", ["uspořádaná skupina", "variace"], "1-2",
          f"V rukopisu uspořádaná skupina (z kontextu variace, název je v exportu oříznutý). {P4}"),
        q("Jak se nazývá kombinace, která má k prvků?", ["kombinace k-té třídy", "kombinace kté třídy",
          "k-té třídy", "kté třídy", "k-tá třída", "ktá třída"], 3, f"Kombinace k-té třídy má k prvků. {P4}"),
        q("Jak se nazývá výběr, ve kterém je každý prvek základní množiny vybrán pouze jednou?",
          ["bez opakování", "výběr bez opakování", "skupina bez opakování"], 2, f"Bez opakování. {P4}"),
        q("Jak se nazývá výběr, ve kterém je možno každý prvek z M vybrat vícekrát?", ["s opakováním",
          "výběr s opakováním", "skupina s opakováním", "skupiny s opakováním"], 2, f"S opakováním. {P4}"),
        q("Jak se nazývá výraz n! / ((n − k)! · k!) pro 0 ≤ k ≤ n?", ["kombinační číslo",
          "binomický koeficient", "n nad k"], 2,
          f"Kombinační číslo (n nad k) = n! / ((n − k)! · k!), n, k ∈ ℕ, 0 ≤ k ≤ n. {P4}"),
        q("Čemu se rovná kombinační číslo (n nad 0)?", [str(comb(7, 0)), "jedna"], 1,
          f"(n nad 0) = n! / (n! · 0!) = 1, stejně (n nad n) = 1. {P4}"),
        q("Čemu se rovná kombinační číslo (n nad 1)?", ["n"], 1, f"(n nad 1) = n! / ((n − 1)! · 1!) = n. {P4}"),
        q("Podle symetrie kombinačních čísel platí (n nad k) = (n nad ?). Co patří místo otazníku?",
          ["n-k", "n minus k"], 1, f"(n nad k) = (n nad n − k), protože n − (n − k) = k. {P4}"),
        q("Jak se nazývá vztah (n nad k) + (n nad k+1) = (n+1 nad k+1) z domácího úkolu?",
          ["Pascalovo pravidlo", "Pascalova identita", "Pascal's rule"], 2,
          "Pascalovo pravidlo (k < n). Rukopis má jen vztah, název je doplněný ve výpiscích 22. 10."),
        q("Kolik je (5 nad 2)?", [str(comb(5, 2)), "deset"], 1, f"(5 nad 2) = 5 · 4 / 2! = 20 / 2 = 10. {P4}"),
        q("Kolik je 5!?", [str(factorial(5)), "sto dvacet"], 1,
          f"5! = 5 · 4 · 3 · 2 · 1 = 120 (na přednášce rozepsáno jako 5 · 4 · 3!). {P4}"),
        # přednáška 29. 10.: variace, permutace, kombinace s opakováním, binomická věta
        q("Jak se nazývá uspořádaná k-tice prvků z n-prvkové množiny M, ve které se žádný prvek neopakuje?",
          ["variace bez opakování", "variace", "variace k-té třídy bez opakování", "variace k-té třídy",
           "variation"], "1-3",
          f"Variace k-té třídy z n prvků bez opakování, V_k(n) = n! / (n − k)!, 0 ≤ k ≤ n (cs.wikipedia). {P5}"),
        q("Jak se nazývá uspořádaná k-tice prvků z n-prvkové množiny M, ve které se prvky mohou opakovat?",
          ["variace s opakováním", "variace k-té třídy s opakováním", "variation with repetition"], 3,
          f"Variace s opakováním, V′_k(n) = n^k; k může být i větší než n (cs.wikipedia). {P5}"),
        q("Jak se nazývá uspořádaná n-tice, která obsahuje každý prvek n-prvkové množiny M právě jednou?",
          ["permutace", "permutace bez opakování", "permutace množiny M", "permutation"], "1-3",
          f"Permutace, P(n) = n! = V_n(n); proto 0! = 1 (cs.wikipedia). {P5}"),
        q("Jak se nazývá uspořádaná k-tice, ve které je každý prvek a_i základní množiny M = {a_1, …, a_n} "
          "přesně k_i-krát (k = k_1 + … + k_n)?", ["permutace s opakováním", "permutation with repetition"], 3,
          f"Permutace s opakováním, P′_(k_1,…,k_n)(k) = k! / (k_1! · k_2! · … · k_n!) (cs.wikipedia). {P5}"),
        q("Jak se nazývá k-prvková skupina prvků z n-prvkové množiny M, ve které se prvky mohou opakovat a "
          "nezáleží na pořadí?", ["kombinace s opakováním", "kombinace k-té třídy s opakováním",
          "combination with repetition"], 3,
          f"Kombinace s opakováním, C′_k(n) = (n+k−1 nad k); k může být i větší než n (cs.wikipedia). {P5}"),
        q("Co vyjadřuje čárka ve značení V′, P′, C′?", ["s opakováním", "opakování", "výběr s opakováním",
          "prvky se opakují", "prvky se mohou opakovat"], 2,
          f"V′, P′, C′ jsou variace, permutace a kombinace s opakováním. {P5}"),
        q("Co udává n! / (n − k)! pro 0 ≤ k ≤ n?", ["variace bez opakování", "počet variací bez opakování",
          "počet variací", "variace", "počet variací k-té třídy z n prvků"], "3-4",
          f"Počet variací k-té třídy z n prvků bez opakování, V_k(n) = n · (n − 1) · … · (n − k + 1). "
          f"Příklad z přednášky V_2(3) = {len(list(permutations('123', 2)))}. {P5}"),
        q("Co udává n^k (n prvků, k-tá třída)?", ["variace s opakováním", "počet variací s opakováním",
          "počet variací s opakováním k-té třídy"], "3-4",
          f"Počet variací s opakováním, V′_k(n) = n^k (prvky kartézského součinu M^k). Příklad z přednášky "
          f"V′_2(3) = {len(list(product('123', repeat=2)))}. {P5}"),
        q("Co udává (n+k−1 nad k)?", ["kombinace s opakováním", "počet kombinací s opakováním",
          "počet kombinací s opakováním k-té třídy"], "3-4",
          f"Počet kombinací s opakováním C′_k(n). Příklad z přednášky C′_2(3) = (4 nad 2) = "
          f"{len(list(combinations_with_replacement('123', 2)))}. {P5}"),
        q("Co udává k! / (k_1! · k_2! · … · k_n!), kde k = k_1 + … + k_n?", ["permutace s opakováním",
          "počet permutací s opakováním"], "3-4",
          f"Počet permutací s opakováním P′_(k_1,…,k_n)(k): prohození stejných prvků nedá nové pořadí. {P5}"),
        q("Kolik je P′_(1,1,2)(4), počet různých pořadí čísel 1, 2, 3, 3?", [str(len(set(permutations("1233")))),
          "dvanáct"], 1, f"4! / (1! · 1! · 2!) = 24 / 2 = 12 (příklad z přednášky). {P5}"),
        q("Jak se v binomické větě nazývá kombinační číslo (n nad k)?", ["binomický koeficient",
          "binomial coefficient"], 2, f"Binomický koeficient, čte se „n nad k“ (cs.wikipedia). {P5}"),
        q("Jak se nazývá vztah (a+b)^n = Σ (n nad k) · a^(n−k) · b^k pro k = 0, 1, …, n?",
          ["binomická věta", "binomický rozvoj", "binomial theorem"], 2,
          f"Binomická věta: rozvoj n-té mocniny dvojčlenu (cs.wikipedia). {P5}"),
        q("Kolik sčítanců má rozvoj (a+b)^n podle binomické věty?", ["n+1", "n + 1", "n plus 1", "n plus jedna"],
          "1-3", f"k = 0, 1, …, n, tedy n + 1 sčítanců; pro n = 3 jsou to {len(BINOM3)}. {P5}"),
        q("Jaké koeficienty má rozvoj (a+b)^3, od a^3 po b^3?", [" ".join(map(str, BINOM3)), "".join(map(str, BINOM3)),
          "jedna tři tři jedna"], 4,
          f"(a+b)^3 = a^3 + 3a^2·b + 3a·b^2 + b^3, koeficienty (3 nad k) = 1, 3, 3, 1. {P5}"),
    ]),
    ("Konečné automaty", [
        q("Jak se nazývá uspořádaná pětice A = (Q, Σ, δ, q₀, F)?", ["konečný automat",
          "deterministický konečný automat", "konečný deterministický automat", "automat", "DKA", "DFA",
          "finite automaton"], 2,
          f"Konečný automat (deterministický): Q stavy, Σ abeceda, δ přechodová funkce, q₀ počáteční stav, "
          f"F přijímací stavy (Mareš, Úvod do automatů, kap. 1.2). {P5}"),
        q("Jak se nazývá množina Q v pětici konečného automatu A = (Q, Σ, δ, q₀, F)?", ["množina stavů", "stavy",
          "konečná množina stavů", "konečná neprázdná množina stavů", "states", "set of states"], 2,
          f"Q je konečná neprázdná množina stavů (Mareš, kap. 1.2). {P5}"),
        q("Jak se nazývá Σ v pětici konečného automatu?", ["abeceda", "vstupní abeceda", "množina znaků",
          "množina vstupních symbolů", "vstupní symboly", "alphabet"], "1-2",
          f"Σ je konečná neprázdná množina znaků, (vstupní) abeceda, např. Σ = {{0, 1}} (Mareš, kap. 1.2). {P5}"),
        q("Jak se nazývá δ : Q × Σ → Q v pětici konečného automatu?", ["přechodová funkce",
          "přechodová funkce automatu", "funkce přechodů", "transition function"], 2,
          f"Přechodová funkce: pro každý stav a znak ze vstupu určí, do jakého stavu automat přejde "
          f"(Mareš, kap. 1.2). {P5}"),
        q("Jak se nazývá q₀ v pětici konečného automatu?", ["počáteční stav", "startovní stav", "počáteční",
          "initial state", "start state"], 2, f"q₀ ∈ Q je počáteční stav (Mareš, kap. 1.2). {P5}"),
        q("Jak se nazývá F ⊆ Q v pětici konečného automatu?", ["množina přijímacích stavů", "přijímací stavy",
          "množina koncových stavů", "koncové stavy", "accepting states", "final states"], 3,
          f"F je množina přijímacích (koncových) stavů (Mareš, kap. 1.2). {P5}"),
        q("Jak se čte symbol Σ v zápisu konečného automatu?", ["velká sigma", "sigma"], 2,
          f"Σ = velká sigma, označuje abecedu. {P5}"),
        q("Jak se čte symbol δ u přechodové funkce?", ["malá delta", "delta"], 2,
          f"δ = malá delta, δ : Q × Σ → Q. {P5}"),
        q("Jak se nazývá množina Q × Σ všech dvojic (stav, znak), na které je definovaná přechodová funkce?",
          ["kartézský součin", "kartézský součin Q a Σ", "kartézský součin množin Q a Σ", "cartesian product"], 2,
          f"Kartézský součin (přednáška 15. 10.), např. dvojice (q₀, 1). {P5}"),
        q("Co je výsledkem δ(q, a) pro stav q ∈ Q a znak a ∈ Σ?", ["stav", "nový stav", "další stav",
          "následující stav", "stav z Q", "stav automatu", "state"], 1,
          f"δ(q, a) = q′, q′ ∈ Q: ve stavu q přečte znak a a přejde do stavu q′ (zápis z tabule). {P5}"),
        q("Jaký je konečný automat, u kterého má každý stav pro každý vstupní symbol právě jeden přechod?",
          ["deterministický", "deterministický automat", "deterministický konečný automat", "DKA", "DFA",
           "deterministic"], 1,
          f"Deterministický: z každého vrcholu stavového diagramu vede pro každý znak právě jedna hrana "
          f"(Mareš, kap. 1.2). Automat z přednášky má {AUT_STATES} · {AUT_SYMBOLS} = {AUT_STATES * AUT_SYMBOLS} "
          f"přechodů. {P5}"),
        q("Jak se nazývá slovo, po jehož přečtení skončí výpočet automatu ve stavu z F?", ["přijaté slovo",
          "přijaté", "přijímané slovo", "přijímané", "rozpoznané slovo", "slovo je přijato", "přijato",
          "accepted"], 2,
          f"Slovo je přijato, když výpočet skončí v přijímacím stavu (Mareš, kap. 1.2). Rozhoduje stav po přečtení "
          f"celého slova. {P5}"),
        q("Jak se nazývá zápis automatu, kde řádky jsou stavy, sloupce znaky abecedy a v políčku je δ(q, a)?",
          ["tabulka přechodů", "tabulka", "přechodová tabulka", "tabulka přechodové funkce", "transition table"], 2,
          f"Tabulka (přechodů): počáteční stav se označí →, přijímací ←, má |Q| · |Σ| políček. {P5}"),
        q("Jak se nazývá orientovaný graf automatu, jehož vrcholy jsou stavy a hrana z q do q′ s popiskem a znamená "
          "δ(q, a) = q′?", ["stavový diagram", "přechodový diagram", "diagram", "stavový graf", "state diagram"], 2,
          f"Stavový (přechodový) diagram, „tabulka jako orientovaný graf“. Podle přednášky se automat navrhuje "
          f"nejdřív stavovým diagramem. {P5}"),
        q("Jak se nazývá zápis automatu z přednášky, ve kterém z počátečního stavu (kořene) vedou větve pro každý "
          "znak do stavu podle δ a stav, který už se objevil, se dál nerozvíjí?", ["stavový strom",
          "strom stavový", "strom", "strom stavů"], 2,
          f"Stavový strom (v rukopisu „STROM STAVOVÝ“). Popis podle stromu z přednášky; definici se zdrojem "
          f"výpisky nemají, ověřit na cvičení. {P5}"),
        q("Jak se na náčrtu konečného automatu z přednášky nazývá část Ř. J., ke které patří množina stavů Q?",
          ["řídicí jednotka"], 2,
          f"Řídicí jednotka (Ř. J.), Q = {{q₀, …, qₙ}}; od ní vede čára k hlavě nad páskou a₁ | a₂ | … | aₘ. {P5}"),
    ]),
]


def word_range(w):
    lo, _, hi = str(w).partition("-")
    return int(lo), int(hi or lo)


def self_check(qs):
    assert len({x["id"] for x in qs}) == len(qs), "duplicitní id"
    assert len({x["text"] for x in qs}) == len(qs), "duplicitní text otázky"
    for x in qs:
        acc = x["accept"]
        assert acc and all(isinstance(v, str) and v.strip() for v in acc), x["id"]
        assert len({v.lower() for v in acc}) == len(acc), f'{x["id"]}: duplicitní varianta'
        lo, hi = word_range(x["words"])
        assert 1 <= lo <= hi <= 5, x["id"]
        assert lo <= len(acc[0].split()) <= hi, f'{x["id"]}: words neodpovídá kanonické odpovědi'
        assert x["category"] and x["explanation"], x["id"]
    # číselné odpovědi napsané ručně (ostatní se počítají přímo v CATS)
    assert int("F", 16) == 15 and 16 == 2 ** 4 and comb(7, 1) == 7
    # přednáška 29. 10.: n + 1 sčítanců, BINOM3 jako (4 nad 2) = 6 z výčtu, rozvoj (a+b)^3 roznásobením
    assert BINOM3 == [1, 3, 3, 1] and len(list(combinations_with_replacement('123', 2))) == comb(4, 2)
    a, b = 2, 5
    assert (a + b) ** 3 == sum(c * a ** (3 - k) * b ** k for k, c in enumerate(BINOM3))


def main():
    qs = [{"type": "recall", "category": cat, **x} for cat, items in CATS for x in items]
    for i, x in enumerate(qs, 1):
        x["number"] = i
        x["id"] = f"r-{i}"
    self_check(qs)
    out = {"title": "Doplňovačka (na paměť), přednášky 1 až 5", "lecture": 5, "date": "2026-10-29", "questions": qs}
    path = Path(__file__).parent / "banky" / "doplnovacka" / "04r-doplnovacka.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = ", ".join(f"{cat} {len(items)}" for cat, items in CATS)
    print(f"{path.name}: {len(qs)} otázek ({counts})")


if __name__ == "__main__":
    main()
