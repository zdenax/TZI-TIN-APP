#!/usr/bin/env python3
"""Převede výpisky z přednášky (Obsidian .md) na sekci v vypisky/vypisky.json pro stránku /vypisky.

Spuštění:  python3 build_vypisky.py /cesta/k/2026-11-12-gramatiky.md 07-2026-11-12
           python3 build_vypisky.py --cviceni /cesta/k/cviko-2026-11-19-gramatiky.md 07-2026-11-12   (-> vypisky/cviceni.json)
Výstup: {"banks": {"<stem banky>": {title, date, source, sections: [{level, heading, id, body}]}}}.
Soubor ve vaultu se jen čte. LaTeX se převádí převodníkem z build_glosar.py (režim NOTES), neznámý příkaz nebo
nepodporovaná markdown konstrukce skript zastaví, ať se nic tiše nepokazí.
Formát těla (čte ui/md.js): odstavce, odrážky „- “, číslované „1. “, tabulky, citace a callouty „> [!typ]± název“
(vnořené „> > “), řádky display matematiky „@@ text“ (víc po sobě = jeden blok), blok „{small}“ … „{/small}“,
podtržení mezi znaky U+E000 a U+E001. Z přednášky se vynechá odkaz na plátno a pdf (sekce „Originál“).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import build_glosar as bg

bg.NOTES = True
OUT = Path(__file__).parent / "vypisky" / "vypisky.json"
CVICENI = Path(__file__).parent / "vypisky" / "cviceni.json"  # {"seminars": {"<jméno souboru>": {bank, title, date, source, sections}}}
PREFIX = re.compile(r"^((?:>\s?)*)(.*)$")
SVG_TAGS = {"svg", "g", "rect", "line", "path", "circle", "ellipse", "polygon", "polyline", "text", "tspan", "title"}


def fail(msg, ln):
    raise SystemExit(f"CHYBA: {msg}\n  v řádku: {ln}")


def display_rows(src):
    """Obsah $$…$$ na řádky „@@ text“; prostředí aligned se rozdělí po \\\\ a & se zahodí (zarovnání se nezachová)."""
    src = re.sub(r"\\(begin|end)\{aligned\}", "", src)
    rows = [r.replace("&", "").strip() for r in src.split("\\\\")]
    return ["@@ " + bg.tex(r) for r in rows if r]


def svg_ok(s):
    return not (set(re.findall(r"</?([a-zA-Z]+)", s)) - SVG_TAGS or re.search(r"\son\w+\s*=|href|javascript:|<!", s, re.I))


def excalidraw_svg(name):
    """Kresba ![[name.excalidraw]] z vaultu jako SVG na jeden řádek; None, když soubor chybí nebo je komprimovaný
    (Obsidian ho po úpravě uloží jako compressed-json). Umí jen obdélníky, čáry, šipky a text, barvy přes currentColor."""
    hits = list(ROOT.rglob(name + ".excalidraw.md")) if ROOT else []
    m = re.search(r"```json\n(.*?)\n```", hits[0].read_text(encoding="utf-8"), re.S) if len(hits) == 1 else None
    if not m:
        return None
    esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    els = [e for e in json.loads(m.group(1))["elements"] if not e.get("isDeleted")]
    x0, y0 = min(e["x"] for e in els) - 10, min(e["y"] for e in els) - 10
    W, H = max(e["x"] + e["width"] for e in els) + 10 - x0, max(e["y"] + e["height"] for e in els) + 10 - y0
    o = []
    for e in els:
        x, y = e["x"] - x0, e["y"] - y0
        if e["type"] == "rectangle":
            fill = 'fill="currentColor" fill-opacity="0.12"' if e.get("backgroundColor", "transparent") != "transparent" else ""
            o.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{e["width"]:.0f}" height="{e["height"]:.0f}" {fill}/>')
        elif e["type"] in ("line", "arrow"):
            pts = [(x + px, y + py) for px, py in e["points"]]
            o.append('<polyline points="' + " ".join(f"{a:.0f},{b:.0f}" for a, b in pts) + '"/>')
            if e["type"] == "arrow":  # hrot šipky jako trojúhelník (bez <marker>, ten SVG_TAGS nepouští)
                (ax, ay), (bx, by) = pts[-2], pts[-1]
                d = max(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, 1)
                ux, uy = (bx - ax) / d, (by - ay) / d
                o.append(f'<polygon fill="currentColor" points="{bx:.0f},{by:.0f} {bx - 12 * ux + 6 * uy:.0f},{by - 12 * uy - 6 * ux:.0f} '
                         f'{bx - 12 * ux - 6 * uy:.0f},{by - 12 * uy + 6 * ux:.0f}"/>')
        elif e["type"] == "text":
            fs = e["fontSize"]
            mid = e.get("textAlign") == "center"
            tx = x + e["width"] / 2 if mid else x
            spans = "".join(f'<tspan x="{tx:.0f}" dy="{fs if i == 0 else fs * 1.25:.0f}">{esc(l)}</tspan>'
                            for i, l in enumerate(e["text"].split("\n")))
            anchor = ' text-anchor="middle"' if mid else ""
            o.append(f'<text x="{tx:.0f}" y="{y:.0f}" font-size="{fs}" fill="currentColor" stroke="none"{anchor}>{spans}</text>')
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" style="max-width:100%" '
         f'fill="none" stroke="currentColor" stroke-width="2" font-family="sans-serif">' + "".join(o) + "</svg>")
    assert svg_ok(s) and "\n" not in s
    return s


ROOT = None  # složka, ve které se hledají kresby (nastaví main: předmět ve vaultu, např. …/TZI1)


def convert(lines):
    out, acc = [], None  # acc = (prefix, [řádky]) uvnitř víceřádkového $$ … $$
    for raw in lines:
        pre, c = PREFIX.match(raw).groups()
        if acc is not None:
            acc[1].append(c)
            if c.rstrip().endswith("$$"):
                body = "\n".join(acc[1]).strip()[2:-2]
                out += [acc[0] + r for r in display_rows(body)]
                acc = None
            continue
        s = c.strip()
        if s.startswith("$$"):
            if len(s) > 4 and s.endswith("$$") and "$$" not in s[2:-2]:
                out += [pre + r for r in display_rows(s[2:-2])]
            elif "$$" not in s[2:]:
                acc = (pre, [c])
            else:
                fail("nepodporované $$", raw)
            continue
        if "$$" in c:
            fail("$$ uprostřed řádku", raw)
        e = re.fullmatch(r"!\[\[([^\]|#]+)\.excalidraw\]\]", s)
        if e:  # nekomprimovaná kresba jako SVG, jinak (kresba z tabule jen v Obsidianu) viditelná poznámka
            svg = excalidraw_svg(e.group(1))
            out.append(pre + "{svg}" + svg if svg else f"{pre}*Řešení z tabule je kresba v Obsidianu ({e.group(1)}).*")
            continue
        if "![[" in c:
            fail("vložený soubor ![[…]]", raw)
        if ".excalidraw]]" in c:  # odkaz na plátno s rukopisem: ve vaultu, ve webu nemá smysl
            continue
        if s.startswith("<svg") and s.endswith("</svg>"):  # vlastní schéma z poznámky: jen tvary a text, žádné skripty/odkazy
            if not svg_ok(s):
                fail("nepovolené SVG", raw)
            out.append(pre + "{svg}" + s); continue
        if s == "<small>":
            out.append("{small}"); continue
        if s == "</small>":
            out.append("{/small}"); continue
        if re.search(r"<[a-zA-Z/]", c):
            fail("HTML značka", raw)
        if re.match(r"\s+([-*]|\d+\.) ", c):
            fail("vnořený seznam není podporovaný", raw)
        if re.search(r"\]\([^)]*\)|^#{4,} ", c):
            fail("odkaz [text](url) nebo nadpis 4. úrovně není podporovaný", raw)
        c = bg.clean(c.replace(" nad ", "\u00a0nad "))  # „(číslo nad šipkou)“ nesmí `fmt` vykreslit jako kombinační číslo
        if "$" in c or "[[" in c or re.search(r"\\[A-Za-z]", c):
            fail("nepřevedený LaTeX nebo odkaz", raw)
        c = re.sub(r"(?<=\d)/(?=\d)", "∕", c)  # „č. 7/2026“ nesmí `fmt` vykreslit jako zlomek
        out.append(pre + c)
    if acc is not None:
        fail("neukončené $$", acc[1][0])
    return out


def slug(t, used):
    s = unicodedata.normalize("NFD", t.lower())
    s = re.sub(r"[^a-z0-9]+", "-", "".join(ch for ch in s if not unicodedata.combining(ch))).strip("-") or "sekce"
    base, n = s, 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def main(src, stem, cviceni=False):
    text = Path(src).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit("CHYBA: chybí frontmatter")
    meta = dict(l.split(": ", 1) for l in m.group(1).split("\n") if ": " in l)
    text = text[m.end():]
    head, orig, tail = text.partition("\n## Originál\n")
    if orig and tail.strip() != "![[" + Path(src).stem + ".pdf]]" and not re.fullmatch(r"Plátno: !\[\[[^\]]+\.excalidraw\]\]", tail.strip()):
        raise SystemExit("CHYBA: sekce Originál obsahuje něco jiného než vložené pdf nebo plátno")
    global ROOT
    ROOT = next((p for p in Path(src).resolve().parents if p.parent.name == "Aktualni"), Path(src).resolve().parent)
    lines = convert(head.split("\n"))
    y, mo, d = meta["datum"].split("-")
    title = re.sub(r"^TZI1 — ", "", next(l[2:] for l in lines if l.startswith("# ")))
    secs, used = [], set()
    for ln in lines:
        h = re.match(r"(#{1,3}) (.*)", ln)
        if h and len(h.group(1)) == 1:
            secs.append({"level": 0, "heading": title, "id": "uvod", "body": []}); used.add("uvod")
        elif h:
            secs.append({"level": len(h.group(1)), "heading": h.group(2).strip(), "id": slug(h.group(2), used), "body": []})
        elif secs:
            if ln.startswith("←") or ln.strip() == "---":  # navigace ve vaultu a oddělovač
                continue
            secs[-1]["body"].append(ln)
    for s in secs:
        s["body"] = re.sub(r"\n{3,}", "\n\n", "\n".join(s["body"]).strip())
    vault = str(Path(src).resolve()).split("/Vault/", 1)[-1]
    out, key = (CVICENI, "seminars") if cviceni else (OUT, "banks")
    data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {key: {}}
    rec = {"title": title, "date": f"{int(d)}. {int(mo)}. {y}", "source": vault, "sections": secs}
    if cviceni:  # klíč = jméno souboru, k jedné bance může být víc cvičení
        data[key][Path(src).stem] = {"bank": stem, **rec}
    else:
        data[key][stem] = rec
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{Path(src).stem if cviceni else stem}: {len(secs)} sekcí -> {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[1], a[2], True) if a and a[0] == "--cviceni" else main(a[0], a[1])
