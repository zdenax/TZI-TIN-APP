#!/usr/bin/env python3
"""Vygeneruje banku 6. přednášky (5. 11. 2026) do banky/06-2026-11-05.json (id 6-N):
jazyky rozpoznatelné konečnými automaty (δ*, Σ⁺/Σ*, zřetězení, jazyk, L(A), příklad 2 s dveřmi).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Obsah vychází z výpisků přednášky 5. 11. 2026 (vault TZI1: 2026-11-05-vypisky-konecne-automaty.pdf), včetně
označených doplňků „Doplněno z Claude“ (definice podle Chytila, Automaty a gramatiky, s. 18–23, a Vaise, kap. 1).
Nejistě čtená místa rukopisu a částečný automat z fotky tabule (3 přechody) se nepoužívají. Odpovědi se počítají
a ověřují zde (simulace automatů, výčet slov přes itertools), ne ručně v JSON. Teorii kontrolovat proti přednášce.
Id 6-1…6-66 jsou pevná (váže se na ně uložený postup): nové otázky jen na konec (extra_*), pořadí skupin neměnit.
Zapisuje se JEN banky/06-2026-11-05.json, ostatní banky ani progress.json se nemění.
Spuštění:  python3 build_bank_6.py
"""
import itertools
import json
import random
import re
from collections import Counter
from pathlib import Path

from build_bank_5 import AD, AF, AQ, AS, BAD, BINOM, TAB, norm, run, s, state_tree

HERE = Path(__file__).parent
CHECKS = 0
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
ST_HINT = "stav jako q a číslo, bez dolního indexu, např. q7"
YN_HINT = "ano nebo ne (bez tečky)"


def check(cond, msg=""):
    global CHECKS
    assert cond, msg
    CHECKS += 1


# Automat z přednášky (q₀–q₃, F = {q₁, q₂}) je AD z build_bank_5.py; příklad 2 (dveře) je nový:
# stav q₀ = zavřeno (0), q₁ = otevřeno (1); vstup 0 = nikdo není, 1 = někdo je před dveřmi. F = {q₁}.
EQ, ES, EF = ["q0", "q1"], ["0", "1"], {"q1"}
ED = {("q0", "0"): "q0", ("q0", "1"): "q1", ("q1", "0"): "q0", ("q1", "1"): "q1"}
DOOR = "Dveře (příklad 2): Q = {q₀, q₁}, δ(q₀, 0) = q₀, δ(q₀, 1) = q₁, δ(q₁, 0) = q₀, δ(q₁, 1) = q₁, F = {q₁}."


def accepts(D, F, w, start="q0"):
    return run(D, start, w)[-1] in F


def words(n, S="01"):
    return ["".join(t) for t in itertools.product(S, repeat=n)]


def upto(n):
    return [w for k in range(n + 1) for w in words(k)]


def count_acc(D, F, n):
    return sum(accepts(D, F, w) for w in words(n))


def final(w, D=AD):
    return run(D, "q0", w)[-1]


# L(A) automatu z přednášky podle výpisků (doplněno z Claude): aspoň jedna 1 a končí 0, nebo tvar 0…01
def in_LA(w):
    return ("1" in w and w.endswith("0")) or re.fullmatch(r"0*1", w) is not None


def verify():
    for D, Q in ((AD, AQ), (ED, EQ)):
        check(set(D) == set(itertools.product(Q, "01")), "úplný DKA")
    # rekurzivní definice δ* (pravidla 1 a 2 z přednášky) = simulace
    def dstar(D, q, w):
        return q if w == "" else D[(dstar(D, q, w[:-1]), w[-1])]
    for w in upto(12):
        check(dstar(AD, "q0", w) == final(w), w)
        check(dstar(ED, "q0", w) == final(w, ED))
        # dveře: nový stav = poslední přečtený znak, jazyk = slova končící 1
        check(accepts(ED, EF, w) == w.endswith("1"), w)
        check(accepts(AD, AF, w) == in_LA(w), w)
    # příklady z výpisků
    check(final("10") == "q1")                                             # δ(δ(q₀,1),0) = δ(q₂,0) = q₁
    check(run(AD, "q0", "1011") == "q0 q2 q1 q3 q3".split())              # prošel F, ale skončil mimo
    check(run(AD, "q0", "1011010")[-1] == "q1" and final("1011010") in AF)
    check(run(ED, "q0", "01001") == "q0 q0 q1 q0 q0 q1".split() and accepts(ED, EF, "01001"))
    check(not accepts(AD, AF, ""))                                         # q₀ ∉ F → ε není rozpoznáno
    check(state_tree(ED, EQ, ES, "q0") == [("q0", [("0", "q0", True), ("1", "q1", False)]),
                                           ("q1", [("0", "q0", True), ("1", "q1", True)])])


# ── výběrové otázky: (text, [správná, špatná, špatná, špatná], [0], vysvětlení) ──
# Správná možnost nesmí být prozrazená délkou: zdůvodnění patří do vysvětlení, ne do možnosti (kontrola v build()).

