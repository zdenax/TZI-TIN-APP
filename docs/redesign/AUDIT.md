# Audit UI/UX a redesign (Zvýrazňovač)

Deklarace: dokument vznikl s pomocí Claude Sonnet 5.5 (viz README). Screenshoty před a po: `before/`, `after/` (desktop 1440, mobil 390, světlý i tmavý režim; tmavé mají příponu `-dark`).

## Nálezy (před)

1. **Menu: tok výběru nebyl vidět.** Přednáška, typ otázek a režim byly tři oddělené bloky bez návaznosti, typ otázek stál nad hlavním tlačítkem a nebylo jasné, že se vztahuje k vybrané přednášce. Devět režimů ve stejných řádcích bez hierarchie.
2. **Hlavní tlačítko neříkalo, jak na tom jsem.** „Začít od první otázky“ bez stavu postupu; postup byl až dole jako malé šedé tečky.
3. **Telefon: hlavní tlačítko až po ~1700 px scrollu** (přednášky a celý postup byly před ním).
4. **Obrazovka otázky: horní lišta zabírala ~280 px na telefonu** (časovač, úspěšnost a řetěz bitů ve třech řádcích), řetěz zalamoval osamocené tečky.
5. **Po odpovědi „Další“ vypadlo pod okraj obrazovky** (otázka + možnosti + zpětná vazba + vysvětlení); zpětná vazba „Špatně. Správně: A“ byla jen tučný text bez vizuální váhy.
6. **Možnosti odpovědí** byly holé řádky bez ohraničení, hint „Vyberte více“ nenápadný, nešly vybrat klávesnicí (Tab), jen písmeny A–D.
7. **Vysvětlení bez nadpisu**: nešlo poznat, jestli je to postup, nebo vysvětlení.
8. **Tap targety** pod 44 px: časovač, `q-pill`, filtry typu, odkazy „Zpět“.
9. **Glosář bez hledání**, 100+ pojmů v jednom dlouhém sloupci.
10. **Návrhář automatů: vlastní nesourodá paleta**, na telefonu tabulka δ vybíhala mimo obrazovku (dvousloupcová mřížka), tlačítka malá.
11. Chyba: `hidden` na `#opts` v teoretické fázi (8z) přebíjel `display: flex`.

## Co je opraveno

| # | Oprava |
|---|---|
| 1, 2 | Číslované kroky 1 Přednáška, 2 Co chceš procvičovat, 3 Jak procvičovat (pořadí je tu skutečné). Hlavní tlačítko má stavový pruh (správně / chybně / nové) a počty. Režimy jsou dlaždice, „Vrať se“ jako tři velké počty, zkouška v tmavé kartě. |
| 3 | Na telefonu pořadí: přednášky, typ, hlavní tlačítko, režimy; postup až pod nimi (CSS `order`). |
| 4 | Hlavička kvízu na telefonu: dva řádky (otázka a úspěšnost) vedle kapsle s časovačem; řetěz bitů hustší; aktuální otázka zvýrazněná zvýrazňovačem. |
| 5 | Spodní lišta s „Další“ je `sticky`, vždy na očích. Zpětná vazba je barevný panel s odznakem 1 / 0 a `role="status"`. |
| 6 | Možnosti jsou karty s odznakem písmene; výběr = zvýrazňovač; správně / špatně / chybělo má barvu, ohraničení i text (ne jen barvu). Tab + mezerník, `role="checkbox"`, `aria-checked`. Hint „Vyberte více“ je štítek. |
| 7 | Bloky „Výklad“, „Postup“, „Vysvětlení“ mají popisek. Zadání a vysvětlení jsou v serifu, data a postup v mono. |
| 8 | Cíle min. 44 px (časovač v kapsli 32 px, tlačítka v něm jsou široká 44 px), `q-pill` 44 px. |
| 9 | Glosář: vyhledávání bez ohledu na diakritiku, počet výsledků, karty pojmů, serifní text. |
| 10 | Návrhář: stejné tokeny, záložky jako pilulky, aktivní nástroj zvýrazňovačem, tabulka δ na telefonu v jednom sloupci. |
| 11 | Globální `[hidden] { display: none !important }`. |

## Směr: Zvýrazňovač

Student, který čte poznámky z přednášek a zvýrazňuje je. Chladný papír (`#F1F3F1`), tmavý inkoust (`#0F1B2D`), **jediný výrazný tón je žlutý zvýrazňovač** (`#FFD84A`): vybraná přednáška, vybraná možnost, aktuální otázka, aktivní nástroj, v tmavém režimu i hlavní tlačítko. Správně / chybně zůstává binární (1 zelená, 0 růžovočervená), to je vlastní „písmo“ aplikace. Modrá je jen pro odkazy a fokus (v tmavém režimu je fokus žlutý).

Písma: Bricolage Grotesque (UI a nadpisy, beze změny), **Source Serif 4** pro zadání a vysvětlení (delší čtení), JetBrains Mono pro data. Vše přes jediný odkaz Google Fonts, při nedostupnosti systémové fonty (Georgia, system-ui). Tokeny jsou v `:root` (světlý i tmavý režim) ve všech třech souborech shodně.

## Změny JS (malé, aditivní)

- `novy.html`: `updateMenuStats` plní pruh postupu a popisek (`#sbar-ok`, `#sbar-bad`, `#sbar-lab`).
- `novy.html`: v `renderQ` mají možnosti `tabIndex`, `role="checkbox"`, `aria-checked` a mezerník; `syncAction` aktualizuje `aria-checked`.
- `glosar.html`: nová funkce `initSearch` (filtr pojmů).
- Žádné id, klíče localStorage, API volání ani bodování se nezměnilo.

## Nedodělané

- Seznam přednášek má dál omezenou výšku (poslední 4 řádky, posuvný), řídí to `fitLectures`.
- Plátno návrháře (SVG) beze změn kromě barev z tokenů; dotykové ovládání na iPhonu jsem ručně nezkoušel.

## Dodatek: zpětná vazba majitele

- Menu na desktopu je na jedné obrazovce (výška okna se dělí mezi sloupce), seznam přednášek má pevnou výšku přesně 5 řádků (`--lec-row`), stejně vysoké řádky, scroll-snap, vybraná přednáška se při načtení posune do seznamu. Měřeno (výchozí přednáška / „Všechny dohromady“): 1280x720 720 / 751 px, 1440x900 900 / 900, 1920x1080 1080 / 1080.
- Modrý směr: světle modré pozadí a gradient, modré hlavní tlačítko (bílý text 8,3:1), v tmavém režimu tmavě modré pozadí a světlejší modrá; žlutá zůstala jako hover a v logu.
- Hlavička: Návrhář automatů, Glosář, Výpisky (rozbalovací nabídka glosářů, max. 8 řádků, Esc, šipky, kliknutí mimo zavře).
- Glosář: hledání jako Ctrl+F (zvýraznění všech shod, čítač, Enter / Shift+Enter, Esc, Ctrl/Cmd+F zaměří pole).
- Odstraněn odkaz „Starý vzhled“ z menu (klasicky.html i route `?ui=` zůstaly).
