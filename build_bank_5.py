#!/usr/bin/env python3
"""Vygeneruje banky otázek pro 5. přednášku (29. 10. 2026) do banky/:
05-2026-10-29.json (variace, permutace, kombinace s opakováním i bez, binomická věta, id 5-N)
a 05a-konecne-automaty.json (konečné automaty jako vlastní modul, id 5a-N).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Opus 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází jen z autorových výpisků přednášky 29. 10. 2026 (vault TZI1: Prednasky/2026-10-29.md
a 2026-10-29-konečné automaty.md) včetně ověřených doplňků „Doplněno z Claude“ (definice podle
cs.wikipedia a M. Mareše, Úvod do automatů, kap. 1.2). Nejistě čtená místa rukopisu a jeho chyby se
nepoužívají, jen opravené znění. Odpovědi, výčty i rozvoje se počítají a ověřují zde (itertools, math,
roznásobení (a+b)^n, simulace automatu), ne ručně v JSON. Teorii kontrolovat proti přednášce a sylabu KI/TIN.
Spuštění:  python3 build_bank_5.py
"""
import itertools
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CHECKS = 0


def check(cond, msg=""):
    """assert, který se počítá (na konci se vypíše, kolik kontrol proběhlo)."""
    global CHECKS
    assert cond, msg
    CHECKS += 1


# ── kombinatorika: počty výčtem (itertools) a vzorce z přednášky ─────────────

def V(n, k): return len(list(itertools.permutations(range(n), k)))           # variace bez opakování
def Vo(n, k): return len(list(itertools.product(range(n), repeat=k)))        # V′, s opakováním
def C(n, k): return len(list(itertools.combinations(range(n), k)))
def Co(n, k): return len(list(itertools.combinations_with_replacement(range(n), k)))
def Po(word): return len(set(itertools.permutations(word)))                  # P′ = různá pořadí


fact = math.factorial
def fV(n, k): return fact(n) // fact(n - k)
def fVo(n, k): return n ** k
def fC(n, k): return math.comb(n, k)
def fCo(n, k): return math.comb(n + k - 1, k)
def fPo(*ks): return fact(sum(ks)) // math.prod(fact(x) for x in ks)


def expand(n):
    """(a+b)^n roznásobením závorek: {(exponent a, exponent b): koeficient}, nezávisle na math.comb."""
    poly = {(0, 0): 1}
    for _ in range(n):
        new = Counter()
        for (i, j), c in poly.items():
            new[(i + 1, j)] += c
            new[(i, j + 1)] += c
        poly = dict(new)
    return poly


def verify_formulas():
    check(fact(0) == 1)
    for n in range(8):
        check(V(n, n) == fact(n), f"P({n})")
        for k in range(n + 1):
            check(V(n, k) == fV(n, k), f"V_{k}({n})")
            check(C(n, k) == fC(n, k) == V(n, k) // fact(k), f"C_{k}({n})")
    for n in range(1, 7):
        for k in range(6):
            check(Vo(n, k) == fVo(n, k), f"V'_{k}({n})")
            check(Co(n, k) == fCo(n, k), f"C'_{k}({n})")
    for r in (1, 2, 3):
        for ks in itertools.product(range(1, 4), repeat=r):
            if sum(ks) <= 7:
                check(Po("".join(str(i) * x for i, x in enumerate(ks))) == fPo(*ks), f"P'{ks}")
    for n in range(13):
        check(expand(n) == {(n - k, k): math.comb(n, k) for k in range(n + 1)}, f"(a+b)^{n}")


def tup(t): return "(" + ",".join(map(str, t)) + ")"
def setstr(t): return "{" + ",".join(map(str, t)) + "}"
def joined(ts): return " ".join("".join(map(str, t)) for t in ts)


M = (1, 2, 3)
V23 = sorted(itertools.permutations(M, 2))
VO23 = sorted(itertools.product(M, repeat=2))
P3 = sorted(itertools.permutations(M))
C23 = list(itertools.combinations(M, 2))
CO23 = list(itertools.combinations_with_replacement(M, 2))
P1233 = sorted("".join(p) for p in set(itertools.permutations("1233")))


def verify_lecture_examples():
    """Příklady z rukopisu (opravené znění podle výpisků)."""
    check(set(V23) == {(1, 2), (1, 3), (2, 3), (2, 1), (3, 1), (3, 2)} and len(V23) == fV(3, 2) == 6)
    check(len(VO23) == fVo(3, 2) == 9)
    check(P3 == [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)] and len(P3) == fact(3))
    check(P1233 == "1233 1323 1332 2133 2313 2331 3123 3132 3213 3231 3312 3321".split())
    check(len(P1233) == fPo(1, 1, 2) == 12 and len(list(itertools.permutations("1233"))) == 24)
    # každé pořadí 1, 2, 3, 3 je mezi 4! pořadími s rozlišenými trojkami právě 2!-krát
    check(set(Counter(itertools.permutations("1233")).values()) == {fact(2)})
    check(C23 == [(1, 2), (1, 3), (2, 3)] and len(C23) == fC(3, 2) == fV(3, 2) // fact(2) == 3)
    check(CO23 == [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)] and len(CO23) == fCo(3, 2) == math.comb(4, 2))
    check(len(VO23) - len(V23) == sum(a == b for a, b in VO23) == 3)  # vizualizace: 11, 22, 33
    check([expand(3)[(3 - k, k)] for k in range(4)] == [1, 3, 3, 1])
    check([math.comb(3, k) * 2 ** (3 - k) * 3 ** k for k in range(4)] == [8, 36, 54, 27] and (2 + 3) ** 3 == 125)
    check(Vo(2, 4) == 16 and Co(2, 3) == 4)  # k > n u výběrů s opakováním (výpisky, Wikipedie C′(3,2) = 4)


def binom_terms(n):
    """Rozvoj (a+b)^n: (dosazený tvar, zjednodušený tvar) z roznásobení."""
    poly = expand(n)
    full, short = [], []
    for k in range(n + 1):
        c = poly[(n - k, k)]
        check(c == math.comb(n, k))
        full.append(f"({n} nad {k}) · a^{n - k} · b^{k}")
        pa = "" if n - k == 0 else "a" if n - k == 1 else f"a^{n - k}"
        pb = "" if k == 0 else "b" if k == 1 else f"b^{k}"
        body = "·".join(p for p in (pa, pb) if p)
        short.append((str(c) if c != 1 else "") + body)
    return " + ".join(full), " + ".join(short)


# slovní příklad: možnosti (popis, hodnota), první je správná; hodnota se ověří výčtem a nesmí se shodovat
def word_choice(text, opts, brute, expl):
    vals = [v for _, v in opts]
    check(vals[0] == brute, text)
    check(len(set(vals)) == len(vals), "distraktor má stejnou hodnotu jako správná odpověď: " + text)
    return text, [o for o, _ in opts], [0], expl