def choice():
    w1, w2 = "1011", "1011010"
    st1, st2 = run(AD, "q0", w1), run(AD, "q0", w2)
    path1 = " → ".join(s(q) for q in st1)
    path2 = " → ".join(s(q) for q in st2)
    c = []
    add = lambda t, o, e: c.append((t, o, [0], e))

    add("Kdy je slovo rozpoznáno konečným automatem (definice z přednášky)?",
        ["Když je slovo celé přečteno a automat skončí v koncovém stavu.",
         "Když automat při čtení slova aspoň jednou projde koncovým stavem.",
         "Když první přečtený znak vede automat do koncového stavu.",
         "Když se automat po přečtení slova vrátí do počátečního stavu."],
        "Rozhoduje jen stav po posledním znaku; cesta slovem a stavy uprostřed se nepočítají.")
    add(f"{TAB} Čte slovo {w1}: {path1}. Je slovo rozpoznáno?",
        [f"Ne, skončil v {s(st1[-1])} ∉ F.",
         f"Ano, cestou prošel koncovým stavem {s(st1[2])}.",
         "Ano, protože slovo začíná jedničkou.",
         "Ne, protože slovo obsahuje víc jedniček než nul."],
        f"Skončil v {s(st1[-1])} ∉ F, i když cestou prošel koncovými stavy {s(st1[1])} a {s(st1[2])}. "
        "Počítá se jen stav po posledním znaku, ne průchod koncovým stavem uprostřed čtení.")
    add(f"{TAB} Čte slovo {w2}: {path2}. Je slovo rozpoznáno?",
        [f"Ano, skončil v {s(st2[-1])} ∈ F.",
         f"Ne, protože prošel stavem {s(st2[3])} ∉ F.",
         "Ne, protože slovo je delší než počet stavů.",
         "Ano, protože cesta začíná i končí ve stejném stavu."],
        "Slovo je celé přečteno a automat stojí v koncovém stavu, takže ho rozpoznává.")
    add("Co je δ* (zobecněná přechodová funkce)?",
        ["δ* : Q × Σ* → Q, vrátí stav po přečtení celého slova.",
         "δ* : Q × Σ → Q, přečte jediný znak a vrátí další stav.",
         "δ* : Q × Σ* → F, vrací vždy některý koncový stav.",
         "δ* : Σ* → ℕ, spočítá délku přečteného slova."],
        "δ umí jen jeden znak, δ* rozšiřuje δ na celá slova: δ*(q, w) = q′ je stav, ve kterém automat skončí.")
    add("Čemu se rovná δ*(q, ε), tedy přečtení prázdného slova?",
        ["q (stav se nezmění).", "Počátečnímu stavu q₀.", "Nějakému koncovému stavu z F.", "Není definováno."],
        "Pravidlo 1: δ*(q, ε) = q. Prázdné slovo nemá žádný znak, takže se nic nepřečte.")
    add("Jak zní rekurzivní pravidlo 2 pro δ*(q, wa), kde w je slovo a a znak?",
        ["δ*(q, wa) = δ(δ*(q, w), a)",
         "δ*(q, wa) = δ(q, a)",
         "δ*(q, wa) = δ*(q, w) ∪ δ(q, a)",
         "δ*(q, wa) = δ(δ*(q, a), w)"],
        "Nejdřív přečti w, pak ještě znak a: poslední znak se oddělí, stav po zbytku w dá δ*, "
        "a na ten se použije obyčejné δ se znakem a.")
    add("Jaký je rozdíl mezi δ a δ*?",
        ["δ je jeden krok (jeden znak), δ* je čtení celého slova.",
         "δ je pro deterministické automaty, δ* pro nedeterministické.",
         "δ vrací stav, δ* vrací množinu slov.",
         "Žádný, jen se píše jinak."],
        "Chytil obě značí stejně (δ), vyučující píše u slova w taky δ bez hvězdičky, ale slovo w znamená čtení celého slova.")
    add("Jak se počítá δ*(q₀, 10), tedy čtení slova 10?",
        ["Zevnitř ven: δ(δ(q₀, 1), 0), nejdřív první znak, pak druhý.",
         "Zvenku dovnitř: δ(δ(q₀, 0), 1), nejdřív poslední znak.",
         "Jako δ(q₀, 10), v jednom kroku.",
         "Jako součet δ(q₀, 1) + δ(q₀, 0)."],
        "Čte se zleva doprava; výsledek je stav po posledním znaku.")
    add("Co je abeceda Σ?",
        ["Konečná neprázdná množina symbolů (písmen).", "Libovolná, klidně i nekonečná množina celých slov.",
         "Množina všech koncových stavů.", "Jedno slovo nad jazykem."],
        "Přednáška: Σ je libovolná konečná abeceda, např. Σ = {0, 1}. Že je neprázdná, doplňuje Vais "
        "(doplněno z Claude).")
    add("Co je slovo nad abecedou Σ?",
        ["Konečná posloupnost písmen z Σ.", "Libovolná podmnožina Σ.", "Nekonečná posloupnost znaků z Σ.",
         "Přechod mezi dvěma stavy."],
        "Délka slova je počet znaků. Např. 0110 je slovo nad {0, 1} a |0110| = 4.")
    add("Co je prázdné slovo ε a jakou má délku?",
        ["Slovo bez jediného písmene, délka 0.", "Jeden znak, který značí mezeru, délka 1.",
         "Prázdná množina, ne slovo.", "Slovo, které nepatří do žádného jazyka."],
        "ε je také slovo (jako prázdný řetězec v programování). V rukopise „e – prázdné slovo“, |ε| = 0.")
    add("Co je Σ⁺?",
        ["Množina všech konečných neprázdných slov nad Σ.", "Množina všech konečných slov nad Σ včetně prázdného.",
         "Množina všech podmnožin Σ.", "Nejdelší slovo nad Σ."],
        "Přednáška: Σ⁺ = všechna konečná neprázdná slova (Chytil, def. 1.2.1). Např. {0, 1}⁺ = {0, 1, 00, 01, 10, 11, 000, …}.")
    add("Co je Σ*?",
        ["Všechna konečná slova nad Σ včetně prázdného slova ε.",
         "Všechna konečná neprázdná slova nad Σ, bez slova ε.",
         "Všechna nekonečná slova (posloupnosti) nad Σ.",
         "Množina všech jazyků nad abecedou Σ."],
        "Σ* = Σ⁺ ∪ {ε}, pro Σ = {0, 1} je Σ* = {ε, 0, 1, 00, …}. Rozdíl proti Σ⁺ je jediný prvek: ε.")
    add("V čem se liší Σ⁺ a Σ*?",
        ["Jen v prázdném slovu: ε ∈ Σ*, ale ε ∉ Σ⁺.", "Σ* je konečná, Σ⁺ nekonečná.",
         "Σ⁺ obsahuje jen slova délky 1.", "Nijak, jsou to dvě značky téže množiny."],
        "Zapamatuj si: + = aspoň jeden znak, * = klidně i žádný.")
    add("Kolik prvků má množina Σ⁺ pro Σ = {0, 1}?",
        ["Nekonečně (spočetně) mnoho.", "2", "Dvě na desátou, tedy přesně 1024.", "Žádný, množina je prázdná."],
        "Slov každé délky n je 2ⁿ, délek je nekonečně mnoho. Slova jdou seřadit podle délky, proto je množina spočetná.")
    add("Co je jazyk nad abecedou Σ?",
        ["Libovolná podmnožina L ⊆ Σ*.", "Jen nekonečná množina slov nad Σ.", "Jen množina slov, která rozpozná nějaký automat.",
         "Množina všech abeced."],
        "Definice důležitá z přednášky (Chytil, def. 1.2.2). Že jazyk může být konečný i nekonečný, "
        "a také prázdný, je doplněno z Claude.")
    add("Je množina {00, 01, 10, 11} jazykem nad abecedou {0, 1}?",
        ["Ano, je to podmnožina {0, 1}*.", "Ne, jazyk musí být nekonečný.",
         "Ne, jazyk smí obsahovat jen slova délky 1.", "Ano, ale jen pokud obsahuje prázdné slovo."],
        "Jazyk je libovolná podmnožina Σ*, tedy i konečný výčet; tady všechna slova délky 2 "
        "(příklad doplněný Claudem).")
    add("Jak se definuje jazyk L(A) rozpoznávaný konečným automatem A = (Q, Σ, δ, q₀, F)?",
        ["L(A) = {w ∈ Σ* ; δ*(q₀, w) ∈ F}, všechna slova, která automat rozpozná.",
         "L(A) = {q ∈ Q ; q ∈ F}, množina koncových stavů.",
         "L(A) = {w ∈ Σ* ; δ*(q₀, w) = q₀}, tedy slova vracející se do počátku.",
         "L(A) = Σ*, vždy všechna slova."],
        "Zkrácený zápis na tabuli: w ∈ L(A) ⇔ δ*(q₀, w) ∈ F. Čte se: pusť automat z q₀, přečti w a podívej se, zda skončil ve F.")
    add("Kdy je jazyk L rozpoznatelný konečným automatem?",
        ["Když L = L(A) pro nějaký konečný automat A.",
         "Když je L nekonečný (má nekonečně mnoho slov).",
         "Když L obsahuje prázdné slovo ε.",
         "Když má L alespoň dvě různá slova."],
        "Definice 1.2.4 z Chytila. Doplněno z Claude: třídu všech takových jazyků značí Chytil 𝓕; každý konečný "
        "jazyk je rozpoznatelný, nekonečný jen někdy, takže nekonečnost o rozpoznatelnosti nerozhoduje.")
    add("Kdy je prázdné slovo rozpoznáno konečným automatem?",
        ["Právě když q₀ ∈ F (počáteční stav je koncový).",
         "Vždy, protože každý automat přijímá ε.",
         "Nikdy, protože prázdné slovo se vůbec nedá přečíst.",
         "Právě když má automat jen jeden stav."],
        "ε ∈ L(A) ⇔ q₀ ∈ F. Plyne z δ*(q₀, ε) = q₀: automat nic nepřečte, takže zůstane v q₀.")
    add(f"{TAB} Je v něm rozpoznáno prázdné slovo?",
        ["Ne, protože q₀ ∉ F.", "Ano, každý automat přijímá ε.", "Ano, protože q₀ je počáteční.",
         "Ne, protože ε není slovo."],
        "ε ∈ L(A) ⇔ q₀ ∈ F, a tady q₀ není v F.")
    add("Musí být počáteční stav zároveň koncový?",
        ["Ne, q₀ v F být může, ale nemusí.",
         "Ano, jinak by automat nepřijal žádné slovo.",
         "Ano, ale jen u automatů se dvěma stavy.",
         "Ne, počáteční stav nesmí být nikdy koncový."],
        "F ⊆ Q je libovolná podmnožina. Je-li q₀ ∈ F, v tabulce se značí ↔ (Chytil) a automat rozpoznává ε.")
    add("Co je zřetězení slov u a v?",
        ["Slovo uv: slovo u a za ním slovo v.", "Průnik písmen slov u a v.", "Slovo, které vznikne zprohazováním znaků.",
         "Množina {u, v}."],
        "Např. u = abc, v = cda → uv = abccda.")
    add("Je zřetězení slov komutativní (platí uv = vu)?",
        ["Ne, ale je asociativní.",
         "Ano, pro libovolná slova u, v.",
         "Ano, ale jen pro slova stejné délky.",
         "Ne, a není ani asociativní."],
        "abc·cda = abccda, ale cda·abc = cdaabc. Zřetězení je asociativní, ne komutativní; "
        "prázdné slovo je neutrální prvek: εu = uε = u.")
    add("Které slovo je neutrální prvek zřetězení (platí εu = uε = u)?",
        ["Prázdné slovo ε.", "Slovo 0.", "Slovo u samo sebou.", "Neexistuje."],
        "Zřetězením s prázdným slovem se slovo nezmění. Délky se při zřetězení sčítají: |uv| = |u| + |v|.")
    add("Jak je definováno n-násobné zřetězení uⁿ slova u?",
        ["u¹ = u, uⁱ⁺¹ = uⁱu, u⁰ = ε",
         "u¹ = u, uⁱ⁺¹ = uⁱuⁱ, u⁰ = ε",
         "u¹ = u, uⁱ⁺¹ = uⁱ, u⁰ = ε",
         "uⁿ je n-tý znak slova u."],
        "Na tabuli u¹ = u, u² = uu, uⁱ⁺¹ = uⁱu (Chytil); u⁰ = ε doplňuje Vais. uⁿ je tedy n kopií u za sebou, "
        "např. pro u = ab je u³ = ababab. Délka je |uⁿ| = n · |u|.")
    add("Jak se čte zápis „∃ q₁, …, qₙ₊₁ : qₙ₊₁ ∈ F, q₁ = q₀, qᵢ₊₁ = δ(qᵢ, xᵢ)“ u slova w = x₁x₂…xₙ?",
        ["Existuje výpočet z q₀ po znacích slova w, který skončí ve F.",
         "Existuje stav, který je zároveň počáteční i koncový.",
         "Každé slovo ze Σ* délky n je automatem rozpoznáno.",
         "Automat má n + 1 stavů a všechny leží ve F."],
        "q₁, …, qₙ₊₁ jsou členy posloupnosti stavů při čtení (q₁ = q₀ je start), ne jména stavů q₁, q₂ automatu "
        "z přednášky. Každý další stav vznikne z předchozího a přečteného znaku a poslední leží ve F. Je to totéž "
        "co δ*(q₀, w) ∈ F; u deterministického automatu je výpočet jen jeden, „existuje“ znamená „ten jediný končí ve F“.")
    add("Proč u deterministického automatu stačí psát δ*(q₀, w) ∈ F místo „existuje výpočet končící ve F“?",
        ["Protože výpočet na slovo w je jen jeden.",
         "Protože automat má vždy jen jeden koncový stav.",
         "Protože slovo w je vždy jednoznakové.",
         "Protože δ* vůbec nezávisí na čteném slově."],
        "Deterministický automat: δ je funkce Q × Σ → Q, každé dvojici (stav, znak) přiřadí jediný stav. "
        "Proto je výpočet na w jen jeden a „existuje výpočet končící ve F“ znamená totéž co δ*(q₀, w) ∈ F.")
    add("Přednáška: „existují diskrétní a spojité, budeme brát diskrétní“. Jak lze „diskrétní“ automat chápat?",
        ["Stav se mění po krocích, jeden krok = jeden přečtený znak.",
         "Stav se mění spojitě v čase, bez jednotlivých kroků.",
         "Automat má nekonečně mnoho stavů a čte slovo naráz.",
         "Automat nečte žádný vstup, mění stav sám od sebe."],
        "Přednáška to dál nerozvedla. Výklad (stav se mění po krocích, krok = znak) je ve výpiscích "
        "označený jako doplněk od Clauda, není to výrok z tabule ani z knihy.")
    add("Z čeho si podle přednášky představujeme automat?",
        ["Z řídicí jednotky, čtecí hlavy a pásky s buňkami.",
         "Z procesoru, operační paměti, disku a sběrnice.",
         "Z obrazovky, klávesnice a myši s tlačítky.",
         "Z jediného přepínače se dvěma polohami."],
        "Na pásce je vstupní slovo, hlava ho čte po jednom znaku, řídicí jednotka drží aktuální stav.")
    add("Jaké čtyři způsoby zadání konečného automatu bude chtít úkol na příští týden?",
        ["Přechodová funkce, tabulka, stavový diagram a stavový strom.",
         "Tabulka přechodů, stavový diagram, regulární výraz a gramatika.",
         "Rovnice, graf, matice sousednosti a vstupní slovo.",
         "Jen tabulka přechodů a stavový diagram, nic dalšího."],
        "Úkol: konečný automat ve všech čtyřech reprezentacích, od jednodušších po složitější.")

    # příklad 2: dveře (nový model z 5. 11., dveře z 29. 10. byly jen odhad)
    add("Příklad 2 (dveře): stav 0 = zavřeno, stav 1 = otevřeno; vstup 0 = nikdo není před dveřmi, vstup 1 = někdo je. "
        "Kolik má automat stavů a jaká je abeceda?",
        ["Dva stavy Q = {q₀, q₁} a abecedu Σ = {0, 1}.", "Jeden stav a abecedu {0, 1}.", "Čtyři stavy a abecedu {0, 1}.",
         "Dva stavy a abecedu {zavřeno, otevřeno}."],
        "Q = {q₀, q₁}, Σ = {0, 1}, počáteční q₀ (zavřeno), F = {q₁} (otevřeno).")
    add(f"{DOOR} Jaká slova automat rozpoznává?",
        ["Slova končící jedničkou.", "Slova obsahující aspoň jednu jedničku.", "Slova se sudým počtem jedniček.",
         "Slova začínající jedničkou."],
        "Nový stav je vždy poslední přečtený znak (1 → q₁, 0 → q₀), takže rozhoduje poslední znak. Ověřeno výčtem do délky 12.")
    add("Dveře (příklad 2): slovo 01001. Jak vypadá posloupnost stavů a je slovo rozpoznáno?",
        ["q₀ → q₀ → q₁ → q₀ → q₀ → q₁; skončí v q₁ ∈ F, rozpoznáno.",
         "q₀ → q₀ → q₁ → q₀ → q₀ → q₀; skončí v q₀, nerozpoznáno.",
         "q₀ → q₁ → q₁ → q₁ → q₁ → q₁; skončí v q₁, rozpoznáno.",
         "q₁ → q₀ → q₁ → q₁ → q₀ → q₁; skončí v q₁, rozpoznáno."],
        "Stavy po znacích 0, 1, 0, 0, 1: q₀, q₁, q₀, q₀, q₁. Poslední znak je 1, takže q₁ ∈ F.")
    add("Dveře (příklad 2): rozpozná se prázdné slovo ε?",
        ["Ne, q₀ ∉ F (F = {q₁}).", "Ano, každý automat přijímá ε.", "Ano, protože dveře jsou na začátku zavřené.",
         "Ne, protože ε nemá délku."],
        "ε ∈ L(A) ⇔ q₀ ∈ F, tady F = {q₁}, takže ne. Slovo musí končit 1, ε nemá žádný znak.")
    add("Kolik přechodů (políček tabulky) má deterministický automat z příkladu 2 s dveřmi?",
        ["4", "2", "3", "6"],
        "2 stavy × 2 znaky: z každého stavu vede pro každý znak abecedy právě jeden přechod, |Q| · |Σ| = 2 · 2 = 4.")
    return c


