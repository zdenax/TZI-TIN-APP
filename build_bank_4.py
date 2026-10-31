#!/usr/bin/env python3
"""Vygeneruje banky otázek pro 4. přednášku do banky/: 04-2026-10-22.json (rozklad, třídy ekvivalence, zobrazení)
a 04k-kombinatorika.json (kombinatorika jako vlastní modul).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z autorových poznámek z přednášky 22. 10. 2026 (poznámky 2026-10-22 a 2026-10-22-kombinatorika)
a z učebního textu Přibyl, Tichá (kap. 4.2.2 a 4.2.3). Kombinatorika: pojmy, kombinační číslo a jeho vlastnosti a Pascalovo pravidlo (domácí úkol). Vzorce pro variace
s opakováním apod. přednáška zatím neprobrala. Odpovědi na příklady se počítají a ověřují zde (brute force),
ne ručně. Teorii je třeba kontrolovat proti přednášce a sylabu KI/TIN.
Spuštění:  python3 build_bank_4.py
"""
import itertools
import json
import math
import random
from pathlib import Path

from formule import pripoj_vzorce


# ── pomocné funkce a ověření ─────────────────────────────────────────────────

def is_partition(system, A):
    """Rozklad: neprázdné podmnožiny A, sjednocení = A, každé dvě různé disjunktní (jako v přednášce)."""
    system = [frozenset(s) for s in system]
    if any(not s for s in system) or any(not s <= frozenset(A) for s in system):
        return False
    if frozenset().union(*system) != frozenset(A):
        return False
    return all(not (a & b) for a, b in itertools.combinations(system, 2)) and len(set(system)) == len(system)


def set_partitions(items):
    """Všechny rozklady množiny (každý jako seznam tříd)."""
    items = list(items)
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for p in set_partitions(rest):
        yield [[first]] + p
        for i in range(len(p)):
            yield p[:i] + [[first] + p[i]] + p[i + 1:]


def is_mapping(pairs, M):
    """Zobrazení M do …: každé x z M má právě jeden obraz (D_f = M, jako v přednášce)."""
    return all(len({y for x2, y in pairs if x2 == x}) == 1 for x in M)


def classify(f, P):
    """f: dict x -> y; vrátí (prosté, na)."""
    return len(set(f.values())) == len(f), set(f.values()) == set(P)