# (text, [možnosti], [správné indexy], vysvětlení); správná je vždy první, pořadí se zamíchá
def komb_choice():
    qs = [
        ("Co je variace k-té třídy z n prvků bez opakování?",
         ["uspořádaná k-tice z prvků n-prvkové množiny M, ve které se žádný prvek neopakuje",
          "neuspořádaná k-prvková podmnožina n-prvkové množiny M",
          "uspořádaná k-tice z prvků n-prvkové množiny M, ve které se prvky mohou opakovat",
          "neuspořádaná k-prvková skupina z prvků M, ve které se prvky mohou opakovat"], [0],
         "Variace: záleží na pořadí a žádný prvek se neopakuje (cs.wikipedia, výpisky 29. 10.). Neuspořádaná "
         "podmnožina je kombinace, uspořádaná k-tice s opakováním je variace s opakováním a neuspořádaná "
         "skupina s opakováním je kombinace s opakováním."),
        ("Jaký je vzorec pro počet variací bez opakování V_k(n), 0 ≤ k ≤ n?",
         ["n! / (n−k)!", "n^k", "n! / ((n−k)! · k!)", "(n+k−1 nad k)"], [0],
         "V_k(n) = n! / (n−k)! = n · (n−1) · … · (n−k+1). n^k je V′_k(n), n! / ((n−k)! · k!) = (n nad k) "
         "je C_k(n) a (n+k−1 nad k) je C′_k(n). Příklad z přednášky: V_2(3) = 3! / 1! = 6."),
        ("Jaký je vzorec pro počet variací s opakováním V′_k(n)?",
         ["n^k", "k^n", "n! / (n−k)!", "n · k"], [0],
         "Na každé z k míst lze dát kterýkoli z n prvků nezávisle na ostatních: n · n · … · n = n^k. "
         f"Příklad z přednášky: V′_2(3) = 3^2 = {fVo(3, 2)}."),
        ("Musí u variací s opakováním platit k ≤ n?",
         ["ne, prvky se smějí opakovat, takže k může být i větší než n",
          "ano, jinak by nebylo z čeho vybírat", "ano, pro k > n vzorec n^k neplatí", "ne, ale k musí být sudé"], [0],
         "Podmínka 0 ≤ k ≤ n patří k variacím bez opakování. S opakováním se na každé místo vybírá stále "
         f"ze všech n prvků, např. V′_4(2) = 2^4 = {Vo(2, 4)} (ověřeno výčtem)."),
        ("Jak souvisí variace s opakováním k-té třídy z množiny M s kartézským součinem?",
         ["jsou to přesně prvky kartézského součinu M × M × … × M = M^k (k-krát)",
          "jsou to všechny k-prvkové podmnožiny M", "jsou to prvky potenční množiny Pot(M)",
          "jsou to třídy rozkladu množiny M"], [0],
         "Uspořádaná k-tice, ve které může být na každém místě libovolný prvek M, je prvek M^k. "
         f"Pro M = {{1,2,3}}, k = 2: {{1,2,3}} × {{1,2,3}} má {len(VO23)} dvojic, to je V′_2(3)."),
        ("Co je permutace (bez opakování) n-prvkové množiny M?",
         ["uspořádaná n-tice, která obsahuje každý prvek M právě jednou",
          "uspořádaná n-tice, ve které se prvky mohou opakovat",
          "n-prvková podmnožina M, u níž nezáleží na pořadí", "uspořádaná k-tice pro libovolné k < n"], [0],
         f"Permutace = seřazení všech n prvků, každý právě jednou, P(n) = n!. Pro M = {{1,2,3}}: "
         f"{', '.join(joined([p]) for p in P3)}, tedy 3! = {len(P3)}."),
        ("Proč je P(n) = V_n(n) = n!?",
         ["permutace je variace n-té třídy z n prvků a n! / (n−n)! = n! / 0! = n!, protože 0! = 1",
          "permutace je kombinace n-té třídy a (n nad n) = n!", "V_n(n) = n^n a to se rovná n!",
          "protože (n−n)! = n!"], [0],
         "Permutace je variace, ve které se vybírá všech n prvků (k = n). Dosazením do n! / (n−k)! vyjde "
         "n! / 0! a díky dohodě 0! = 1 je to n!. Kombinační číslo (n nad n) = 1."),
        ("Jaký je vzorec pro počet permutací s opakováním P′_(k_1,…,k_n)(k), kde k = k_1 + … + k_n?",
         ["k! / (k_1! · k_2! · … · k_n!)", "k! · k_1! · k_2! · … · k_n!", "k^n", "(k nad n)"], [0],
         "Všech k míst se seřadí k! způsoby a vydělí se počty prohození stejných prvků k_1!, …, k_n!. "
         f"Příklad z přednášky (1, 2, 3, 3): 4! / (1! · 1! · 2!) = 24 / 2 = {fPo(1, 1, 2)}."),
        ("Co znamená k ve vzorci P′_(k_1,…,k_n)(k) pro permutace s opakováním?",
         ["délku skupiny (počet míst), k = k_1 + k_2 + … + k_n", "počet různých prvků základní množiny M",
          "kolikrát se opakuje prvek a_1", "počet všech permutací s opakováním"], [0],
         "M = {a_1, …, a_n} má n různých prvků, prvek a_i je ve skupině k_i-krát a k = k_1 + … + k_n je "
         "délka skupiny, proto n ≤ k. V příkladu 1, 2, 3, 3 je n = 3 a k = 4."),
        ("Proč se ve vzorci pro permutace s opakováním dělí k_1! · k_2! · … · k_n!?",
         ["prohození stejných prvků mezi sebou nedá nové pořadí, takže každé pořadí je v k! započítané "
          "k_1! · … · k_n!-krát",
          "protože u permutací s opakováním nezáleží na pořadí",
          "protože se každý prvek smí použít nejvýš jednou",
          "protože se odečítají skupiny, ve kterých se žádný prvek neopakuje"], [0],
         "Příklad 1, 2, 3, 3: s rozlišenými trojkami 3_a, 3_b je 4! = 24 pořadí, ale 1 3_a 2 3_b a 1 3_b 2 3_a "
         f"jsou obě 1323. Každé pořadí je tak započítané 2!-krát: 24 / 2 = {fPo(1, 1, 2)}. Na pořadí záleží, "
         "jen stejné prvky nejdou rozlišit."),
        ("Co je kombinace k-té třídy z n prvků s opakováním?",
         ["k-prvková skupina z prvků n-prvkové množiny M, ve které se prvky mohou opakovat a nezáleží na pořadí",
          "k-prvková podmnožina M, ve které se žádný prvek neopakuje",
          "uspořádaná k-tice z prvků M, ve které se prvky mohou opakovat",
          "uspořádaná k-tice z prvků M bez opakování"], [0],
         "Kombinace s opakováním: každý prvek se může opakovat (až k-krát) a nezáleží na pořadí. Pro "
         f"M = {{1,2,3}}, k = 2: {', '.join(setstr(c) for c in CO23)}, tedy {len(CO23)}."),
        ("Jaký je vzorec pro počet kombinací s opakováním C′_k(n)?",
         ["(n+k−1 nad k)", "(n nad k)", "n^k", "(n+k nad k)"], [0],
         "C′_k(n) = (n+k−1 nad k) = (n+k−1)! / (k! · (n−1)!). Příklad z přednášky: C′_2(3) = (3+2−1 nad 2) = "
         f"(4 nad 2) = {fCo(3, 2)}."),
        ("Jak spolu souvisí počet kombinací C_k(n) a počet variací V_k(n) (bez opakování)?",
         ["C_k(n) = V_k(n) / k!, protože každou k-prvkovou skupinu lze seřadit k! způsoby",
          "C_k(n) = V_k(n) · k!", "C_k(n) = V_k(n) / n!", "C_k(n) = V_k(n) − k"], [0],
         "U kombinací je {1,2} = {2,1} jedna skupina, u variací jsou (1,2) a (2,1) dvě. Pro n = 3, k = 2: "
         f"V_2(3) = {fV(3, 2)} a C_2(3) = 6 / 2 = {fC(3, 2)}."),
        ("Podle čeho se u příkladu rozhoduje mezi variací a kombinací?",
         ["zda záleží na pořadí vybraných prvků: ano → variace, ne → kombinace",
          "zda se prvky smějí opakovat: ano → variace, ne → kombinace",
          "zda je k větší než n: ano → variace, ne → kombinace",
          "zda se řadí všechny prvky: ano → kombinace, ne → variace"], [0],
         "Pořadí rozhoduje mezi variací a kombinací (aby se omylem nepoužily variace místo kombinací). "
         "Opakování rozhoduje, zda je to výběr s opakováním (čárka), a řazení všech prvků vede k permutaci."),
        ("Úloha chce seřadit všechny prvky množiny, každý právě jednou. Co použiješ?",
         ["permutaci P(n) = n!", "kombinaci C_n(n) = (n nad n)", "variaci s opakováním V′_n(n) = n^n",
          "kombinaci s opakováním C′_n(n)"], [0],
         "Řadím všechny prvky → permutace (s opakováním, když se některé prvky opakují). C_n(n) = 1 a "
         "V′_n(n) = n^n počítá i n-tice, ve kterých se prvky opakují."),
        ("Co vyjadřuje čárka ve značení V′, P′, C′?",
         ["že jde o výběr s opakováním (prvky se mohou opakovat)", "že nezáleží na pořadí",
          "že se vybírají všechny prvky", "že jde o doplněk množiny"], [0],
         "V′, P′, C′ = variace, permutace a kombinace s opakováním. (Doplněk množiny A′ z 15. 10. je jiný význam čárky.)"),
        ("Jak zní binomická věta?",
         ["(a+b)^n = součet přes k = 0, 1, …, n členů (n nad k) · a^(n−k) · b^k",
          "(a+b)^n = a^n + b^n",
          "(a+b)^n = součet přes k = 0, 1, …, n členů (n nad k) · a^n · b^k",
          "(a+b)^n = součet přes k = 0, 1, …, n členů k · a^(n−k) · b^k"], [0],
         "cs.wikipedia (Binomická věta), výpisky 29. 10.: (a+b)^n = Σ (n nad k) · a^(n−k) · b^k pro k = 0, …, n. "
         f"Pro n = 3: {binom_terms(3)[1]}."),
        ("Jak se v rozvoji (a+b)^n = Σ (n nad k) · a^(n−k) · b^k mění exponenty?",
         ["u a klesá od n do 0, u b roste od 0 do n a součet exponentů je v každém členu n",
          "u a i u b roste od 0 do n", "u a je stále n, u b roste od 0 do n", "součet exponentů v členu je k"], [0],
         "Člen (n nad k) · a^(n−k) · b^k má součet exponentů (n−k) + k = n. Koeficient (n nad k) patří "
         "k exponentu k u b."),
        ("Proč je u členu a^(n−k) · b^k v rozvoji (a+b)^n koeficient (n nad k)?",
         ["při roznásobení n závorek (a+b) se vybírá, ze kterých k závorek se vezme b, a na pořadí závorek nezáleží",
          "protože každý člen vznikne při roznásobení právě jednou", "protože b^k vznikne k! způsoby",
          "protože exponenty u a klesají"], [0],
         "Z každé závorky se bere a nebo b. Člen a^(n−k) · b^k vznikne tolikrát, kolika způsoby lze vybrat k závorek "
         f"z n (kombinace k-té třídy), tedy (n nad k). Pro n = 3, k = 1: 3 způsoby, proto 3a^2·b."),
    ]
    # rozlišení typů na slovních příkladech
    qs += [
        word_choice("Čtyřmístný PIN se skládá z číslic 0 až 9 a číslice se mohou opakovat. Čím se spočítá počet PINů?",
                    [("variace s opakováním V′_4(10) = 10^4", fVo(10, 4)),
                     ("variace bez opakování V_4(10) = 10! / 6!", fV(10, 4)),
                     ("kombinace C_4(10) = (10 nad 4)", fC(10, 4)),
                     ("kombinace s opakováním C′_4(10) = (13 nad 4)", fCo(10, 4))], Vo(10, 4),
                    f"Záleží na pořadí (1234 ≠ 4321) a číslice se smějí opakovat → variace s opakováním: "
                    f"10^4 = {fVo(10, 4)}."),
        word_choice("Ze 20 studentů se volí předseda, místopředseda a pokladník (každý nejvýš jednu funkci). "
                    "Čím se spočítá počet možností?",
                    [("variace bez opakování V_3(20) = 20! / 17!", fV(20, 3)),
                     ("kombinace C_3(20) = (20 nad 3)", fC(20, 3)),
                     ("variace s opakováním V′_3(20) = 20^3", fVo(20, 3)),
                     ("permutace P(20) = 20!", fact(20))], V(20, 3),
                    f"Záleží na pořadí (funkce se liší) a nikdo nemá dvě funkce → variace bez opakování: "
                    f"20 · 19 · 18 = {fV(20, 3)}."),
        word_choice("Ze 20 studentů se vybírá tříčlenná komise, členové jsou si rovni. Čím se spočítá počet možností?",
                    [("kombinace C_3(20) = (20 nad 3)", fC(20, 3)),
                     ("variace bez opakování V_3(20) = 20! / 17!", fV(20, 3)),
                     ("kombinace s opakováním C′_3(20) = (22 nad 3)", fCo(20, 3)),
                     ("permutace P(3) = 3!", fact(3))], C(20, 3),
                    f"Na pořadí nezáleží a nikdo nemůže být v komisi dvakrát → kombinace: (20 nad 3) = {fC(20, 3)}."),
        word_choice("V cukrárně mají 5 druhů zákusků a kupuješ 3 zákusky. Druhy se mohou opakovat a na pořadí "
                    "nezáleží. Čím se spočítá počet možností?",
                    [("kombinace s opakováním C′_3(5) = (7 nad 3)", fCo(5, 3)),
                     ("kombinace C_3(5) = (5 nad 3)", fC(5, 3)),
                     ("variace s opakováním V′_3(5) = 5^3", fVo(5, 3)),
                     ("variace bez opakování V_3(5) = 5! / 2!", fV(5, 3))], Co(5, 3),
                    f"Nezáleží na pořadí a druhy se opakují → kombinace s opakováním: (5+3−1 nad 3) = (7 nad 3) = {fCo(5, 3)}."),
        word_choice("Kolika způsoby lze seřadit 6 různých knih na poličku? Čím se to spočítá?",
                    [("permutace P(6) = 6!", fact(6)),
                     ("variace s opakováním V′_6(6) = 6^6", fVo(6, 6)),
                     ("kombinace C_6(6) = (6 nad 6)", fC(6, 6)),
                     ("permutace s opakováním P′_(3,3)(6) = 6! / (3! · 3!)", fPo(3, 3))], V(6, 6),
                    f"Řadí se všechny knihy, každá jednou → permutace: 6! = {fact(6)}."),
        word_choice("Kolik různých pořadí písmen má slovo MAMA? Čím se to spočítá?",
                    [("permutace s opakováním P′_(2,2)(4) = 4! / (2! · 2!)", fPo(2, 2)),
                     ("permutace P(4) = 4!", fact(4)),
                     ("variace s opakováním V′_4(2) = 2^4", fVo(2, 4)),
                     ("variace bez opakování V_2(4) = 4! / 2!", fV(4, 2))], Po("MAMA"),
                    f"Řadí se všechna 4 písmena, M i A jsou dvakrát → permutace s opakováním: 4! / (2! · 2!) = "
                    f"24 / 4 = {fPo(2, 2)} (AAMM, AMAM, AMMA, MAAM, MAMA, MMAA)."),
    ]
    check(sorted("".join(p) for p in set(itertools.permutations("MAMA"))) == "AAMM AMAM AMMA MAAM MAMA MMAA".split())
    return qs


