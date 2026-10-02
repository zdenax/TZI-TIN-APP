#!/usr/bin/env python3
"""TZI Trenér: terminálová aplikace na opakování 1. přednášky (číselné soustavy).

Spuštění:  python3 tzi_trener.py
Bez závislostí (jen standardní knihovna). Postup kartiček se ukládá do ~/.tzi_trener.json.
"""
import json
import random
from pathlib import Path

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


def main():
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


if __name__ == "__main__":
    main()