# ── příklady na výsledek: (text, hint, odpověď, řešení) ──

def dstar_text(w):
    st = run(AD, "q0", w)
    return st, ", ".join(f"δ({s(st[i])}, {w[i]}) = {s(st[i + 1])}" for i in range(len(w)))


def inputs():
    out = []
    for w in ("10", "1011", "1011010", "111", "001"):
        st, krok = dstar_text(w)
        out.append((f"{TAB} Do jakého stavu dojde po přečtení slova {w}, tedy čemu se rovná δ*(q₀, {w})?",
                    ST_HINT, st[-1],
                    f"Čte se po znacích: {krok}.\nδ*(q₀, {w}) = {s(st[-1])}, "
                    + ("a to je koncový stav, slovo je rozpoznáno." if st[-1] in AF else "to není koncový stav, slovo není rozpoznáno.")))
    ano = lambda b: "ano" if b else "ne"
    # 6-43 a 6-44 dřív opakovaly 1011 a 1011010 (už v 6-2, 6-3, 6-38, 6-39), proto jiná slova
    yn = ("11", "0011", "1110", "0", "1100")
    check(Counter(ano(accepts(AD, AF, w)) for w in yn) == Counter({"ne": 3, "ano": 2}))
    for w in yn:
        st = run(AD, "q0", w)
        out.append((f"{TAB} Je slovo {w} rozpoznáno?", YN_HINT,
                    ano(st[-1] in AF), " → ".join(s(q) for q in st) + (" – skončil ve F: ano." if st[-1] in AF else " – skončil mimo F: ne.")))
    # nejkratší rozpoznané slovo a počty
    short = next(n for n in range(0, 8) if count_acc(AD, AF, n))
    check(short == 1 and [w for w in words(1) if accepts(AD, AF, w)] == ["1"])
    out.append((f"{TAB} Jak dlouhé je nejkratší slovo, které automat rozpoznává?",
                "číslo (délka slova)", str(short),
                "Prázdné slovo ne (q₀ ∉ F). Jednoznakové: 0 vede q₀ → q₀ (nepřijato), 1 vede q₀ → q₂ ∈ F (přijato). Nejkratší je slovo 1, délka 1."))
    # délka 2 je v rozboru 6-65, tady délka 4 a 3
    for n in (4, 3):
        k = count_acc(AD, AF, n)
        acc = [w for w in words(n) if accepts(AD, AF, w)]
        check(k == sum(in_LA(w) for w in words(n)))
        out.append((f"{TAB} Kolik slov délky {n} nad {{0, 1}} automat rozpoznává?",
                    "číslo", str(k), f"Z {2 ** n} slov délky {n} jich končí ve F {k}: {' '.join(acc)}."))
    # dveře (příklad 2); 6-50 dřív opakovala 01001 z 6-34
    for w in ("10110", "010010", "11"):
        st = run(ED, "q0", w)
        out.append((f"{DOOR} Do jakého stavu dojde automat po slově {w}?", ST_HINT, st[-1],
                    " → ".join(s(q) for q in st) + f". Nový stav je poslední přečtený znak: {s(st[-1])}."))
    k = count_acc(ED, EF, 4)
    check(k == 8)
    out.append(("Dveře (příklad 2, rozpoznává slova končící 1). Kolik slov délky 4 nad {0, 1} rozpozná?", "číslo", str(k),
                "Poslední znak je pevně 1, zbylé tři jsou libovolné: 2³ = 8."))
    # slova, délky, zřetězení
    for n in (3, 5):
        check(len(words(n)) == 2 ** n)
        out.append((f"Kolik slov délky {n} existuje nad abecedou {{0, 1}}?", "číslo", str(2 ** n),
                    f"Na každé z {n} pozic jsou dva znaky, tedy 2{str(n).translate(SUP)} = {2 ** n} slov."))
    n_plus = sum(len(words(n)) for n in range(1, 4))
    n_star = n_plus + 1
    check(n_plus == 14 and n_star == 15 and len(upto(3)) == 15)
    out.append(("Kolik slov z množiny Σ* nad Σ = {0, 1} má délku nejvýše 3 (včetně prázdného slova)?", "číslo", str(n_star),
                "ε (1) + délka 1 (2) + délka 2 (4) + délka 3 (8) = 15. Bez prázdného slova (Σ⁺) by jich bylo 14."))
    out.append(("Kolik slov z množiny Σ⁺ nad Σ = {0, 1} má délku nejvýše 3?", "číslo", str(n_plus),
                "Σ⁺ neobsahuje ε: 2 + 4 + 8 = 14."))
    out.append(("Jaká je délka slova 0110, tedy |0110|?", "číslo", "4", "Počet znaků: 4."))
    out.append(("Jaká je délka prázdného slova ε (na přednášce značené e), tedy |ε|?", "číslo", "0",
                "Prázdné slovo nemá žádný znak, |ε| = 0."))
    u = "ab"
    check(len(u * 4) == 8 and len(u * 0) == 0)
    out.append(("Slovo u = ab. Jakou délku má slovo u⁴ (čtyřnásobné zřetězení)?", "číslo", "8",
                "u⁴ = abababab, |u⁴| = 4 · |u| = 4 · 2 = 8."))
    out.append(("Slovo u = ab. Jakou délku má slovo u⁰?", "číslo", "0", "u⁰ = ε, délka 0."))
    out.append(("Slova u = abc a v = cda. Jakou délku má zřetězení uv?", "číslo", "6",
                "uv = abccda, |uv| = |u| + |v| = 3 + 3 = 6."))
    return out