# (text, [možnosti], [správné indexy], vysvětlení); správná odpověď je vždy první možnost, pořadí se zamíchá
def choice_questions():
    A5 = {1, 2, 3, 4, 5}
    ok = [[1, 2], [3], [4, 5]]
    bad = ([[1, 2], [2, 3], [4, 5]], [[1, 2], [4, 5]], [[1, 2], [3], [4, 5], []])
    assert is_partition(ok, A5) and not any(is_partition(b, A5) for b in bad)

    M6 = set("abcdef")
    E = [{"a", "d"}, {"c", "e", "f"}, {"b"}]
    F = [{"a", "b"}, {"c", "e", "f"}, {"a", "b"}]
    G = [{"a", "b", "c"}, {"d", "f"}]
    H = [{"a", "b"}, {"c", "d"}, {"e"}]
    assert is_partition(E, M6) and not any(is_partition(x, M6) for x in (F, G, H))

    M3 = [1, 2, 3]
    f_ok = {(1, 2), (2, 2), (3, 1)}
    f_bad = ({(1, 2), (1, 3), (2, 2), (3, 1)}, {(1, 1), (2, 2)}, {(1, 2), (2, 3), (2, 1), (3, 3)})
    assert is_mapping(f_ok, M3) and not any(is_mapping(x, M3) for x in f_bad)

    f1 = {1: "a", 2: "b", 3: "c"}              # prosté, ne na
    f2 = {1: "a", 2: "a", 3: "b", 4: "b"}      # na, ne prosté
    assert classify(f1, "abcd") == (True, False) and classify(f2, "ab") == (False, True)

    main = [
        # rozklad
        ("Jak je definován disjunktní rozklad množiny A?",
         ["systém neprázdných podmnožin A, jejichž sjednocením je A a každé dvě různé jsou disjunktní",
          "systém podmnožin A, jejichž průnikem je A",
          "systém neprázdných podmnožin A, jejichž sjednocením je A, ale mohou se překrývat",
          "systém podmnožin A, které jsou disjunktní, ale nemusí dát dohromady A"], [0],
         "Rozklad (přednáška 22. 10.): a) A₁ ∪ … ∪ Aₙ = A a b) Aᵢ ∩ Aⱼ = ∅ pro i ≠ j. Podskupiny jsou neprázdné."),
        ("Který systém je rozkladem množiny A = {1, 2, 3, 4, 5}?",
         ["{{1,2}, {3}, {4,5}}", "{{1,2}, {2,3}, {4,5}}", "{{1,2}, {4,5}}", "{{1,2}, {3}, {4,5}, ∅}"], [0],
         "{{1,2},{2,3},{4,5}}: číslo 2 je ve dvou skupinách (překrývají se). {{1,2},{4,5}}: chybí 3 (sjednocení není A). "
         "{{1,2},{3},{4,5},∅} má prázdnou skupinu, ta v rozkladu být nesmí."),
        ("Co říká podmínka b) u rozkladu, Aᵢ ∩ Aⱼ = ∅ pro i ≠ j?",
         ["žádné dvě různé skupiny rozkladu nemají společný prvek", "sjednocení všech skupin je celá množina A",
          "žádná skupina rozkladu není prázdná", "každá skupina rozkladu má aspoň dva prvky"], [0],
         "b) = disjunktnost (nepřekrývání). Sjednocení je podmínka a), neprázdnost skupin patří do definice zvlášť."),
        ("Která z množin je rozkladem M = {a, b, c, d, e, f}?",
         ["{{a,d}, {c,e,f}, {b}}", "{{a,b}, {c,e,f}, {a,b}}", "{{a,b,c}, {d,f}}", "{{a,b}, {c,d}, {e}}"], [0],
         "Správně je {{a,d},{c,e,f},{b}} (skripta, s. 121). {{a,b},{c,e,f},{a,b}} opakuje {a,b} a chybí d. "
         "{{a,b,c},{d,f}} vynechává e. {{a,b},{c,d},{e}} vynechává f."),
        # třída ekvivalence, podílová množina
        ("Která trojice vlastností musí platit, aby relace byla ekvivalencí?",
         ["reflexivní, symetrická, tranzitivní", "reflexivní, antisymetrická, tranzitivní",
          "symetrická, antisymetrická, tranzitivní", "antireflexivní, symetrická, tranzitivní"], [0],
         "Ekvivalence = reflexivní + symetrická + tranzitivní."),
        ("Co tvoří jednu třídu ekvivalence?",
         ["všechny prvky, které jsou spolu navzájem ekvivalentní", "všechny prvky celé množiny",
          "libovolné dva prvky množiny", "prvky, které spolu nejsou ekvivalentní"], [0],
         "Třídu ekvivalence tvoří prvky, které jsou spolu vždy ekvivalentní (a každý prvek ekvivalentní s nimi do třídy patří)."),
        ("Co říká podmínka 3) u třídy ekvivalence A′: x ∈ A′ ∧ x ∼ y ⇒ y ∈ A′?",
         ["každý prvek ekvivalentní s prvkem třídy patří do téže třídy", "každé dva prvky třídy jsou ekvivalentní",
          "třída A′ je podmnožinou A", "třída A′ není prázdná"], [0],
         "Podmínka 3) znamená, že třídu nelze „rozšířit“: co je ekvivalentní s prvkem třídy, už v ní je. "
         "„Každé dva prvky třídy jsou ekvivalentní“ je podmínka 2), „A′ je podmnožinou A“ je podmínka 1)."),
        ("Jak souvisí relace ekvivalence a rozklad množiny?",
         ["třídy ekvivalence tvoří rozklad a každý rozklad určuje ekvivalenci (prvky ve stejné třídě jsou ekvivalentní)",
          "třídy ekvivalence se mohou překrývat, rozklad ne",
          "ekvivalence nikdy nedá rozklad", "rozklad určuje ekvivalenci jen u konečných množin"], [0],
         "Skripta, s. 106 až 107: třídy ekvivalence tvoří rozklad a každý rozklad určuje relaci ekvivalence."),
        ("Co je podílová (faktorová) množina A/∼?",
         ["množina všech tříd rozkladu (tříd ekvivalence) množiny A", "množina všech prvků A",
          "množina všech dvojic ekvivalentních prvků", "největší třída ekvivalence"], [0],
         "A/∼ je množina, jejímiž prvky jsou třídy. Např. pro M = {1,…,8} a stejný zbytek po dělení 3 má 3 prvky, "
         "ačkoli M má 8 prvků. (Ve skriptech se jí říká faktorová množina, značí se M/E.)"),
        # zobrazení
        ("Co je zobrazení množiny M do množiny P?",
         ["předpis, který každému prvku x z M přiřadí právě jeden prvek y z P",
          "předpis, který každému x z M přiřadí aspoň jeden prvek y z P",
          "libovolná relace mezi M a P", "předpis, který některým x nepřiřadí nic"], [0],
         "Zobrazení: ∀x ∈ M ∃! y ∈ P; x ↦ y. „Právě jeden“ je klíčové."),
        ("Která relace je zobrazením množiny M = {1, 2, 3} do M (každé x ∈ M musí mít právě jeden obraz)?",
         ["{(1,2), (2,2), (3,1)}", "{(1,2), (1,3), (2,2), (3,1)}", "{(1,1), (2,2)}", "{(1,2), (2,3), (2,1), (3,3)}"], [0],
         "Každé x ∈ M musí mít právě jeden obraz. V {(1,2), (1,3), (2,2), (3,1)} má 1 dva obrazy, "
         "v {(1,1), (2,2)} nemá obraz 3, v {(1,2), (2,3), (2,1), (3,3)} má 2 dva obrazy."),
        ("Jak se nazývá x a y u zobrazení f(x) = y?",
         ["x je vzor prvku y, y je obraz prvku x", "x je obraz prvku y, y je vzor prvku x",
          "x je obor hodnot, y definiční obor", "x i y jsou obrazy"], [0],
         "Rukopis: x se nazývá vzor prvku y, y se nazývá obraz prvku x."),
        ("Co označují D_f a H_f u zobrazení f: M → P?",
         ["D_f je definiční obor (D_f = M), H_f je obor hodnot (H_f ⊆ P)",
          "D_f je obor hodnot, H_f je definiční obor", "D_f = P a H_f = M", "D_f i H_f jsou vždy rovno P"], [0],
         "D_f = M (všechna x, která mají obraz), H_f ⊆ P (všechna y, která jsou něčím obrazem)."),
        ("Kdy je zobrazení f: M → P zobrazením na množinu P (surjektivní)?",
         ["když H_f = P", "když D_f = P", "když x₁ ≠ x₂ ⇒ f(x₁) ≠ f(x₂)", "když H_f je vlastní podmnožinou P"], [0],
         "Na P: obor hodnot je celé P (každé y má aspoň jeden vzor). x₁ ≠ x₂ ⇒ f(x₁) ≠ f(x₂) je prosté zobrazení. "
         "H_f jako vlastní podmnožina P je zobrazení do P, které na P není."),
        ("Kdy je zobrazení f prosté (injektivní)?",
         ["když x₁ ≠ x₂ ⇒ f(x₁) ≠ f(x₂)", "když H_f = P", "když x₁ = x₂ ⇒ f(x₁) ≠ f(x₂)", "když D_f = P"], [0],
         "Prosté: různé prvky mají různé obrazy (žádné dvě šipky nekončí ve stejném bodě)."),
        ("Co je vzájemně jednoznačné zobrazení (bijekce)?",
         ["zobrazení, které je prosté a zároveň na P (D_f = M, H_f = P)", "zobrazení, které je jen prosté",
          "zobrazení, které je jen na P", "zobrazení, kde H_f je vlastní podmnožinou P"], [0],
         "Bijekce = prosté + na. Pak má každé y ∈ P právě jeden vzor."),
        ("Zobrazení f: {1,2,3} → {a,b,c,d} je dáno f(1) = a, f(2) = b, f(3) = c. Je:",
         ["prosté, ale není na", "na, ale není prosté", "prosté i na (bijekce)", "není zobrazení"], [0],
         "Obrazy a, b, c jsou různé (prosté). Prvek d nemá vzor, takže f není na množinu {a,b,c,d}."),
        ("Zobrazení f: {1,2,3,4} → {a,b} je dáno f(1) = f(2) = a, f(3) = f(4) = b. Je:",
         ["na, ale není prosté", "prosté, ale není na", "bijekce", "není ani na, ani prosté"], [0],
         "Oba prvky a, b mají vzor (na). Ale f(1) = f(2) = a, takže různé prvky mají stejný obraz (není prosté)."),
        ("Kdy k zobrazení f existuje inverzní zobrazení f⁻¹?",
         ["když je f vzájemně jednoznačné (bijekce)", "vždy", "když je f jen zobrazením do P", "když D_f = H_f"], [0],
         "Inverzní zobrazení existuje, když je f bijekce (prosté a na). Skripta: F je prosté ⇔ F⁻¹ je zobrazení."),
        ("Co platí pro inverzní zobrazení f⁻¹?",
         ["D(f⁻¹) = H_f a H(f⁻¹) = D_f", "D(f⁻¹) = D_f a H(f⁻¹) = H_f",
          "D(f⁻¹) = H_f a H(f⁻¹) = H_f", "D(f⁻¹) = D_f a H(f⁻¹) = D_f"], [0],
         "Šipky se otočí: kde zobrazení končilo (H_f), tam inverzní začíná, a naopak."),
        ("Jak se zapíše f⁻¹(y) = x?",
         ["f⁻¹(y) = x ⇔ f(x) = y", "f⁻¹(y) = x ⇔ f(y) = x", "f⁻¹(y) = x ⇔ f(x) ≠ y", "f⁻¹(y) = 1/f(y)"], [0],
         "Inverzní zobrazení jde po šipkách zpátky: co f pošle z x do y, to f⁻¹ pošle z y do x."),
        ("Je dáno g: K → L a f: L → Q. Co je složené zobrazení f∘g (zápis z přednášky)?",
         ["f∘g: K → Q, (f∘g)(x) = f(g(x))", "f∘g: K → L, (f∘g)(x) = f(g(x))",
          "f∘g: Q → K, (f∘g)(x) = f(g(x))", "f∘g: K → Q, (f∘g)(x) = f(x) · g(x)"], [0],
         "Nejdřív g (z K do L), pak f (z L do Q). Pozor: skripta (s. 118) mají pořadí opačné, F∘G(x) = G(F(x)); "
         "tady je to zápis z přednášky."),
        ("Jak poznáš z grafu v rovině (x vodorovně, y svisle), že relace NENÍ zobrazení?",
         ["nějaká svislá přímka protne graf ve dvou nebo více bodech (jedno x má víc hodnot y)",
          "graf prochází počátkem", "graf je vodorovná přímka", "graf nemá žádný bod s x > 0"], [0],
         "Zobrazení: každému x právě jedno y, tedy každá svislá přímka protne graf nejvýše jednou. "
         "Vodorovná přímka y = c je zobrazení (konstantní)."),
    ]
    komb = [
        # kombinatorika (pojmy)
        ("Co je kombinace ze základní množiny M?",
         ["skupina prvků z M, u níž nezáleží na pořadí; (a, b) a (b, a) je tatáž skupina",
          "skupina prvků z M, u níž záleží na pořadí; (a, b) a (b, a) jsou různé skupiny",
          "skupina, ve které je vždy vybráno všech n prvků M", "skupina, ve které se každý prvek vybírá víckrát"], [0],
         "Rukopis: kombinace je skupina, u níž nezáleží na pořadí, (a, b) i (b, a) zastupuje tutéž skupinu. "
         "Kombinace k-té třídy má k prvků."),
        ("Co je uspořádaná skupina (variace)?",
         ["skupina, ve které záleží na pořadí prvků; (a, b) a (b, a) jsou dvě různé skupiny",
          "skupina, ve které nezáleží na pořadí; (a, b) a (b, a) je tatáž skupina",
          "skupina, ve které se žádný prvek neopakuje", "skupina, která obsahuje všechny prvky M"], [0],
         "Uspořádaná skupina: záleží na pořadí, tedy (a, b) ≠ (b, a). (Že jde o variace, je čtení z kontextu rukopisu.)"),
        ("Co znamená, že se skupina vybírá bez opakování?",
         ["každý prvek základní množiny je vybrán pouze jednou", "každý prvek je vybrán nejméně dvakrát",
          "záleží na pořadí prvků", "skupina má stejně prvků jako M"], [0],
         "Bez opakování: každý prvek z M jen jednou. S opakováním: každý prvek lze vybrat vícekrát."),
        ("Co je to kombinace k-té třídy?",
         ["skupina o k prvcích (bez ohledu na pořadí)", "skupina o k prvcích, u níž záleží na pořadí",
          "skupina o n prvcích", "k-tý prvek základní množiny"], [0],
         "Rukopis: kombinace k-té třídy je skupina, která má k prvků."),
        # kombinační číslo (přednáška 22. 10., 2. část)
        ("Čemu se rovná 0! (nula faktoriál)?",
         ["1", "0", "není definováno", "n"], [0],
         "Dohoda 0! = 1. Bez ní by C(n,0) = n!/(n!·0!) a C(n,n) = n!/(0!·n!) nedávala smysl."),
        ("Jak je definováno kombinační číslo C(n, k) = (n nad k), kde 0 ≤ k ≤ n?",
         ["n! / ((n−k)! · k!)", "n! / (n−k)!", "n! / k!", "(n−k)! · k! / n!"], [0],
         "C(n,k) = n!/((n−k)!·k!) je počet kombinací k-té třídy z n prvků. n!/(n−k)! je počet variací."),
        ("Jak se rozepíše n!, aby se dal vykrátit faktoriál (n−k)! (k ≤ n)?",
         ["n! = n·(n−1)·…·(n−k+1)·(n−k)!", "n! = n·(n−1)·…·(n−k)·k!",
          "n! = n·(n−1)·…·(n−k+1)·k!", "n! = (n−k)!·k!"], [0],
         "n! = n·(n−1)·…·2·1. Prvních k činitelů necháme rozepsaných, zbytek (n−k)·…·1 je (n−k)!. "
         "Příklad: 6! = 6·5·4!."),
        ("Čemu se rovná C(n, k) = n! / ((n−k)!·k!) po vykrácení (n−k)!?",
         ["n·(n−1)·…·(n−k+1) / k!", "n·(n−1)·…·(n−k+1)", "n·(n−1)·…·(n−k) / k!", "(n−k)! / k!"], [0],
         "C(n,k) = n!/((n−k)!·k!) = n·(n−1)·…·(n−k+1)·(n−k)! / ((n−k)!·k!) = n·(n−1)·…·(n−k+1)/k!. "
         "Čitatel má k činitelů."),
        ("Čemu se rovná C(n, k) podle symetrie kombinačních čísel?",
         ["C(n, n−k)", "C(n, k+1)", "C(n−k, k)", "C(n, n+k)"], [0],
         "C(n,n−k) = n!/((n−(n−k))!·(n−k)!) = n!/(k!·(n−k)!) = C(n,k). Vybrat k prvků je totéž jako vybrat těch n−k, které nevezmeme."),
        ("Čemu se rovnají C(n, 0) a C(n, n)?",
         ["obě 1", "obě 0", "C(n,0) = 1 a C(n,n) = n", "obě n"], [0],
         "C(n,0) = n!/(n!·0!) = 1 a C(n,n) = n!/(0!·n!) = 1. Nevybrat nic i vybrat všechno jde jedním způsobem."),
        ("Čemu se rovná C(n, 1)?",
         ["n", "1", "n!", "n − 1"], [0],
         "C(n,1) = n!/((n−1)!·1!) = n·(n−1)!/(n−1)! = n. Jeden prvek z n lze vybrat n způsoby."),
        ("Pascalovo pravidlo (domácí úkol): čemu se rovná C(n, k) + C(n, k+1), kde k < n?",
         ["C(n+1, k+1)", "C(n+1, k)", "C(n, k+2)", "C(n+1, k+2)"], [0],
         "C(n,k) + C(n,k+1) = C(n+1,k+1). Např. C(5,2) + C(5,3) = 10 + 10 = 20 = C(6,3)."),
        ("Proč se v domácím úkolu C(n,k) + C(n,k+1) = C(n+1,k+1) předpokládá k < n?",
         ["aby C(n, k+1) bylo definováno (potřeba k+1 ≤ n)", "aby bylo C(n, k) rovno nule",
          "aby platilo n < 0", "protože pro k = n vychází C(n+1, k+1) = 0"], [0],
         "C(n,k+1) vyžaduje k+1 ≤ n. Pro k = n by ve jmenovateli bylo (n−k−1)! = (−1)!, které není definováno."),
        ("Jak se v důkazu Pascalova pravidla získá společný jmenovatel?",
         ["využijí se vztahy (k+1)! = (k+1)·k! a (n−k)! = (n−k)·(n−k−1)!",
          "oba zlomky se vynásobí n!", "použije se vztah (k+1)! = k! + 1",
          "použije se vztah (n−k)! = (n−k−1)! + (n−k)"], [0],
         "Společný jmenovatel je (k+1)!·(n−k)!. První zlomek se rozšíří (k+1), druhý (n−k). "
         "Součet čitatelů n!·[(k+1)+(n−k)] = n!·(n+1) = (n+1)!."),
    ]
    return main, komb