# (text, hint, answer, řešení)
def komb_input():
    qs = []
    # dosazení do vzorců (značení z přednášky)
    qs.append(("Kolik je V_3(5), počet variací 3. třídy z 5 prvků bez opakování?", "číslo", str(V(5, 3)),
               f"V_3(5) = 5! / (5−3)! = 5 · 4 · 3 = {fV(5, 3)}."))
    qs.append(("Kolik je V′_3(4), počet variací 3. třídy ze 4 prvků s opakováním?", "číslo", str(Vo(4, 3)),
               f"V′_3(4) = 4^3 = {fVo(4, 3)}."))
    qs.append(("Kolik je V′_4(2), počet uspořádaných čtveřic ze 2 prvků s opakováním? (k může být větší než n)",
               "číslo", str(Vo(2, 4)), f"V′_4(2) = 2^4 = {fVo(2, 4)}. S opakováním podmínka k ≤ n neplatí."))
    qs.append(("Kolik je P(5), počet permutací 5 prvků?", "číslo", str(V(5, 5)), f"P(5) = 5! = 5 · 4 · 3 · 2 · 1 = {fact(5)}."))
    qs.append(("Základní množina M = {1, 2, 3}, první prvek se opakuje jednou, druhý také jednou a třetí dvakrát. "
               "Kolik je permutací s opakováním P′_(1,1,2)(4)?", "číslo", str(len(P1233)),
               f"P′_(1,1,2)(4) = 4! / (1! · 1! · 2!) = 24 / 2 = {fPo(1, 1, 2)}:\n{', '.join(P1233)}"))
    qs.append(("Kolik různých pořadí mají čísla 1, 1, 2, 2, 2 (P′_(2,3)(5))?", "číslo", str(Po("11222")),
               f"P′_(2,3)(5) = 5! / (2! · 3!) = 120 / 12 = {fPo(2, 3)}."))
    qs.append(("Kolik je C′_2(3), počet kombinací 2. třídy s opakováním z M = {1, 2, 3}?", "číslo", str(len(CO23)),
               f"C′_2(3) = (3+2−1 nad 2) = (4 nad 2) = {fCo(3, 2)}: {', '.join(setstr(c) for c in CO23)}."))
    qs.append(("Kolik je C′_3(5), počet kombinací 3. třídy s opakováním z 5 prvků?", "číslo", str(Co(5, 3)),
               f"C′_3(5) = (5+3−1 nad 3) = (7 nad 3) = 7 · 6 · 5 / 3! = {fCo(5, 3)}."))
    co32 = list(itertools.combinations_with_replacement((1, 2), 3))
    qs.append(("Kolik je C′_3(2), počet kombinací 3. třídy s opakováním ze 2 prvků? (k může být větší než n)",
               "číslo", str(len(co32)),
               f"C′_3(2) = (2+3−1 nad 3) = (4 nad 3) = {fCo(2, 3)}: {', '.join(setstr(c) for c in co32)}."))
    # výčty pro M = {1, 2, 3} (porovnání bez mezer, pořadí vzestupně)
    h_pair = "každou dvojici jako dvojčíslí (např. (4,5) jako 45), dvojice vzestupně, oddělené mezerou"
    h_set = "každou dvojici od menšího čísla (např. {4,5} jako 45), dvojice vzestupně, oddělené mezerou"
    qs.append(("Vypiš všechny variace 2. třídy bez opakování z M = {1, 2, 3}.", h_pair, joined(V23),
               f"V_2(3) = {{{', '.join(tup(t) for t in V23)}}}, celkem 3! / 1! = {len(V23)}."))
    qs.append(("Vypiš všechny variace 2. třídy s opakováním z M = {1, 2, 3}.", h_pair, joined(VO23),
               f"V′_2(3) = {{1,2,3}} × {{1,2,3}} = {{{', '.join(tup(t) for t in VO23)}}}, celkem 3^2 = {len(VO23)}."))
    qs.append(("Vypiš všechny permutace množiny M = {1, 2, 3}.",
               "každou trojici jako trojčíslí (např. (4,5,6) jako 456), vzestupně, oddělené mezerou", joined(P3),
               f"P(3) = {{{', '.join(tup(t) for t in P3)}}}, celkem 3! = {len(P3)}."))
    qs.append(("Vypiš všechny kombinace 2. třídy bez opakování z M = {1, 2, 3}.", h_set, joined(C23),
               f"C_2(3) = {', '.join(setstr(t) for t in C23)}, celkem (3 nad 2) = {len(C23)}."))
    qs.append(("Vypiš všechny kombinace 2. třídy s opakováním z M = {1, 2, 3}.", h_set, joined(CO23),
               f"C′_2(3) = {', '.join(setstr(t) for t in CO23)}, celkem (4 nad 2) = {len(CO23)}. "
               "Na pořadí nezáleží, {1,2} a {2,1} je tatáž skupina."))
    same = [t for t in VO23 if t[0] == t[1]]
    qs.append(("Kolik z 9 variací s opakováním V′_2(3) z M = {1, 2, 3} má oba prvky stejné?", "číslo", str(len(same)),
               f"{', '.join(tup(t) for t in same)}. Bez nich zbude {len(VO23) - len(same)} variací bez opakování V_2(3)."))
    # slovní příklady na výsledek
    qs.append(("Kolik trojmístných kódů lze sestavit z číslic 1 až 5, když se číslice mohou opakovat?", "číslo",
               str(Vo(5, 3)), f"Záleží na pořadí, opakování povoleno → V′_3(5) = 5^3 = {fVo(5, 3)}."))
    qs.append(("Závodu se účastní 8 běžců. Kolika způsoby lze rozdělit zlatou, stříbrnou a bronzovou medaili?",
               "číslo", str(V(8, 3)),
               f"Záleží na pořadí (zlato ≠ stříbro), nikdo nemá dvě medaile → V_3(8) = 8 · 7 · 6 = {fV(8, 3)}."))
    qs.append(("Kolika způsoby lze z 10 otázek vybrat 4 do testu, když na pořadí nezáleží?", "číslo", str(C(10, 4)),
               f"Nezáleží na pořadí, bez opakování → C_4(10) = (10 nad 4) = 10 · 9 · 8 · 7 / 4! = {fC(10, 4)}."))
    qs.append(("V pekárně mají 3 druhy koláčů a kupuješ 4 koláče. Druhy se mohou opakovat a na pořadí nezáleží. "
               "Kolik je možností?", "číslo", str(Co(3, 4)),
               f"Kombinace s opakováním (k > n je tu v pořádku): C′_4(3) = (3+4−1 nad 4) = (6 nad 4) = {fCo(3, 4)}."))
    qs.append(("Kolik různých pořadí písmen má slovo KOLO?", "číslo", str(Po("KOLO")),
               f"Řadí se všechna 4 písmena, O je dvakrát → P′_(1,2,1)(4) = 4! / (1! · 2! · 1!) = 24 / 2 = {fPo(1, 2, 1)}."))
    # binomická věta
    p5 = expand(5)
    qs.append(("Jaký koeficient má člen a^2 · b^3 v rozvoji (a+b)^5?", "číslo", str(p5[(2, 3)]),
               f"Exponent u b je k = 3: (5 nad 3) = 5 · 4 · 3 / 3! = {math.comb(5, 3)}."))
    p4 = expand(4)
    qs.append(("Napiš koeficienty rozvoje (a+b)^4 od členu a^4 po b^4.", "čísla oddělená mezerou",
               " ".join(str(p4[(4 - k, k)]) for k in range(5)),
               f"(4 nad 0), (4 nad 1), …, (4 nad 4) = {', '.join(str(p4[(4 - k, k)]) for k in range(5))}.\n"
               f"(a+b)^4 = {binom_terms(4)[1]}"))
    qs.append(("Kolik sčítanců má rozvoj (a+b)^7 podle binomické věty?", "číslo", str(len(expand(7))),
               f"k = 0, 1, …, 7, tedy n + 1 = {len(expand(7))} sčítanců."))
    t2 = math.comb(3, 2) * 2 ** 1 * 3 ** 2
    qs.append(("Spočítej člen pro k = 2 v rozvoji (2+3)^3 podle binomické věty.", "číslo", str(t2),
               f"(3 nad 2) · 2^1 · 3^2 = 3 · 2 · 9 = {t2}. Celý rozvoj: 8 + 36 + 54 + 27 = 125 = 5^3."))
    return qs