# ── zadání na rozbor ──

def reveal():
    tree = state_tree(ED, EQ, ES, "q0")
    acc = lambda q: f"{s(q)} ←" if q in EF else s(q)
    tree_txt = "\n".join(f"{acc(q)}: " + ", ".join(f"{a} → {acc(r)}" + (" (už ve stromu)" if old else "") for a, r, old in kids)
                         for q, kids in tree)
    A4 = [w for w in words(2) if accepts(AD, AF, w)]
    N4 = [w for w in words(2) if not accepts(AD, AF, w)]
    w = "1001"  # dřív 1011, který už je v 6-2 a 6-38; stejná pointa: projde F, skončí mimo
    st = run(AD, "q0", w)
    via = list(dict.fromkeys(q for q in st[1:-1] if q in AF))
    check(st[-1] not in AF and len(via) == 2)
    return [
        ("Příklad 2 (dveře): stavy q₀ = zavřeno (0), q₁ = otevřeno (1), vstup 0 = nikdo není, 1 = někdo je před dveřmi. "
         "Zapiš automat jako pětici a ve všech čtyřech reprezentacích: přechodová funkce, tabulka, stavový diagram, stavový strom.",
         "Pětice: A = (Q, Σ, δ, q₀, F), Q = {q₀, q₁}, Σ = {0, 1}, q₀ počáteční, F = {q₁}.\n"
         "Přechodová funkce: δ(q₀, 0) = q₀, δ(q₀, 1) = q₁, δ(q₁, 0) = q₀, δ(q₁, 1) = q₁.\n"
         "Tabulka (→ počáteční, ← koncový):\n        0    1\n→ q₀   q₀   q₁\n← q₁   q₀   q₁\n"
         "Diagram: šipka zvenku do q₀, q₀ má smyčku 0, q₀ –1→ q₁, q₁ má smyčku 1, q₁ –0→ q₀, z q₁ šipka ven (koncový).\n"
         f"Strom (kořen q₀, ← = koncový):\n{tree_txt}\n"
         "Nový stav je poslední přečtený znak, automat rozpoznává slova končící 1."),
        (f"{TAB} Rozepiš po krocích δ*(q₀, {w}) a rozhodni, zda je slovo rozpoznáno.",
         "Zevnitř ven, po jednom znaku: " + ", ".join(f"δ({s(st[i])}, {w[i]}) = {s(st[i + 1])}" for i in range(len(w))) + f".\n"
         f"δ*(q₀, {w}) = {s(st[-1])} ∉ F, slovo není rozpoznáno, i když cestou prošel koncovými stavy "
         f"{' a '.join(s(q) for q in via)}. "
         f"Zapsáno rekurzivně: δ*(q₀, {w[:-1]}·{w[-1]}) = δ(δ*(q₀, {w[:-1]}), {w[-1]}) a tak dále, až u δ*(q₀, ε) = q₀."),
        (f"{TAB} Vypiš všechna slova délky 2 nad {{0, 1}} a rozděl je na rozpoznaná a nerozpoznaná.",
         "Všechna slova délky 2: " + " ".join(words(2)) + ".\n"
         "Rozpoznaná: " + " ".join(A4) + ".\nNerozpoznaná: " + (" ".join(N4) or "žádná") + ".\n"
         "Postup: pro každé slovo spočítej δ*(q₀, w) po dvou krocích a podívej se, jestli je výsledek ve F."),
        ("Vysvětli vlastními slovy rozdíl mezi Σ, Σ⁺, Σ* a jazykem nad Σ. Uveď příklad pro Σ = {0, 1}.",
         "Σ = {0, 1} je abeceda (konečná množina znaků).\n"
         "Σ⁺ = {0, 1, 00, 01, 10, 11, 000, …} = všechna neprázdná konečná slova.\n"
         "Σ* = Σ⁺ ∪ {ε} = {ε, 0, 1, 00, …} = totéž plus prázdné slovo.\n"
         "Jazyk nad Σ = libovolná podmnožina Σ*, třeba {00, 01, 10, 11} (slova délky 2), nebo všechna slova končící 1, nebo prázdná množina.\n"
         "Konečný automat jazyk L(A) = {w ; δ*(q₀, w) ∈ F} rozpoznává, když přijme právě slova z jazyka."),
    ]