# (text, hint, answer, řešení)
def input_questions():
    qs = []
    # počty rozkladů (skripta s. 120: {a,b,c} má 5 rozkladů; {1,2,3,4} počítáno)
    for n in (3, 4):
        items = list(range(1, n + 1))
        cnt = sum(1 for _ in set_partitions(items))
        assert all(is_partition(p, items) for p in set_partitions(items))
        names = "{" + ",".join(map(str, items)) + "}"
        qs.append((f"Kolik různých rozkladů má množina {names}?", "číslo", str(cnt),
                   f"Všech rozkladů množiny {names} je {cnt}. (Pro 3 prvky: {{{{1,2,3}}}}, {{{{1,2}},{{3}}}}, "
                   f"{{{{1,3}},{{2}}}}, {{{{2,3}},{{1}}}}, {{{{1}},{{2}},{{3}}}}.)" if n == 3 else
                   f"Všech rozkladů množiny {names} je {cnt} (spočítáno výčtem)."))
    # třídy ekvivalence: stejný zbytek po dělení m na M = {1..n}
    for n, m, x in ((8, 3, 1), (9, 4, 2), (9, 3, 5)):
        M = list(range(1, n + 1))
        cls = {}
        for v in M:
            cls.setdefault(v % m, []).append(v)
        mine = cls[x % m]
        assert all(len(c) >= 1 for c in cls.values()) and is_partition(list(cls.values()), M)
        text = f"M = {{1,…,{n}}}, relace: stejný zbytek po dělení {m}. Napiš třídu prvku {x} (prvky vzestupně bez mezer)."
        sol = "třídy: " + "; ".join("{" + ",".join(map(str, c)) + "}" for c in cls.values()) + \
              f"\ntřída prvku {x}: {{{','.join(map(str, mine))}}}"
        qs.append((text, "např. 147", "".join(map(str, mine)), sol))
    # počet prvků podílové množiny
    n, m = 20, 4
    M = list(range(1, n + 1))
    k = len({v % m for v in M})
    qs.append((f"M = {{1,…,{n}}}, relace: stejný zbytek po dělení {m}. Kolik prvků má podílová množina M/∼?",
               "číslo", str(k),
               f"Třídy odpovídají zbytkům 0, 1, 2, 3, tedy M/∼ má {k} prvky (tříd, ne čísel z M)."))
    # obor hodnot
    f = {1: "a", 2: "a", 3: "c", 4: "c", 5: "b"}
    h = len(set(f.values()))
    qs.append(("f: {1,2,3,4,5} → {a,b,c,d}, f(1) = a, f(2) = a, f(3) = c, f(4) = c, f(5) = b. Kolik prvků má obor hodnot H_f?",
               "číslo", str(h), f"H_f = {{a,b,c}}, tedy {h} prvky. Prvek d nemá vzor, takže f není na množinu {{a,b,c,d}}."))
    # inverzní zobrazení
    g = {1: 2, 2: 4, 3: 6}
    inv = {v: k2 for k2, v in g.items()}
    assert len(inv) == len(g)
    qs.append(("f: {1,2,3} → {2,4,6}, f(x) = 2x, je bijekce. Kolik je f⁻¹(4)?", "číslo", str(inv[4]),
               "f⁻¹(4) = x ⇔ f(x) = 4. Z 2x = 4 plyne x = 2, tedy f⁻¹(4) = 2."))
    # složené zobrazení (zápis z přednášky)
    gg = lambda x: x + 1
    ff = lambda y: 2 * y
    qs.append(("g(x) = x + 1, f(y) = 2y. Kolik je (f∘g)(3), kde (f∘g)(x) = f(g(x))?", "číslo", str(ff(gg(3))),
               f"Nejdřív g: g(3) = 4. Pak f: f(4) = 8. Tedy (f∘g)(3) = {ff(gg(3))}."))
    qs.append(("g(x) = x + 1, f(y) = 2y. Kolik je (g∘f)(3), kde (g∘f)(x) = g(f(x))?", "číslo", str(gg(ff(3))),
               f"Nejdřív f: f(3) = 6. Pak g: g(6) = 7. Tedy (g∘f)(3) = {gg(ff(3))}, "
               f"což je jiné než (f∘g)(3) = {ff(gg(3))}. Na pořadí záleží."))
    main_qs, qs = qs, []  # od tohoto místa kombinatorika (vlastní modul)
    # kombinatorika: počty (výčtem)
    M5 = "abcde"
    v = len(list(itertools.permutations(M5, 2)))
    assert v == 5 * 4 == 120 // 6
    qs.append(("Kolik uspořádaných dvojic (bez opakování) lze vybrat z množiny {a,b,c,d,e}?", "číslo", str(v),
               f"První prvek 5 způsoby, druhý 4 způsoby: 5 · 4 = {v}. Pořadí záleží, (a,b) ≠ (b,a)."))
    c = len(list(itertools.combinations("abcd", 2)))
    qs.append(("Kolik různých dvouprvkových skupin (kombinací 2. třídy, na pořadí nezáleží) lze vybrat z {a,b,c,d}?",
               "číslo", str(c), "ab, ac, ad, bc, bd, cd, tedy " + str(c) + "."))
    p = len(list(itertools.permutations("abcd")))
    assert p == 24
    qs.append(("Kolika způsoby lze seřadit 4 různé prvky (n! = n · (n−1) · … · 2 · 1)?", "číslo", str(p),
               "4! = 4 · 3 · 2 · 1 = 24."))
    # kombinační čísla (výpočty ověřeny math.comb i výčtem)
    for n, k in ((6, 2), (7, 3), (10, 8)):
        c = math.comb(n, k)
        assert c == len(list(itertools.combinations(range(n), k))) == math.comb(n, n - k)
        num = " · ".join(str(n - i) for i in range(k))
        qs.append((f"Kolik je C({n}, {k}) = ({n} nad {k})?", "číslo", str(c),
                   f"C({n},{k}) = {n}!/(({n}-{k})!·{k}!) = {num} / {k}! = {c}."
                   + (f" Rychleji přes symetrii: C({n},{k}) = C({n},{n-k}) = {c}." if k > n - k else "")))
    c25, c35 = math.comb(5, 2), math.comb(5, 3)
    assert c25 + c35 == math.comb(6, 3) == 20
    qs.append(("Kolik je C(5,2) + C(5,3) (Pascalovo pravidlo: součet je C(6,3))?", "číslo", str(c25 + c35),
               f"C(5,2) = {c25}, C(5,3) = {c35}, součet {c25 + c35} = C(6,3)."))
    v3 = len(list(itertools.permutations(range(6), 3)))
    assert v3 == 6 * 5 * 4 == math.factorial(6) // math.factorial(3)
    qs.append(("Kolik uspořádaných trojic (bez opakování) lze vybrat ze 6 prvků? (6·5·4! = 6!, k = 3: n·(n−1)·…·(n−k+1))",
               "číslo", str(v3), f"6 · 5 · 4 = {v3} (= 6!/3!)."))
    return main_qs, qs