# zadání bez políčka: řešení se odhalí, hodnotí se sám (reveal)
def komb_reveal():
    full4, short4 = binom_terms(4)
    return [
        ("Ukaž na příkladu M = {1, 2, 3}, k = 2, proč je variací bez opakování 6, a vypiš je.",
         f"První místo lze obsadit 3 způsoby, druhé už jen 2 (prvek se nesmí opakovat): 3 · 2 = {fV(3, 2)}.\n"
         f"V_2(3) = {{{', '.join(tup(t) for t in V23)}}}\n"
         "Obecně n · (n−1) · … · (n−k+1) = n! / (n−k)!, tady 3! / 1! = 6."),
        ("Vysvětli na příkladu řazení čísel 1, 2, 3, 3, proč je permutací s opakováním 12, a ne 4! = 24.",
         "1. Kdyby byly trojky různé (3_a, 3_b), byla by to obyčejná permutace 4 prvků: 4! = 24 pořadí.\n"
         "2. Trojky ale rozlišit nejde: 1 3_a 2 3_b a 1 3_b 2 3_a jsou obě 1323. Každé pořadí je tak započítané "
         "tolikrát, kolika způsoby lze mezi sebou proházet stejné prvky: 2! = 2krát.\n"
         f"3. Proto 4! / (1! · 1! · 2!) = 24 / 2 = {fPo(1, 1, 2)}. Prvky, které tam jsou jednou, dávají 1! = 1.\n"
         f"Všech {len(P1233)} pořadí: {', '.join(P1233)}."),
        ("Rozepiš (a+b)^4 podle binomické věty.",
         f"(a+b)^4 = {full4}\n= {short4}\n"
         "Exponent u a klesá od 4 do 0, u b roste od 0 do 4, koeficienty jsou (4 nad k)."),
    ]


