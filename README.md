# TZI Trenér

> **Deklarace využití AI**
> Tento projekt (aplikaci, banky otázek a dokumentaci) vytvořil autor s pomocí nástroje **Claude Sonnet 5.5** (Anthropic, https://claude.ai, 2026). Obsah otázek vychází z autorových poznámek z přednášek KI/TIN. Správnost výpočetních příkladů je ověřena výpočtem, teoretické části doplněné AI je třeba kontrolovat proti sylabu předmětu.
> Uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (pro studijní pomůcky povinné není, autor ji uvádí dobrovolně).

Kvíz na opakování přednášek z Teoretické informatiky (KI/TIN), stylem podobný [MTCNA-app](https://github.com/zdenax/MTCNA-app). Běží v prohlížeči, spouští se jedním `.py` souborem bez závislostí.

## Spuštění

```
python3 tzi_trener.py          # http://127.0.0.1:5051, otevře se prohlížeč
python3 tzi_trener.py --lan    # navíc dostupné v místní síti (telefon)
```

Stačí Python 3, nic se neinstaluje. Aplikace čte `ui/*.html` a `banky/*.json`, spouštěj ji z celé složky repa.

## Výběr přednášky

Nahoře v menu je rozbalovací seznam **Přednáška**. Každá přednáška má vlastní banku otázek (`banky/*.json`), v seznamu je její číslo, datum a téma. Je tam i volba **Všechny přednášky dohromady**. Dále se dá přepnout typ otázek: vše, teorie (výběr A/B/C/D) nebo příklady (zadáš výsledek).

## Režimy

| Režim | Co dělá |
|---|---|
| 📦 Po X (postupně) | Bloky po X otázkách, v bloku rozpad na správné/chybné/neznámé a výběr podmnožiny |
| 🚀 Vše popořadě | Celá banka od začátku |
| 🆕 Jen neprozkoumané | Otázky, na které jsi ještě neodpovídal |
| ⚠️ Jen chybné | Otázky, které jsi zodpověděl špatně |
| ✅ Zopakovat správné | Otázky, které máš správně |
| 🎲 Náhodný výběr | Zadáš počet |
| 📖 Studuj pak testuj | Nejdřív otázky s odpovědí a postupem, pak test |
| 🎯 Ostrý test | 15 otázek, 30 minut, orientačně 60 % na úspěch |
| 💀 Sudden Death | První chyba = konec |

Postup (správně/chybně) se ukládá do `progress.json`, nabídne se **Pokračovat od poslední otázky**. U příkladů se po odpovědi ukáže celý postup (tabulka dělení, rozvoj, skupiny bitů).

## Vzhled

Aplikace má dva vzhledy. Výchozí je **nový** (postup je zobrazený jako binární řetězec: `1` správně, `0` chybně, `·` nová otázka; jeden řádek je jeden blok z režimu Po X). Starý vzhled zůstal zachovaný:

- odkaz **Starý vzhled** dole v menu (a **Nový vzhled** vpravo nahoře ve starém) přepíná mezi nimi, volba se pamatuje v cookie,
- `?ui=klasicky` nebo `?ui=novy` v adrese přepne přímo,
- `python3 tzi_trener.py --klasicky` spustí se starým vzhledem jako výchozím.

Soubory: `ui/novy.html`, `ui/klasicky.html`. Záloha celého původního skriptu je v `zaloha/tzi_trener_v1.py` (`python3 zaloha/tzi_trener_v1.py`) a v git tagu `ui-v1-klasicky` (`git checkout ui-v1-klasicky`).

## Návrhář automatů

Na adrese **`/automat`** (odkaz je v úvodu kvízu) se konečný automat nakreslí a hned zkontroluje:

- stavy a přechody se kreslí myší, dotykem i perem (přidání stavu dvojklikem, přechod tažením od stavu ke stavu, smyčky, přejmenování), počáteční stav je šipka zvenku a přijímací šipka ven jako na přednášce,
- vedle se sama přepisuje **tabulka přechodů** a hláška, jestli je automat deterministický a úplný,
- **čtení slova** po znacích se zvýrazněním aktuálního stavu a **stavový strom** podle Vaise,
- **7 úloh s přesnou kontrolou** (např. končí nulou, sudý počet jedniček, bez 11, automat z přednášky): návrh se porovná s referenčním automatem na všech možných slovech a ukáže se nejkratší slovo, na kterém se liší,
- **hotové příklady** (řešení úloh) se dají načíst do volného návrhu.

Čistý JavaScript bez knihoven, logika je v `ui/automat-core.js` a testuje se `node test_automat.js`. Rozpracovaný návrh se ukládá v prohlížeči po úlohách.

## Screenshoty

### Desktop

<table>
<tr>
<td align="center"><b>1. Hlavní menu</b><br><img src="docs/screenshots/desktop-menu.png" width="420"></td>
<td align="center"><b>2. Bloky (Po 10)</b><br><img src="docs/screenshots/desktop-chunks.png" width="420"></td>
</tr>
<tr>
<td align="center"><b>3. Detail bloku</b><br><img src="docs/screenshots/desktop-chunk-detail.png" width="420"></td>
<td align="center"><b>4. Teoretická otázka</b><br><img src="docs/screenshots/desktop-question-choice.png" width="420"></td>
</tr>
<tr>
<td align="center"><b>5. Příklad s postupem</b><br><img src="docs/screenshots/desktop-question-input.png" width="420"></td>
<td align="center"><b>6. Studijní režim</b><br><img src="docs/screenshots/desktop-study.png" width="420"></td>
</tr>
<tr>
<td align="center"><b>7. Výsledky</b><br><img src="docs/screenshots/desktop-results.png" width="420"></td>
<td align="center"><b>8. Menu v tmavém režimu</b><br><img src="docs/screenshots/desktop-menu-dark.png" width="420"></td>
</tr>
</table>

### Doplňovačka (na paměť)

Čtvrtý filtr vedle Vše / Teorie / Příklady. Po jeho zapnutí pracují všechny režimy (Po 10, Vše popořadě, Náhodný výběr, Jen chybné, Ostrý test, Sudden Death) s doplňovacími otázkami napříč přednáškami; místo přednášek se vlevo vybírá kategorie (matematický zápis, soustavy, logika, důkazy, množiny, relace, zobrazení, kombinatorika, nebo všechny). Odpověď píšeš z hlavy, u otázky je napsáno, kolik slov se čeká, a uznává se víc variant (synonyma, bez diakritiky, jeden překlep). Špatně vyhodnocenou odpověď si můžeš ručně opravit.

<table>
<tr>
<td align="center"><b>Filtr Doplňovačka v menu</b><br><img src="docs/screenshots/desktop-recall-menu.png" width="420"></td>
<td align="center"><b>Otázka</b><br><img src="docs/screenshots/desktop-recall-question.png" width="420"></td>
</tr>
<tr>
<td align="center"><b>Odpověď uznána jako překlep</b><br><img src="docs/screenshots/desktop-recall-answered.png" width="420"></td>
<td align="center"><b>Na mobilu</b><br><img src="docs/screenshots/mobile-recall-answered.png" width="260"></td>
</tr>
</table>

### Návrhář automatů

<table>
<tr>
<td align="center"><b>Hotový příklad: automat z přednášky</b><br><img src="docs/screenshots/automat/automat-priklad.png" width="420"></td>
<td align="center"><b>Úloha: návrh se nepovedl, ukáže se protipříklad</b><br><img src="docs/screenshots/automat/automat-uloha.png" width="420"></td>
</tr>
<tr>
<td align="center"><b>Čtení slova a stavový strom</b><br><img src="docs/screenshots/automat/automat-slovo.png" width="420"></td>
<td></td>
</tr>
</table>

### Mobil (`--lan`)

<table>
<tr>
<td align="center"><b>Menu</b><br><img src="docs/screenshots/mobile-menu.png" width="260"></td>
<td align="center"><b>Otázka</b><br><img src="docs/screenshots/mobile-question.png" width="260"></td>
</tr>
</table>

### Legacy (starý vzhled)

<details>
<summary>Původní screenshoty</summary>

<table>
<tr>
<td align="center"><b>Hlavní menu</b><br><img src="docs/screenshots/legacy/desktop-menu.png" width="320"></td>
<td align="center"><b>Bloky</b><br><img src="docs/screenshots/legacy/desktop-chunks.png" width="320"></td>
<td align="center"><b>Detail bloku</b><br><img src="docs/screenshots/legacy/desktop-chunk-detail.png" width="320"></td>
</tr>
<tr>
<td align="center"><b>Teoretická otázka</b><br><img src="docs/screenshots/legacy/desktop-question-choice.png" width="320"></td>
<td align="center"><b>Příklad</b><br><img src="docs/screenshots/legacy/desktop-question-input.png" width="320"></td>
<td align="center"><b>Studijní režim</b><br><img src="docs/screenshots/legacy/desktop-study.png" width="320"></td>
</tr>
<tr>
<td align="center"><b>Mobil: menu</b><br><img src="docs/screenshots/legacy/mobile-menu.png" width="200"></td>
<td align="center"><b>Mobil: příklad</b><br><img src="docs/screenshots/legacy/mobile-question.png" width="200"></td>
<td></td>
</tr>
</table>

</details>

## Banky otázek

Jedna přednáška = jeden soubor `banky/NN-RRRR-MM-DD.json`. Formát:

```json
{"title": "Téma", "lecture": 1, "date": "2026-10-01", "questions": [
  {"id": "1-1", "number": 1, "type": "choice", "text": "...",
   "options": {"A": "...", "B": "..."}, "correct": ["B"], "explanation": "..."},
  {"id": "1-30", "number": 30, "type": "input", "text": "(37)₁₀ → (?)₂",
   "hint": "...", "answer": "100101", "solution": "postup"}
]}
```

Banky 1. a 2. přednášky se generují skripty `build_bank.py` a `build_bank_2.py`, které odpovědi i postupy počítá, takže jsou správně. Nová přednáška = nový soubor v `banky/`, aplikace ho najde sama.

## Licence

MIT, viz [LICENSE](LICENSE). Obsah vznikl s pomocí AI (Claude Sonnet 5.5, Anthropic) z mých poznámek z přednášek.