# ── doplněné otázky 6-67 a dál (jen na konec, aby se neposunula id) ──

def extra_choice():
    c = []
    add = lambda t, o, e: c.append((t, o, [0], e))
    # 1. popis L(A); špatné popisy musí být opravdu jiné jazyky (protipříklad do délky 12)
    wrong = {"Slova končící nulou, nebo slova obsahující přesně dvě jedničky.":
                 lambda w: w.endswith("0") or w.count("1") == 2,
             "Slova se sudým počtem jedniček, která končí nulou.":
                 lambda w: w.count("1") % 2 == 0 and w.endswith("0"),
             "Slova obsahující aspoň jednu jedničku, bez ohledu na konec.":
                 lambda w: "1" in w}
    for p in wrong.values():
        check(any(p(w) != accepts(AD, AF, w) for w in upto(12)))
    add(f"{TAB} Která slova automat rozpoznává?",
        ["Slova s aspoň jednou 1 končící 0, nebo slova tvaru 0…01."] + list(wrong),
        "Doplněno z Claude (ve výpiscích, ověřeno výčtem do délky 12): po 1 je automat v q₂, po další 1 v q₃, "
        "nula z q₁, q₂, q₃ vede do q₁ ∈ F. Takže slovo s jedničkou končící 0 skončí v q₁, slovo 0…01 v q₂, "
        "jinak q₀ nebo q₃.")
    # 2. automat s q₀ ∈ F (nákres z rukopisu, s. 6)
    add("Na nákresu z přednášky je q₀ označený ↔ (počáteční i koncový stav). Rozpozná tento automat prázdné slovo ε?",
        ["Ano, protože q₀ ∈ F.",
         "Ne, prázdné slovo se nikdy nerozpoznává.",
         "Ne, protože se nepřečte žádný znak.",
         "Ano, ale jen když má q₀ smyčku."],
        "ε ∈ L(A) ⇔ q₀ ∈ F. Po přečtení ε zůstane automat v q₀ (δ*(q₀, ε) = q₀), a ten je koncový.")
    # 3. značky v tabulce
    add("Co v tabulce přechodů znamenají značky →, ← a ↔ u stavu?",
        ["→ počáteční, ← koncový, ↔ počáteční i koncový.",
         "→ koncový, ← počáteční, ↔ počáteční i koncový.",
         "→ počáteční, ← koncový, ↔ stav se smyčkou.",
         "→ přechod na 1, ← přechod na 0, ↔ na oba."],
        "Doplněno z Claude podle Chytila (s. 19): → počáteční stav, ← koncový, ↔ stav, který je počáteční i koncový.")
    # 5. slovo nad jinou abecedou
    sig = set("abc")
    check(not set("ccka") <= sig)
    add("Σ′ = {a, b, c}. Patří slovo ccka do Σ′⁺?",
        ["Ne, znak k není v abecedě Σ′.",
         "Ano, je to neprázdné konečné slovo.",
         "Ano, Σ′⁺ obsahuje každé slovo z písmen.",
         "Ne, slovo je delší než abeceda."],
        "Slovo nad Σ′ smí obsahovat jen znaky z Σ′. Ve výpiscích je příklad Σ′ = {a, b, c, …} a ccka ∈ Σ′⁺; "
        "to platí jen tehdy, když k ∈ Σ′.")
    # 7. přirozený jazyk
    add("Přednáška: „my jako Češi rozumíme češtině, rozpoznáváme to“. Jak to zapadá do teorie jazyků?",
        ["Čeština je jazyk nad konečnou abecedou, jeho slova jsou správné věty.",
         "Čeština není jazyk ve smyslu teorie, protože je nekonečná.",
         "Čeština je abeceda a jednotlivé věty jsou její písmena.",
         "Čeština je konečný automat, který rozpoznává všechny správné české věty."],
        "Doplněno z Claude podle Chytila (s. 21): přirozený jazyk je jazyk nad konečnou abecedou, jeho řetězy "
        "jsou správně utvořené věty. Jazyk může být i nekonečný.")
    # 8. spočetnost Σ⁺
    check([len(words(n)) for n in range(1, 6)] == [2, 4, 8, 16, 32])
    add("Proč je Σ⁺ pro Σ = {0, 1} spočetná, i když je nekonečná?",
        ["Protože slova jde seřadit do posloupnosti podle délky.",
         "Protože délka všech slov je shora omezená.",
         "Protože Σ⁺ je podmnožina konečné množiny Σ.",
         "Protože slov každé délky je nekonečně mnoho."],
        "Přednáška: Σ⁺ je spočetná. Důvod je doplněk od Clauda: slov délky n je 2ⁿ (konečně mnoho), takže jde "
        "vypsat nejdřív slova délky 1, pak 2 atd. a každé slovo dostane pořadové číslo (bijekce s ℕ).")
    return c