# ── konečné automaty ──────────────────────────────────────────────────────────

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
def s(q): return q.translate(SUB)  # q0 → q₀ (jen v textu, odpovědi se píšou q0)


AQ, AS, AF = ["q0", "q1", "q2", "q3"], ["0", "1"], {"q1", "q2"}
AD = {("q0", "0"): "q0", ("q0", "1"): "q2", ("q1", "0"): "q1", ("q1", "1"): "q3",   # fotka tabule
      ("q2", "0"): "q1", ("q2", "1"): "q3", ("q3", "0"): "q1", ("q3", "1"): "q3"}
BQ, BS, BF = ["q0", "q1"], ["0", "1"], {"q0"}
BD = {("q0", "0"): "q0", ("q0", "1"): "q1", ("q1", "0"): "q1", ("q1", "1"): "q0"}
DQ, DS = ["zavřeno", "otevřeno"], ["vstup", "odchod"]
DD = {("zavřeno", "vstup"): "otevřeno", ("otevřeno", "odchod"): "zavřeno",       # z přednášky
      ("zavřeno", "odchod"): "zavřeno", ("otevřeno", "vstup"): "otevřeno"}        # doplněno ve výpiscích (*)
D_LECTURE = {("zavřeno", "vstup"), ("otevřeno", "odchod")}


def run(D, start, word):
    """Simulace: posloupnost stavů od počátečního po přečtení celého slova."""
    st = [start]
    for c in word:
        st.append(D[(st[-1], c)])
    return st


def delta_list(D, Q, S):
    return ", ".join(f"δ({s(q)}, {a}) = {s(D[(q, a)])}" for q in Q for a in S)


def path_text(D, start, word):
    st = run(D, start, word)
    return ", ".join(f"δ({s(st[i])}, {c}) = {s(st[i + 1])}" for i, c in enumerate(word))


def verdict(st, F):
    return f"konec v {s(st[-1])} ∈ F → přijato" if st[-1] in F else f"konec v {s(st[-1])} ∉ F → nepřijato"


def state_tree(D, Q, S, start):
    """Stavový strom podle přednášky: rozvíjí se jen stav, který ve stromu ještě nebyl."""
    seen, queue, rows = {start}, [start], []
    while queue:
        q = queue.pop(0)
        kids = []
        for a in S:
            r = D[(q, a)]
            kids.append((a, r, r in seen))
            if r not in seen:
                seen.add(r)
                queue.append(r)
        rows.append((q, kids))
    return rows


TAB = (f"Automat z přednášky: Q = {{q₀, q₁, q₂, q₃}}, Σ = {{0, 1}}, počáteční stav q₀, F = {{q₁, q₂}}, "
       f"{delta_list(AD, AQ, AS)}.")
TAB_B = (f"Automat: Q = {{q₀, q₁}}, Σ = {{0, 1}}, počáteční stav q₀, F = {{q₀}}, {delta_list(BD, BQ, BS)}.")


def verify_automata():
    for D, Q, S in ((AD, AQ, AS), (BD, BQ, BS), (DD, DQ, DS)):
        check(set(D) == set(itertools.product(Q, S)), "deterministický: každý stav × znak právě jeden přechod")
        check(set(D.values()) <= set(Q))
    check(len(AD) == len(AQ) * len(AS) == 8)
    st = run(AD, "q0", "1011010")
    check(st == "q0 q2 q1 q3 q3 q1 q3 q1".split() and st[-1] in AF)  # řádek „TADY JSME TO SLOVO PŘEČETLI“
    rows = state_tree(AD, AQ, AS, "q0")
    check([(q, a, r) for q, kids in rows for a, r, _ in kids] ==
          [("q0", "0", "q0"), ("q0", "1", "q2"), ("q2", "0", "q1"), ("q2", "1", "q3"),
           ("q1", "0", "q1"), ("q1", "1", "q3"), ("q3", "0", "q1"), ("q3", "1", "q3")])  # strom ve výpiscích
    check({q for q, _ in rows} == set(AQ))
    st = run(AD, "q0", "011")
    check("q2" in st and st[-1] not in AF)  # vysvětlení „Kdy automat slovo přijme?“
    check(run(DD, "zavřeno", ["vstup"])[-1] == "otevřeno" and run(DD, "otevřeno", ["odchod"])[-1] == "zavřeno")


