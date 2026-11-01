#!/usr/bin/env python3
"""Převede glosář z Obsidianu (Glosar.md) na glosar/glosar.json pro tlačítko „Glosář“ v aplikaci.

Spuštění:  python3 build_glosar.py /cesta/k/Glosar.md
Výstup: {"banks": {"<stem banky>": [{"term": ..., "body": ...}, ...], ...}}, pojmy podle balíčku otázek.
LaTeX se převádí na text, který umí `fmt` v ui/novy.html (zlomky „a / b“, „(n nad k)“, indexy _x, mocniny ^x).
Neznámý LaTeX příkaz skript zastaví, ať nic nezůstane nepřeloženo.
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).parent / "glosar" / "glosar.json"

SYM = {
    "Rightarrow": "⇒", "Leftrightarrow": "⇔", "neg": "¬", "in": "∈", "wedge": "∧", "vee": "∨", "cdot": "·",
    "dots": "…", "cdots": "…", "ldots": "…", "to": "→", "forall": "∀", "exists": "∃", "times": "×",
    "subseteq": "⊆", "subset": "⊂", "equiv": "≡", "varphi": "φ", "neq": "≠", "le": "≤", "ge": "≥",
    "geq": "≥", "leq": "≤", "Sigma": "Σ", "delta": "δ", "notin": "∉", "cup": "∪", "cap": "∩",
    "emptyset": "∅", "sim": "∼", "setminus": "∖", "circ": "∘", "sum": "∑", "prod": "∏", "sin": "sin",
    "lambda": "λ", "pi": "π", "mapsto": "↦", "leftarrow": "←", "xrightarrow": "→",
    "qquad": " ", "quad": " ", ";": " ", ",": " ", " ": " ", "{": "{", "}": "}", "displaystyle": "",
    "left": "", "right": "",
}
BB = {"N": "ℕ", "Z": "ℤ", "Q": "ℚ", "R": "ℝ", "C": "ℂ"}


def group(s, i):
    """Obsah závorky { } začínající na s[i] == '{'; vrátí (obsah, index za závorkou)."""
    if s[i] != "{":  # \sqrt2: argument bez závorek je jeden znak
        return s[i], i + 1
    d = 0
    for j in range(i, len(s)):
        d += s[j] == "{"
        d -= s[j] == "}"
        if d == 0:
            return s[i + 1:j], j + 1
    raise ValueError("nespárovaná závorka: " + s)


def tex(s):
    out, i = "", 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[i:])
            name = m.group(1)
            i += m.end()
            if name in ("frac", "dfrac", "binom", "dbinom"):
                while s[i] == " ":
                    i += 1
                a, i = group(s, i)
                b, i = group(s, i)
                a, b = tex(a), tex(b)
                out += f"({a} nad {b})" if "binom" in name else f"({a}) / ({b})"
            elif name == "sqrt":
                a, i = group(s, i)
                out += f"√({tex(a)})"
            elif name == "mathbb":
                a, i = group(s, i)
                out += BB[a]
            elif name in ("mathrm", "mathcal", "text"):
                a, i = group(s, i)
                out += tex(a)
            elif name in SYM:
                out += SYM[name]
                if name.isalpha() and name not in ("left", "right", "displaystyle"):
                    out += " " if name in ("to", "in", "sin") or SYM[name] in "⇒⇔" else ""
            else:
                raise ValueError(f"neznámý příkaz \\{name} v: {s}")
        elif c in "_^" and i + 1 < len(s) and s[i + 1] == "{":
            a, i2 = group(s, i + 1)
            a = tex(a)
            if a.startswith("(") and a.endswith(")") and "(" not in a[1:-1]:
                a = a[1:-1]  # fmt neumí vnořené závorky v indexu: P'_(k_1,…,k_n)
            out += f"{c}({a})"
            i = i2
        else:
            out += c
            i += 1
    return re.sub(r" {2,}", " ", out)


def inline_math(line):
    line = re.sub(r"\$\$(.+?)\$\$", lambda m: tex(m.group(1)), line)
    return re.sub(r"\$(.+?)\$", lambda m: tex(m.group(1)), line)


def clean(text):
    """Odkazy [[a|b]] / [[a#b]] na prostý text, matematika na text."""
    text = re.sub(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]", lambda m: m.group(3) or m.group(1) or m.group(2), text)
    out, display = [], False
    for ln in text.split("\n"):
        if ln.strip() == "$$":  # víceřádková display matematika
            display = not display
            continue
        out.append(inline_math(ln))
    return "\n".join(out)


# Sekce glosáře -> balíčky otázek (stem souboru v banky/). Kombinatorika se dělí po heslech, viz niže.
SECTION_BANKS = [
    ("Matematický zápis", ["01-2026-10-01"]),
    ("Výroky", ["02-2026-10-08"]), ("Implikace", ["02-2026-10-08"]), ("Formule", ["02-2026-10-08"]),
    ("Výrokové formy", ["02-2026-10-08"]), ("Kvantifikátory", ["02-2026-10-08"]),
    ("Logická výstavba", ["02-2026-10-08"]),
    ("Důkazy", ["02d-dukazy"]),
    ("Množiny", ["03-2026-10-15"]),
    ("Rozklad", ["04-2026-10-22"]),
    ("Konečné automaty", ["05a-konecne-automaty"]),
]
KOMB, KOMB22, KOMB29 = "04k-kombinatorika", "04k-kombinatorika", "05-2026-10-29"
# do 04k (22. 10.: základy, kombinace, kombinační číslo, Pascal) patří jen tahle hesla; 05 (29. 10.) dostane všechna
KOMB_JEN_22 = ("Základní množina", "Bez opakování", "Faktoriál", "Kombinace (nezáleží", "Kombinační číslo", "Vlastnosti kombinačního")


def banks_of(title, term):
    if title.startswith("Kombinatorika"):
        return [KOMB22, KOMB29] if term.startswith(KOMB_JEN_22) or term.startswith("Kombinatorika") else [KOMB29]
    return next(b for k, b in SECTION_BANKS if title.startswith(k))


def main(src):
    md = Path(src).read_text(encoding="utf-8")
    md = md.split("\n## Použité zdroje")[0]
    out = {}
    for sec in re.split(r"\n(?=## )", md)[1:]:
        title, _, rest = sec.partition("\n")
        title = title[3:].strip()
        rest = re.sub(r"\n---\s*$", "", rest.strip())
        parts = re.split(r"(?:^|\n)(?=### )", rest)  # sekce může začínat rovnou heslem, pak je intro prázdné
        intro, entries = parts[0], parts[1:]
        intro = "\n".join(l for l in intro.split("\n") if not l.startswith("Podrobně:")).strip()
        if len(intro) > 80:
            entries.insert(0, f"### {re.sub(r' \(.*\)$', '', title)}: přehled\n{intro}")
        for e in entries:
            head, _, body = e.partition("\n")
            term = clean(head[4:].strip())
            for b in banks_of(title, term):
                out.setdefault(b, []).append({"term": term, "body": clean(body.strip())})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"banks": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in sorted(out.items())}, "->", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
