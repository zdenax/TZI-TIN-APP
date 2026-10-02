#!/usr/bin/env python3
"""Vygeneruje banku otázek pro 1. přednášku (číselné soustavy) do banky/.

Otázky na výpočty se počítají zde (ne ručně), takže správné odpovědi i postupy jsou ověřené.
Spuštění:  python3 build_bank.py
"""
import json
from pathlib import Path

D = "0123456789ABCDEF"
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def base(n, z):
    out = ""
    while n:
        out = D[n % z] + out
        n //= z
    return out or "0"


def num(s, z):
    return f"({s}){str(z).translate(SUB)}"


def groups(s, k):
    s = s.zfill(-(-len(s) // k) * k)
    return [s[i:i + k] for i in range(0, len(s), k)]


def steps(s, frm, to):
    n = int(s, frm)
    lines = []
    if frm == 10:
        lines.append("dělení      podíl  zbytek")
        m = n
        while m > 0:
            r = m % to
            lines.append(f"{m:>6} : {to:<2}  {m // to:>6}  {r}" + (f" = {D[r]}" if r > 9 else ""))
            m //= to
        lines.append(f"Zbytky zdola nahoru: {base(n, to)}")
    elif to == 10:
        L = len(s)
        lines.append(" + ".join(f"{D.index(c)}·{frm}^{L - 1 - i}" for i, c in enumerate(s)))
        lines.append("= " + " + ".join(str(D.index(c) * frm ** (L - 1 - i)) for i, c in enumerate(s)) + f" = {n}")
    else:
        k = {2: 1, 8: 3, 16: 4}
        if frm == 2:
            g = groups(s, k[to])
            lines.append(f"Zprava po {k[to]} bitech: " + " | ".join(g))
            lines.append("-> " + " ".join(D[int(x, 2)] for x in g) + f" = {base(n, to)}")
        elif to == 2:
            g = [bin(D.index(c))[2:].zfill(k[frm]) for c in s]
            lines.append(f"Každá číslice na {k[frm]} bity: " + " | ".join(g))
            lines.append(f"= {base(n, 2)} (vedoucí nuly pryč)")
        else:
            b = base(n, 2)
            lines.append(f"Přes dvojkovou: {s} = {b}")
            lines.append(f"Po {k[to]} bitech zprava: " + " | ".join(groups(b, k[to])) + f" -> {base(n, to)}")
    if to != 10:
        lines.append(f"Kontrola zpět do desítkové: {int(base(n, to), to)}")
    return "\n".join(lines)


# ---------- výběrové otázky (teorie) ----------
# (text, [možnosti], [správné indexy], vysvětlení)
CHOICE = [
    ("Která z uvedených soustav je nepoziční?",
     ["dvojková", "římská", "šestnáctková", "osmičková"], [1],
     "Nepoziční soustava nemá základ. Příklad z přednášky: římská (I, II, III, IV, V, VI...)."),
    ("Co udává základ Z poziční číselné soustavy?",
     ["počet číslic v zápisu konkrétního čísla", "maximální počet číslic, které jsou v soustavě k dispozici",
      "největší číslo, které lze v soustavě zapsat", "počet pozic, na které lze číslo rozepsat"], [1],
     "Základ udává max. počet číslic v soustavě (Z > 1)."),
    ("Které číslice existují v osmičkové soustavě?",
     ["0 až 8", "0 až 7", "1 až 8", "0 až 9"], [1],
     "Osmičková má číslice 0 až 7. Číslice 8 a 9 neexistují, po 7 následuje 10."),
    ("Jak zní obecný zápis čísla a v poziční soustavě o základu Z (číslice a_n ... a_0)?",
     ["a = a_n·Z^n + a_(n-1)·Z^(n-1) + ... + a_1·Z^1 + a_0·Z^0", "a = a_n·n^Z + ... + a_0·0^Z",
      "a = a_n + a_(n-1) + ... + a_0 + Z", "a = Z·(a_n + a_(n-1) + ... + a_0)"], [0],
     "Každá číslice se násobí příslušnou mocninou základu a všechno se sečte."),
    ("Jaká je nejvyšší mocnina základu u třímístného čísla zapsaného v poziční soustavě?",
     ["Z³", "Z²", "Z¹", "Z⁴"], [1],
     "Nejvyšší mocnina = počet číslic − 1, tedy 3 − 1 = 2."),
    ("Čemu se rovná (101)₂ v desítkové soustavě?", ["3", "4", "5", "6"], [2],
     "1·2² + 0·2¹ + 1·2⁰ = 4 + 0 + 1 = 5."),
    ("Jakou hodnotu má hexadecimální číslice D?", ["11", "12", "13", "14"], [2],
     "A=10, B=11, C=12, D=13, E=14, F=15."),
    ("Kolika bitům odpovídá jedna číslice šestnáctkové soustavy?", ["2", "3", "4", "8"], [2],
     "16 = 2⁴, takže jedna hex číslice nese přesně 4 bity."),
    ("Kolika bitům odpovídá jedna číslice osmičkové soustavy?", ["2", "3", "4", "8"], [1],
     "8 = 2³, takže jedna osmičková číslice nese přesně 3 bity."),
    ("Jak se čtou zbytky při převodu z desítkové do soustavy o základu Z dělením?",
     ["shora dolů", "zdola nahoru", "zleva doprava podle velikosti", "v libovolném pořadí"], [1],
     "Zbytky se zapisují v pořadí, jak vznikají, a čtou se zdola nahoru (první zbytek je nejnižší řád)."),
    ("Jak se podle přednášky převádí osmičková soustava na šestnáctkovou?",
     ["oklikou přes dvojkovou soustavu", "přímo po jedné číslici", "dělením čtyřmi", "nelze, převádí se jen přes desítkovou"], [0],
     "Osmičkové číslice rozepíšu na trojice bitů, bity pak seskupím po čtveřicích zprava."),
    ("Kolik je 1 + 1 ve dvojkové soustavě?",
     ["2", "(10)₂, tedy zapíšu 0 a 1 přenesu", "(11)₂", "0 bez přenosu"], [1],
     "1 + 1 = (10)₂: zapíšu 0 a přenos 1 do vyššího řádu."),
    ("Které uspořádání číselných oborů je správné?",
     ["N ⊂ Z ⊂ Q ⊂ R ⊂ C", "Z ⊂ N ⊂ Q ⊂ R ⊂ C", "N ⊂ Q ⊂ Z ⊂ R ⊂ C", "N ⊂ Z ⊂ R ⊂ Q ⊂ C"], [0],
     "Přirozená ⊂ celá ⊂ racionální ⊂ reálná ⊂ komplexní."),
    ("Kolik je 0! (nula faktoriál)?", ["0", "1", "není definován", "2"], [1], "Podle definice 0! = 1."),
    ("Kolik je 5!?", ["25", "60", "120", "720"], [2], "5! = 1·2·3·4·5 = 120."),
    ("Které z čísel patří do Q (racionální), ale ne do Z (celá)?", ["−3", "0", "3/4", "7"], [2],
     "3/4 je zlomek, který není celé číslo."),
    ("Které dva zápisy jsou platná čísla v osmičkové soustavě? (vyber dvě)",
     ["157", "289", "7070", "108"], [0, 2],
     "V osmičkové neexistují číslice 8 a 9. Zápisy 289 a 108 je obsahují."),
    ("Čemu se rovná (A5)₁₆ v desítkové soustavě?", ["155", "160", "165", "170"], [2],
     "10·16 + 5 = 165."),
    ("Které hexadecimální číslo je (1011 1010)₂?", ["AB", "BA", "1A", "B9"], [1],
     "1011 = 11 = B, 1010 = 10 = A, tedy (BA)₁₆."),
    ("Jaký je výsledek dělení jedničky nulou ve dvojkové soustavě?",
     ["0", "1", "dělení nulou není definováno (chyba)", "(10)₂"], [2],
     "Dělení nulou není definováno."),
    ("Kolik cifer má desítková soustava?", ["9", "10", "11", "16"], [1], "Cifry 0, 1, ..., 9, tedy 10."),
    ("Kolik je a⁰ pro nenulové a?", ["0", "1", "a", "nedefinováno"], [1],
     "a⁰ = 1. Pozor, 0⁰ je zvláštní případ (viz tabule na přednášce)."),
]

# ---------- příklady na výsledek ----------
CONV = [  # (zápis, ze základu, na základ)
    ("37", 10, 2), ("100", 10, 2), ("255", 10, 2), ("83", 10, 2), ("26", 10, 2), ("200", 10, 2),
    ("100", 10, 8), ("511", 10, 8), ("251", 10, 8), ("200", 10, 8),
    ("1000", 10, 16), ("4095", 10, 16), ("251", 10, 16), ("262342", 10, 16),
    ("101101", 2, 10), ("110011", 2, 10), ("11111011", 2, 10),
    ("157", 8, 10), ("373", 8, 10), ("2F", 16, 10), ("1C3", 16, 10), ("BAC", 16, 10),
    ("11010110", 2, 16), ("101111101", 2, 16), ("101110101100", 2, 16),
    ("3E7", 16, 2), ("111", 16, 2), ("FB", 16, 2),
    ("1101011", 2, 8), ("11111011", 2, 8),
    ("725", 8, 2), ("5654", 8, 2),
    ("373", 8, 16), ("725", 8, 16), ("BAC", 16, 8),
]
ARIT = [("1011", "+", "110"), ("11011", "+", "1111"), ("111", "+", "10"), ("1101", "-", "101"),
        ("10100", "-", "111"), ("111", "-", "10"), ("101", "*", "11"), ("110", "*", "11"),
        ("1011", "*", "101"), ("1100", ":", "11"), ("110", ":", "10"), ("111100", ":", "101")]


def arit(a, op, b):
    x, y = int(a, 2), int(b, 2)
    r = {"+": x + y, "-": x - y, "*": x * y, ":": x // y}[op]
    sym = {"+": "+", "-": "−", "*": "·", ":": ":"}[op]
    R = bin(r)[2:]
    sol = f"{x} {sym} {y} = {r} (desítkově), tedy {R}."
    if op == "*":
        parts = [a + "0" * i for i, c in enumerate(reversed(b)) if c == "1"]
        sol += "\nDílčí součiny (posun o řád): " + " + ".join(parts)
    elif op == "-":
        sol += f"\nKontrola sčítáním: {R} + {b} = {a}"
    elif op == ":":
        sol += f"\nKontrola násobením: {R} · {b} = {a}"
    else:
        sol += "\nSčítej zprava, 1+1 = 10 (zapiš 0, přenos 1)."
    return f"{num(a, 2)} {sym} {num(b, 2)} = ?", R, sol


def main():
    qs = []
    for text, opts, correct, expl in CHOICE:
        qs.append({"type": "choice", "text": text,
                   "options": {"ABCD"[i]: o for i, o in enumerate(opts)},
                   "correct": ["ABCD"[i] for i in correct], "explanation": expl})
    for s, frm, to in CONV:
        ans = base(int(s, frm), to)
        qs.append({"type": "input", "text": f"{num(s, frm)} → (?){str(to).translate(SUB)}",
                   "hint": f"výsledek v soustavě o základu {to}", "answer": ans, "solution": steps(s, frm, to)})
    for a, op, b in ARIT:
        text, ans, sol = arit(a, op, b)
        qs.append({"type": "input", "text": text, "hint": "výsledek zapiš dvojkově", "answer": ans, "solution": sol})
    for i, q in enumerate(qs, 1):
        q["number"] = i
        q["id"] = f"1-{i}"
    out = {"title": "Číselné soustavy a matematický zápis", "lecture": 1, "date": "2026-10-01", "questions": qs}
    path = Path(__file__).parent / "banky" / "01-2026-10-01.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_c = sum(q["type"] == "choice" for q in qs)
    print(f"{path.name}: {len(qs)} otázek ({n_c} výběrových, {len(qs) - n_c} na výsledek)")


if __name__ == "__main__":
    main()