def auto_choice():
    path = run(DD, "zavřeno", ["vstup", "odchod", "vstup"])
    used = set(zip(path, ["vstup", "odchod", "vstup"]))
    check(used <= D_LECTURE, "cesta používá jen přechody z přednášky")
    wrong = [["zavřeno", "otevřeno", "otevřeno", "otevřeno"], ["zavřeno", "zavřeno", "otevřeno", "zavřeno"],
             ["zavřeno", "otevřeno", "zavřeno", "zavřeno"]]
    check(all(w != path for w in wrong) and len({tuple(w) for w in wrong}) == 3)
    arrow = lambda p: " → ".join(p)
    return [
        ("Co tvoří pětici A = (Q, Σ, δ, q₀, F) konečného automatu?",
         ["stavy, abeceda, přechodová funkce, počáteční stav, množina přijímacích stavů",
          "stavy, abeceda, přechodová funkce, koncový stav, množina počátečních stavů",
          "abeceda, slova, množina přechodů, počáteční znak, přijímací znaky",
          "stavy, slova, přechodová funkce, počáteční slovo, přijímaná slova"], [0],
         "Konečným automatem nazýváme každou uspořádanou pětici A = (Q, Σ, δ, q₀, F): Q stavy, Σ abeceda, "
         "δ přechodová funkce, q₀ počáteční stav, F množina přijímacích (koncových) stavů (Mareš, kap. 1.2)."),
        ("Co je Q v pětici konečného automatu?",
         ["konečná neprázdná množina stavů", "konečná neprázdná množina znaků (abeceda)",
          "množina přijímacích stavů", "přechodová funkce"], [0],
         "Q = {q₀, q₁, …} je konečná neprázdná množina stavů (Mareš, kap. 1.2). Abeceda je Σ, přijímací stavy F ⊆ Q, "
         "přechodová funkce δ."),
        ("Co je Σ (velká sigma) v pětici konečného automatu?",
         ["konečná neprázdná množina znaků, vstupní abeceda", "množina stavů",
          "součet všech stavů", "množina přijímacích stavů"], [0],
         "Σ je konečná neprázdná množina znaků, (vstupní) abeceda, např. Σ = {0, 1} (Mareš, kap. 1.2)."),
        ("Co je δ (malá delta) v pětici konečného automatu?",
         ["přechodová funkce δ : Q × Σ → Q, pro každý stav a znak ze vstupu určí, do jakého stavu automat přejde",
          "konečná neprázdná množina znaků, ze kterých se skládá vstupní slovo",
          "množina stavů, ve kterých když výpočet skončí, je slovo přijato",
          "počáteční stav, ve kterém automat začíná číst slovo"], [0],
         "δ je přechodová funkce (zobrazení) δ : Q × Σ → Q (Mareš, kap. 1.2)."),
        ("Co je q₀ v pětici konečného automatu?",
         ["počáteční stav, q₀ ∈ Q", "první znak vstupního slova", "přijímací stav, q₀ ∈ F", "množina všech stavů"], [0],
         "q₀ je počáteční stav, q₀ ∈ Q. Přijímací být nemusí: v příkladu z přednášky je F = {q₁, q₂}."),
        ("Co je F v pětici konečného automatu?",
         ["množina přijímacích (koncových) stavů, F ⊆ Q", "jeden koncový znak abecedy", "přechodová funkce",
          "množina všech slov, která automat přečte"], [0],
         "F ⊆ Q je množina přijímacích (koncových) stavů (Mareš, kap. 1.2). V příkladu z přednášky F = {q₁, q₂}."),
        ("Jak se čte zápis δ : Q × Σ → Q?",
         ["delta je zobrazení z Q krát sigma do Q", "delta je zobrazení z Q do Q krát sigma",
          "delta je prvek množiny Q krát sigma", "Q krát sigma je zobrazení do delta"], [0],
         "δ je jméno zobrazení, „:“ = „je zobrazení z … do …“, Q × Σ jsou dvojice (stav, znak), → Q: výsledkem je stav."),
        ("Co jsou prvky množiny Q × Σ, na které je definovaná přechodová funkce δ?",
         ["všechny dvojice (stav, znak)", "všechny stavy automatu", "všechny znaky abecedy",
          "všechna slova nad abecedou Σ"], [0],
         "Q × Σ je kartézský součin (přednáška 15. 10.): dvojice (q, a), kde q ∈ Q a a ∈ Σ, např. (q₀, 1) "
         "u automatu z přednášky."),
        ("Proč je přechodová funkce δ : Q × Σ → Q zobrazení?",
         ["každé dvojici (stav, znak) přiřadí právě jeden stav", "každému stavu přiřadí právě jeden znak",
          "každé dvojici (stav, znak) přiřadí aspoň jeden stav, může i víc", "každému znaku přiřadí množinu stavů"], [0],
         "Zobrazení (přednáška 22. 10.) přiřadí každému prvku právě jeden obraz. Na náčrtu z přednášky vede z každé "
         "dvojice v Q × Σ právě jedna šipka do Q."),
        ("Co znamená zápis δ(q, a) = q′?",
         ["automat ve stavu q přečte znak a a přejde do stavu q′",
          "automat ve stavu q′ přečte znak a a přejde do stavu q",
          "stav q se přepíše na znak a", "q, a i q′ jsou znaky abecedy"], [0],
         "δ(q, a) = q′, kde q, q′ ∈ Q a a ∈ Σ (zápis z tabule): ve stavu q přečte a, přejde do q′."),
        ("Co musí splňovat přechody deterministického konečného automatu?",
         ["každý stav má pro každý vstupní symbol právě jeden přechod",
          "každý stav má aspoň jeden přechod, pro některé symboly může chybět",
          "ze stavu může pro jeden symbol vést víc přechodů", "přechody stačí zadat jen z počátečního stavu"], [0],
         "Mareš, kap. 1.2: δ pro každý stav a znak určí, kam automat přejde; v grafu z každého vrcholu vede pro každý "
         f"znak abecedy právě jedna hrana. Automat z přednášky: {len(AQ)} · {len(AS)} = {len(AD)} přechodů, všechny zadané."),
        ("Co je stavový (přechodový) diagram konečného automatu?",
         ["orientovaný graf: vrcholy jsou stavy, hrana z q do q′ je označená znakem a, když δ(q, a) = q′",
          "tabulka, ve které řádky jsou stavy a sloupce znaky", "výčet všech δ(q, a) = q′ pod sebou",
          "seznam všech přijímaných slov"], [0],
         "„Tabulka jako orientovaný graf“: vrcholy = stavy, hrany podle δ; počáteční stav má šipku zvenku, přijímací "
         "se zvýrazní (dvojitý kroužek). Tabulka a výčet δ jsou jiné zápisy téhož automatu."),
        ("Kolik hran vede ve stavovém diagramu deterministického konečného automatu z každého vrcholu?",
         ["pro každý znak abecedy právě jedna", "právě jedna, bez ohledu na abecedu",
          "nejvýš jedna pro každý znak", "tolik, kolik je stavů"], [0],
         "Mareš, kap. 1.2: z každého vrcholu vede pro každý znak abecedy právě jedna hrana. Při Σ = {0, 1} tedy "
         "dvě (může to být i smyčka zpět do téhož stavu)."),
        ("Co je v tabulce přechodů v řádku stavu q a ve sloupci znaku a?",
         ["stav δ(q, a), do kterého automat přejde", "znak, který automat přečte jako další",
          "počet přechodů ze stavu q", "informace, zda je q přijímací stav"], [0],
         "Řádky = stavy, sloupce = znaky abecedy, v políčku δ(q, a). Tabulka má |Q| · |Σ| políček."),
        ("Jak jsou v tabulce přechodů z přednášky označené počáteční a přijímací stavy?",
         ["počáteční šipkou →, přijímací šipkou ←", "počáteční šipkou ←, přijímací šipkou →",
          "počáteční hvězdičkou, přijímací podtržením", "počáteční i přijímací stejnou šipkou →"], [0],
         "Tabulka z přednášky: → q₀ (počáteční), ← q₁ a ← q₂ (přijímací, F = {q₁, q₂})."),
        ("Kdy automat slovo přijme?",
         ["když výpočet po přečtení celého slova skončí ve stavu z F",
          "když výpočet během čtení projde aspoň jedním stavem z F",
          "když výpočet skončí v počátečním stavu q₀", "když slovo obsahuje jen znaky abecedy Σ"], [0],
         f"Rozhoduje stav po přečtení celého slova (Mareš, kap. 1.2). Slovo 1011010: {s(st_word('1011010'))} ∈ F, přijato. "
         f"Slovo 011 projde q₂ ∈ F, ale skončí v {s(run(AD, 'q0', '011')[-1])} ∉ F, nepřijato."),
        ("Jaké je podle přednášky hlavní poslání konečného automatu?",
         ["o libovolném slově z nul a jedniček rozhodnout, zda ho přijme (rozpozná), nebo ne",
          "spočítat, kolik je ve slově jedniček", "převést slovo do desítkové soustavy",
          "vypsat všechny stavy v abecedním pořadí"], [0],
         "Přednáška: hlavní poslání je rozpoznat libovolnou kombinaci jedniček a nul a rozhodnout, zda je nebo není "
         "rozpoznatelná. Odborně: slovo je přijato, když výpočet skončí ve stavu z F."),
        ("Jak se podle přednášky doporučuje navrhovat konečný automat?",
         ["nejdřív stavový diagram, potom přechodové funkce, tabulka a stavový strom",
          "nejdřív stavový strom, z něj tabulka a nakonec diagram", "jen tabulkou, diagram se nekreslí",
          "nejdřív seznam přijímaných slov, potom tabulka"], [0],
         "Přednáška: při návrhu konečného automatu se doporučuje začít stavovým diagramem a pak doplnit přechodové "
         "funkce, tabulku a stavový strom."),
        ("Co je kořenem stavového stromu automatu?",
         ["počáteční stav q₀", "libovolný přijímací stav", "poslední přečtený znak", "stav s nejvíce přechody"], [0],
         "Strom z přednášky začíná šipkou do q₀ a z q₀ vedou větve pro každý znak do stavu podle δ."),
        ("Vstupní dveře jako konečný automat (příklad z přednášky): stavy jsou zavřeno a otevřeno. "
         "Co tvoří vstupní abecedu Σ?",
         ["události vstup a odchod", "stavy zavřeno a otevřeno", "jediný znak „dveře“", "počet lidí, kteří prošli"], [0],
         "Když vstoupíme, dveře se otevřou, když odejdeme, zavřou se. Události jsou vstupní znaky, Σ = {vstup, odchod}, "
         "Q = {zavřeno, otevřeno}, q₀ = zavřeno (zápis z výpisků)."),
        ("Dveře: Q = {zavřeno, otevřeno}, Σ = {vstup, odchod}. Z přednášky jsou jen přechody "
         "δ(zavřeno, vstup) = otevřeno a δ(otevřeno, odchod) = zavřeno. Proč je třeba doplnit i "
         "δ(zavřeno, odchod) a δ(otevřeno, vstup)?",
         ["deterministický automat musí mít pro každý stav a každý znak právě jeden přechod",
          "aby měl automat víc přijímacích stavů", "protože každý stav musí mít smyčku",
          "aby se dveře nikdy nezavřely"], [0],
         f"Úplná tabulka má |Q| · |Σ| = 2 · 2 = {len(DD)} políčka. Ve výpiscích jsou doplněná tak, že se stav nezmění "
         "(je to návrh, přesný model vyučujícího výpisky neznají)."),
        ("Dveře (q₀ = zavřeno, δ(zavřeno, vstup) = otevřeno, δ(otevřeno, odchod) = zavřeno) dostanou události "
         "vstup, odchod, vstup. Kudy vede výpočet?",
         [arrow(path)] + [arrow(w) for w in wrong], [0],
         f"δ(zavřeno, vstup) = otevřeno, δ(otevřeno, odchod) = zavřeno, δ(zavřeno, vstup) = otevřeno: {arrow(path)}."),
    ]