def extra_inputs():
    # 4. asociativita zřetězení; slova voleny tak, aby výsledek nezačínal nulou (norm ruší nuly vpředu)
    u, v, w = "10", "0", "11"
    ans = (u + v) + w
    check(ans == u + (v + w) and not ans.startswith("0"))
    return [(f"Slova u = {u}, v = {v}, w = {w}. Napiš slovo (uv)w.", "slovo z 0 a 1 bez mezer", ans,
             f"uv = {u + v}, (uv)w = {ans}. Vyjde totéž co u(vw) = {u}·{v + w} = {ans}: zřetězení je asociativní, "
             "závorky jde vynechat.")]


def extra_reveal():
    # 6. rekurzivní rozpis δ* podle pravidel 1 a 2
    w = "110"
    st = run(AD, "q0", w)
    lines = [f"δ*(q₀, {w})"]
    for k in range(len(w) - 1, -1, -1):  # rozbal δ*(q₀, w[:k+1]) = δ(δ*(q₀, w[:k]), w[k])
        inner = f"δ*(q₀, {w[:k]})" if k else "δ*(q₀, ε)"
        expr = inner
        for j in range(k, len(w)):
            expr = f"δ({expr}, {w[j]})"
        lines.append(expr)
    evals = []
    for i in range(len(w)):
        expr = s(st[i])
        for j in range(i, len(w)):
            expr = f"δ({expr}, {w[j]})"
        evals.append(expr)
    check(lines[-1] == "δ(δ(δ(δ*(q₀, ε), 1), 1), 0)" and evals[0] == "δ(δ(δ(q₀, 1), 1), 0)")
    check(st[-1] == "q1" and st[-1] in AF)
    return [(f"{TAB} Rozepiš δ*(q₀, {w}) rekurzivně podle pravidel 1 a 2 až k δ*(q₀, ε) = q₀ "
             "a pak výsledek vyhodnoť zevnitř ven.",
             "Pravidlo 2 (δ*(q, wa) = δ(δ*(q, w), a)) opakovaně:\n" + "\n= ".join(lines) + "\n"
             "Pravidlo 1 (δ*(q₀, ε) = q₀) a vyhodnocení zevnitř ven:\n= " + "\n= ".join(evals + [s(st[-1])]) + "\n"
             f"δ*(q₀, {w}) = {s(st[-1])} ∈ F, slovo je rozpoznáno.")]


