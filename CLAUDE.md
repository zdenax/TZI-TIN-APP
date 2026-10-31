# TZI Trenér

Kvíz na opakování přednášek KI/TIN. Vzor: MTCNA-app (stejné režimy a UI).

## Soubory

- `tzi_trener.py`: server (stdlib `http.server`, port 5051), výběr UI (`?ui=`, cookie `tzi_ui`, `--klasicky`) a `/api/*` routy.
- `ui/novy.html`: nové UI (výchozí), inline CSS a JS, barvy a písma přes proměnné v `:root`, dark mód.
- `ui/klasicky.html`: původní UI, už se nevyvíjí (nahoře je upozornění, odkaz „Nový vzhled“); nové funkce jsou jen v `novy.html`. Zálohy: `zaloha/tzi_trener_v1.py`, git tag `ui-v1-klasicky`.
- `banky/*.json`: jedna banka na přednášku, aplikace je najde sama. Typy otázek: `choice` (options, correct, explanation) a `input` (answer, solution). `input` s `reveal: true` je zadání bez políčka: tlačítko „Ukázat řešení“ odhalí `solution`, hodnotí si člověk sám (Zvládl/Nezvládl jsem).
- `build_bank.py`, `build_bank_2.py`, `build_bank_3.py`: generují banku 1., 2. a 3. přednášky. Příklady na výsledek se počítají ve skriptu, odpovědi neměnit ručně v JSON.
- `build_bank_4.py`: dvě banky 4. přednášky (22. 10.): `04-2026-10-22.json` (rozklad, třídy ekvivalence, zobrazení, id `4-N`) a `04k-kombinatorika.json` (kombinatorika jako vlastní modul: kombinace, kombinační číslo, Pascalovo pravidlo, id `4k-N`). Odpovědi se ověřují brute force přímo ve skriptu. Variace/kombinace s opakováním přednáška zatím neprobrala, po další přednášce doplnit.
- `build_bank_dukazy.py`: speciální sada „Důkazy (sada na cvičení)“ (`banky/02d-dukazy.json`, vede se jako 2. přednáška, id `2d-N`): přímý, nepřímý důkaz, sporem a indukce.
- `build_bank_recall.py`: banka režimu „Doplňovačka (na paměť)“ `banky/doplnovacka/04r-doplnovacka.json` (typ `recall`: `category`, `accept` = uznané varianty, první kanonická, `words` = počet slov, např. `1` nebo `"1-2"`, `explanation`; id `r-N`). Odpověď se píše z hlavy, UI ji porovná bez ohledu na velikost písmen, diakritiku a interpunkci a toleruje 1 překlep u slov delších než 5 písmen; verdikt jde ručně opravit (`gradeTask`). V menu je to čtvrtý filtr typu (Vše / Teorie / Příklady / Doplňovačka): `ALL = RECALL`, všechny režimy běží nad recall otázkami napříč přednáškami, místo přednášky se vlevo vybírá kategorie (`recallCat`, prázdná = všechny). Recall otázky patří jen do `banky/doplnovacka/` (čte je jen `/api/recall`), běžné režimy a klasický vzhled je nevidí. Kontrola: `node test_doplnovacka.js`.
- `formule.py`: připojí k zadání otázky (v `build_bank_4.py` a `build_bank_5.py`) vzorec značek, které zadání používá (C(n, k), V_k(n), P′ a další; „a / b“ vykreslí `fmt` v `novy.html` jako zlomek). Otázky, které se na vzorec samy ptají, se vynechají (`BEZ`). Nové značky doplnit do `VZORCE`.
- `ui/automat.html` + `ui/automat-core.js`: Návrhář automatů (`/automat`, odkaz z úvodu kvízu). Čistý JavaScript bez knihoven, SVG plátno. Logika (tabulka, kontrola DKA, čtení slova, stavový strom, ekvivalence automatů, úlohy `Auto.TASKS` s referenčním automatem a nezávislým predikátem) je v `automat-core.js` a jde testovat v node: `node test_automat.js`. Nová úloha = další položka v `Auto.TASKS`; test ji porovná s predikátem na slovech do délky 12. Server ho obsluhuje v `AUTOMAT_FILES` v `tzi_trener.py`. Rozpracování uživatele se ukládá do localStorage (`tzi_automat_<úloha>`).
- `progress.json`: postup, vzniká za běhu, není v gitu.

## Nová přednáška

Přidat nový soubor `banky/NN-RRRR-MM-DD.json` (id otázek `N-číslo`, aby byly unikátní napříč přednáškami). Pro výpočetní otázky použít funkce z `build_bank.py` a odpovědi ověřit nezávisle.

## Pravidla

- Každý dokument z AI má mít deklaraci využití AI (viz README).
- `novy.html` zobrazuje možnosti `choice` otázek zamíchané (Fisher-Yates, pořadí stálé v rámci sady, uvnitř se pracuje s původními klíči). Vysvětlení ani možnosti proto nesmí odkazovat na pořadí nebo písmena („druhá možnost“, „A i B“, „žádná z uvedených“).
- UI měnit v `ui/novy.html`; `ui/klasicky.html` jen při opravě chyby. Logika (JS) je v obou UI stejná, id elementů nepřejmenovávat.
- Staré screenshoty jsou v `docs/screenshots/legacy/`.