def build(choice, inputs, rnd, prefix):
    qs = []
    for text, opts, correct, expl in choice:
        text = pripoj_vzorce(text)
        order = list(range(len(opts)))
        rnd.shuffle(order)
        opts = [opts[i] for i in order]
        correct = sorted(order.index(c) for c in correct)
        qs.append({"type": "choice", "text": text,
                   "options": {"ABCD"[i]: o for i, o in enumerate(opts)},
                   "correct": ["ABCD"[i] for i in correct], "explanation": expl})
    for text, hint, ans, sol in inputs:
        qs.append({"type": "input", "text": pripoj_vzorce(text), "hint": hint, "answer": ans, "solution": sol})
    for i, q in enumerate(qs, 1):
        q["number"] = i
        q["id"] = f"{prefix}-{i}"
    return qs


def write(qs, filename, title):
    out = {"title": title, "lecture": 4, "date": "2026-10-22", "questions": qs}
    path = Path(__file__).parent / "banky" / filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_c = sum(q["type"] == "choice" for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({n_c} výběrových, {len(qs) - n_c} na výsledek)")


def main():
    rnd = random.Random(22)  # pevné pořadí, aby správná odpověď nebyla pořád A
    ch_main, ch_komb = choice_questions()
    in_main, in_komb = input_questions()
    write(build(ch_main, in_main, rnd, "4"), "04-2026-10-22.json",
          "Rozklad, třídy ekvivalence a zobrazení")
    write(build(ch_komb, in_komb, rnd, "4k"), "04k-kombinatorika.json",
          "Kombinatorika (kombinace, kombinační číslo, Pascalovo pravidlo)")


if __name__ == "__main__":
    main()