# ── sestavení, kontroly a zápis ──

MAX_RATIO = 1.3      # správná možnost nejvýš o 30 % delší než nejdelší špatná
MAX_LONGEST = 0.35   # a nejdelší nejvýš u ~třetiny otázek (náhodou by to bylo ~25 %)


def build(groups, rnd, prefix):
    qs, longest = [], 0
    for kind, items in groups:
        for it in items:
            if kind == "choice":
                text, opts, correct, expl = it
                check(len(set(opts)) == len(opts) == 4 and correct == [0], text)
                check(len(opts[0]) <= MAX_RATIO * max(map(len, opts[1:])), f"správná možnost je moc dlouhá: {text}")
                longest += len(opts[0]) > max(map(len, opts[1:]))
                order = list(range(4))
                rnd.shuffle(order)
                qs.append({"type": "choice", "text": text, "options": {"ABCD"[i]: opts[j] for i, j in enumerate(order)},
                           "correct": ["ABCD"[order.index(0)]], "explanation": expl})
            elif kind == "input":
                text, hint, ans, sol = it
                check(norm(ans) != "" and sol, text)
                check(ans == "0" or not ans.startswith("0"), f"odpověď začíná nulou: {text}")
                qs.append({"type": "input", "text": text, "hint": hint, "answer": ans, "solution": sol})
            else:
                text, sol = it
                qs.append({"type": "input", "reveal": True, "text": text, "solution": sol})
    n_choice = sum(q["type"] == "choice" for q in qs)
    check(longest <= MAX_LONGEST * n_choice, f"správná možnost je nejdelší u {longest} z {n_choice} otázek")
    for i, q in enumerate(qs, 1):
        q["number"] = i
        q["id"] = f"{prefix}-{i}"
        texts = [q["text"], q.get("explanation", ""), q.get("solution", "")] + list(q.get("options", {}).values())
        for t in texts:
            check(not BAD.search(t), f"{q['id']}: odkaz na pořadí/písmeno možnosti: {t}")
            for m in BINOM.finditer(t):
                check(all(re.fullmatch(r"[\w+−\- ]{1,7}", x) and not re.search(r"[^\W\d_]{2}", x) for x in m.groups()),
                      f"{q['id']}: „{m.group(0)}“ by se vykreslilo jako kombinační číslo")
    check(len({q["text"] for q in qs}) == len(qs), "duplicitní text otázky")
    return qs, longest


def main():
    verify()
    groups = [("choice", choice()), ("input", inputs()), ("reveal", reveal()),
              ("choice", extra_choice()), ("input", extra_inputs()), ("reveal", extra_reveal())]
    check(sum(len(g) for _, g in groups[:3]) == 66, "6-1…6-66 musí zůstat na místě")
    qs, longest = build(groups, random.Random(105), "6")
    other = {q["id"] for p in (HERE / "banky").glob("*.json") if p.name != "06-2026-11-05.json"
             for q in json.loads(p.read_text(encoding="utf-8"))["questions"]}
    check(not {q["id"] for q in qs} & other, "id otázek musí být unikátní napříč přednáškami")
    out = {"title": "Jazyky rozpoznatelné konečnými automaty", "lecture": 6, "date": "2026-11-05", "questions": qs}
    path = HERE / "banky" / "06-2026-11-05.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter("reveal" if q.get("reveal") else q["type"] for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({c['choice']} výběrových, {c['input']} na výsledek, {c['reveal']} na rozbor)")
    print(f"správná možnost nejdelší: {longest} z {c['choice']}")
    print(f"kontrol (assert): {CHECKS}")


if __name__ == "__main__":
    main()
