# TZI Trenér

Kvíz na opakování přednášek KI/TIN. Vzor: MTCNA-app (stejné režimy a UI).

## Soubory

- `tzi_trener.py`: server (stdlib `http.server`, port 5051) a celé UI. `HTML` je řetězec s inline CSS a JS, `/api/*` routy jsou dole.
- `banky/*.json`: jedna banka na přednášku, aplikace je najde sama. Typy otázek: `choice` (options, correct, explanation) a `input` (answer, solution).
- `build_bank.py`: generuje banku 1. přednášky. Příklady na výsledek se počítají ve skriptu, odpovědi neměnit ručně v JSON.
- `progress.json`: postup, vzniká za běhu, není v gitu.

## Nová přednáška

Přidat nový soubor `banky/NN-RRRR-MM-DD.json` (id otázek `N-číslo`, aby byly unikátní napříč přednáškami). Pro výpočetní otázky použít funkce z `build_bank.py` a odpovědi ověřit nezávisle.

## Pravidla

- Každý dokument z AI má mít deklaraci využití AI (viz README).
- UI měnit jen v řetězci `HTML` v `tzi_trener.py`.
