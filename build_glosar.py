#!/usr/bin/env python3
"""Převede glosář z Obsidianu (Glosar.md) na glosar/glosar.json pro tlačítko „Glosář“ v aplikaci.

Spuštění:  python3 build_glosar.py /cesta/k/Glosar.md
Výstup: {"lectures": {"1": [{"term": ..., "body": ...}, ...], ...}}, hesla podle přednášky.
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


def lectures_of(zdroj, default):
    """Jen sekce Kombinatorika (default 4 a 5) se dělí podle data ve Zdroji: základy z 22. 10. patří k 4. i 5. přednášce, zbytek (29. 10.) jen k 5."""
    if default != [4, 5]:
        return default
    return [4, 5] if "22. " in zdroj else [5]


SECTION_LECTURE = {"Implikace": 2, "Formule": 2, "Výrokové formy": 2, "Kvantifikátory": 2,
                   "Důkazy": 2, "Logická výstavba": 2}


def main(src):
    md = Path(src).read_text(encoding="utf-8")
    md = md.split("\n## Použité zdroje")[0]
    out = {str(n): [] for n in range(1, 6)}
    for sec in re.split(r"\n(?=## )", md)[1:]:
        title, _, rest = sec.partition("\n")
        title = title[3:].strip()
        m = re.search(r"\((\d)\. přednáška\)", title)
        if "(4. a 5. přednáška)" in title:
            default = [4, 5]
        elif m:
            default = [int(m.group(1))]
        else:
            default = [next(v for k, v in SECTION_LECTURE.items() if title.startswith(k))]
        rest = re.sub(r"\n---\s*$", "", rest.strip())
        parts = re.split(r"(?:^|\n)(?=### )", rest)  # sekce může začínat rovnou heslem, pak je intro prázdné
        intro, entries = parts[0], parts[1:]
        intro = "\n".join(l for l in intro.split("\n") if not l.startswith("Podrobně:")).strip()
        if len(intro) > 80:
            entries.insert(0, f"### {re.sub(r' \(.*\)$', '', title)}: přehled\n{intro}")
        for e in entries:
            head, _, body = e.partition("\n")
            body = body.strip()
            zd = "\n".join(l for l in body.split("\n") if l.startswith("*Zdroj"))
            ls = lectures_of(zd, default)
            for n in ls:
                out[str(n)].append({"term": clean(head[4:].strip()), "body": clean(body)})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"lectures": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in out.items()}, "->", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
