"""Připojí k zadání otázky vzorce značek, které zadání používá (kdo se látku teprve učí, je nemusí znát zpaměti)."""
import re

# (značka v zadání, vzorec); „a / b“ vykreslí UI jako zlomek, „(a nad b)“ jako kombinační číslo
VZORCE = [
    (r"(?<![′\w])C\(", "C(n, k) = n! / ((n−k)!·k!)"),
    (r"(?<![′\w])C_[\wk]", "C_k(n) = n! / ((n−k)!·k!)"),
    (r"(?<![′\w])V_[\wk]", "V_k(n) = n! / (n−k)!"),
    (r"V′_", "V′_k(n) = n^k"),
    (r"(?<![′\w])P\(", "P(n) = n!"),
    (r"P′_", "P′_(k_1,…,k_n)(k) = k! / (k_1!·k_2!·…·k_n!)"),
    (r"C′_", "C′_k(n) = (n+k−1 nad k)"),
    (r"uspořádaných (dvojic|trojic)", "V_k(n) = n! / (n−k)!"),
    (r"kombinací \d\. třídy", "C_k(n) = n! / ((n−k)!·k!)"),
    (r"\(a\+b\)\^|binomické věty", "(a+b)^n = Σ (n nad k) · a^(n−k) · b^k"),
]
# otázky, které se na vzorec samy ptají, nebo ho už obsahují
BEZ = re.compile(r"^(Jaký je vzorec|Jak je definováno|Jak zní|Co znamená|Co vyjadřuje|Proč se ve vzorci)|= n!|Σ")


# slovní úlohy, u kterých se má poznat typ: dostanou všechny vzorce a pravidla výběru, ne jen jeden
SLOVNI = re.compile(r"^(Kolik trojmístných|Závodu se účastní|Kolika způsoby lze z 10|V pekárně|Kolik různých pořadí písmen má slovo KOLO)")
VSECHNY = ("V_k(n) = n! / (n−k)! (záleží na pořadí, bez opakování); V′_k(n) = n^k (záleží na pořadí, s opakováním); "
           "C_k(n) = n! / ((n−k)!·k!) (nezáleží na pořadí, bez opakování); C′_k(n) = (n+k−1 nad k) (nezáleží na pořadí, s opakováním); "
           "P(n) = n! (seřadit všech n prvků); P′_(k_1,…,k_n)(k) = k! / (k_1!·…·k_n!) (seřadit, některé prvky se opakují)")


def pripoj_vzorce(text):
    if SLOVNI.search(text):
        return f"{text} (Vzorce: {VSECHNY})"
    if BEZ.search(text):
        return text
    nalezene = [f for znacka, f in VZORCE if re.search(znacka, text)]
    return f"{text} (Vzorec: {'; '.join(nalezene)})" if nalezene else text