def st_word(word):
    return run(AD, "q0", word)[-1]


def auto_input():
    qs = []
    h_state = "stav jako q a číslo, např. q7"
    for q, a in (("q0", "1"), ("q2", "0")):
        qs.append((f"{TAB} Čemu se rovná δ({s(q)}, {a})?", h_state, AD[(q, a)],
                   f"Řádek {s(q)}, sloupec {a} tabulky: δ({s(q)}, {a}) = {s(AD[(q, a)])}."))
    st = run(AD, "q0", "1011010")
    qs.append((f"{TAB} Automat čte slovo 1011010. Napiš posloupnost stavů od q₀ po poslední stav.",
               "stavy oddělené mezerou, bez čárek, např. q0 q3 q1", " ".join(st),
               f"{path_text(AD, 'q0', '1011010')}\n{' '.join(s(x) for x in st)}, {verdict(st, AF)}"))
    for w in ("1011010", "011", "000"):
        st = run(AD, "q0", w)
        qs.append((f"{TAB} Přijme automat slovo {w}?", "ano / ne", "ano" if st[-1] in AF else "ne",
                   f"{path_text(AD, 'q0', w)}\n{verdict(st, AF)}"
                   + (" (počáteční stav q₀ není přijímací)" if st[-1] == "q0" else "")))
    st = run(AD, "q0", "0001")
    qs.append((f"{TAB} Ve kterém stavu automat skončí po přečtení slova 0001?", h_state, st[-1],
               f"{path_text(AD, 'q0', '0001')}\nKonec v {s(st[-1])}."))
    words = ["1", "10", "11", "0110", "1101"]
    bits = "".join("1" if run(AD, "q0", w)[-1] in AF else "0" for w in words)
    qs.append((f"{TAB} Pro slova {', '.join(words)} napiš 1 (přijato) nebo 0 (nepřijato), v tomto pořadí bez mezer.",
               "pět cifer, např. 10011", bits,
               "\n".join(f"{w}: {path_text(AD, 'q0', w)}, {verdict(run(AD, 'q0', w), AF)}" for w in words)))
    qs.append(("Kolik přechodů (vyplněných políček tabulky) má deterministický konečný automat z přednášky, "
               "Q = {q₀, q₁, q₂, q₃}, Σ = {0, 1}?", "číslo", str(len(AD)),
               f"Pro každý stav a každý znak právě jeden přechod: |Q| · |Σ| = 4 · 2 = {len(AD)}."))
    loops = [(q, a) for (q, a), r in AD.items() if q == r]
    qs.append((f"{TAB} Kolik smyček (hran ze stavu zpět do téhož stavu) má stavový diagram tohoto automatu?",
               "číslo", str(len(loops)),
               ", ".join(f"δ({s(q)}, {a}) = {s(q)}" for q, a in loops) + f", tedy {len(loops)}."))
    given = {("q0", "a"): "q1", ("q0", "b"): "q0", ("q1", "a"): "q1"}
    missing = sorted(set(itertools.product(["q0", "q1"], ["a", "b"])) - set(given))
    qs.append(("Automat má Q = {q₀, q₁}, Σ = {a, b} a zadané přechody δ(q₀, a) = q₁, δ(q₀, b) = q₀, δ(q₁, a) = q₁. "
               "Kolik přechodů chybí, aby to byl deterministický konečný automat?", "číslo", str(len(missing)),
               f"Potřeba |Q| · |Σ| = 2 · 2 = 4 přechody (každý stav pro každý znak právě jeden), zadané {len(given)}, "
               f"chybí {', '.join(f'δ({s(q)}, {a})' for q, a in missing)}."))
    st = run(BD, "q0", "1101")
    qs.append((f"{TAB_B} Ve kterém stavu automat skončí po přečtení slova 1101?", h_state, st[-1],
               f"{path_text(BD, 'q0', '1101')}\nKonec v {s(st[-1])}."))
    st = run(BD, "q0", "0110")
    qs.append((f"{TAB_B} Přijme automat slovo 0110?", "ano / ne", "ano" if st[-1] in BF else "ne",
               f"{path_text(BD, 'q0', '0110')}\n{verdict(st, BF)}"))
    qs.append(("Vstupní dveře jako konečný automat: Q = {zavřeno, otevřeno}, Σ = {vstup, odchod}. Kolik políček "
               "musí mít úplná tabulka přechodové funkce δ?", "číslo", str(len(DQ) * len(DS)),
               f"|Q| · |Σ| = 2 · 2 = {len(DD)}: pro každý stav a každou událost právě jeden přechod."))
    return qs


def auto_reveal():
    tree = state_tree(AD, AQ, AS, "q0")
    acc = lambda q: f"{s(q)} ←" if q in AF else s(q)
    tree_txt = "\n".join(f"{acc(q)}: " + ", ".join(f"{a} → {acc(r)}" + (" (už ve stromu, dál se nerozvíjí)" if old else "")
                                                for a, r, old in kids) for q, kids in tree)
    edges = "\n".join(f"{s(q)} –{a}→ {s(r)}" + (" (smyčka)" if q == r else "") for (q, a), r in AD.items())
    door = "\n".join(f"δ({q}, {a}) = {DD[(q, a)]}" + ("" if (q, a) in D_LECTURE else " *") for q in DQ for a in DS)
    return [
        (f"{TAB} Nakresli stavový diagram tohoto automatu.",
         "Vrcholy (stavy): q₀, q₁, q₂, q₃. Do q₀ vede šipka zvenku (počáteční stav), q₁ a q₂ jsou přijímací "
         "(dvojitý kroužek).\n"
         f"Hrany ({len(AD)} = 4 stavy · 2 znaky, z každého vrcholu jedna pro 0 a jedna pro 1):\n{edges}"),
        (f"{TAB} Rozviň stavový strom tohoto automatu (stav, který už ve stromu je, se dál nerozvíjí).",
         f"Kořen je počáteční stav q₀, ← = přijímací stav.\n{tree_txt}\n"
         "Strom podle přednášky; definici stavového stromu se zdrojem výpisky nemají, jak ho chce vyučující, "
         "ověřit na cvičení."),
        ("Zapiš vstupní dveře (příklad z přednášky: když vstoupíme, otevřou se, když odejdeme, zavřou se) jako "
         "konečný automat: Q, Σ, q₀, přechodová funkce δ a F.",
         "Jeden možný zápis (návrh z výpisků, přesný model vyučujícího neznáme):\n"
         "Q = {zavřeno, otevřeno}, Σ = {vstup, odchod}, q₀ = zavřeno\n"
         f"{door}\n* doplněno, aby byla δ úplná (2 · 2 = 4 políčka), stav se nezmění.\n"
         "F tu nemá přirozený význam; šlo by F = {zavřeno} (posloupnost událostí skončila zavřenými dveřmi)."),
    ]


# ── sestavení, kontroly a zápis ──────────────────────────────────────────────

def norm(a):  # jako norm() v ui/novy.html
    return re.sub(r"^0+(?=.)", "", re.sub(r"[\s_]", "", a.upper()))


BAD = re.compile(r"(první|druhá|třetí|čtvrtá|poslední) možnost|žádná z uvedených|všechny uvedené|"
                 r"\b[A-D] i [A-D]\b|možnost [A-D]\b", re.I)
BINOM = re.compile(r"\(([^()<>]+?) nad ([^()<>]+?)\)")


def build(choice, inputs, reveal, rnd, prefix):
    qs = []
    for text, opts, correct, expl in choice:
        check(len(set(opts)) == len(opts) == 4 and correct == [0], text)
        order = list(range(len(opts)))
        rnd.shuffle(order)
        qs.append({"type": "choice", "text": text,
                   "options": {"ABCD"[i]: opts[j] for i, j in enumerate(order)},
                   "correct": ["ABCD"[order.index(0)]], "explanation": expl})
    for text, hint, ans, sol in inputs:
        check(norm(ans) != "" and sol, text)
        qs.append({"type": "input", "text": text, "hint": hint, "answer": ans, "solution": sol})
    for text, sol in reveal:
        qs.append({"type": "input", "reveal": True, "text": text, "solution": sol})
    for i, q in enumerate(qs, 1):
        q["number"] = i
        q["id"] = f"{prefix}-{i}"
    for q in qs:
        texts = [q["text"], q.get("explanation", ""), q.get("solution", "")] + list(q.get("options", {}).values())
        for t in texts:
            check(not BAD.search(t), f"{q['id']}: odkaz na pořadí/písmeno možnosti: {t}")
            for m in BINOM.finditer(t):  # „(… nad …)“ vykreslí UI jako kombinační číslo, nesmí to být běžný text
                check(all(re.fullmatch(r"[\w+−\- ]{1,7}", x) and not re.search(r"[^\W\d_]{2}", x) for x in m.groups()),
                      f"{q['id']}: „{m.group(0)}“ by se vykreslilo jako kombinační číslo")
    check(len({q["text"] for q in qs}) == len(qs), f"{prefix}: duplicitní text otázky")
    return qs


def write(qs, filename, title):
    out = {"title": title, "lecture": 5, "date": "2026-10-29", "questions": qs}
    path = HERE / "banky" / filename
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter("reveal" if q.get("reveal") else q["type"] for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({c['choice']} výběrových, {c['input']} na výsledek, "
          f"{c['reveal']} na rozbor)")


def main():
    verify_formulas()
    verify_lecture_examples()
    verify_automata()
    rnd = random.Random(29)  # pevné pořadí možností v JSON (nové UI je stejně míchá)
    banks = [
        (build(komb_choice(), komb_input(), komb_reveal(), rnd, "5"), "05-2026-10-29.json",
         "Variace, permutace, kombinace a binomická věta"),
        (build(auto_choice(), auto_input(), auto_reveal(), rnd, "5a"), "05a-konecne-automaty.json", "Konečné automaty"),
    ]
    mine = {f for _, f, _ in banks}
    other = {q["id"] for p in (HERE / "banky").glob("*.json") if p.name not in mine
             for q in json.loads(p.read_text(encoding="utf-8"))["questions"]}
    ids = [q["id"] for qs, _, _ in banks for q in qs]
    check(len(set(ids)) == len(ids) and not set(ids) & other, "id otázek musí být unikátní napříč přednáškami")
    for qs, filename, title in banks:
        write(qs, filename, title)
    print(f"kontrol (assert): {CHECKS}")


if __name__ == "__main__":
    main()
