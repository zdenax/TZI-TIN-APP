# TZI Trenér

Aplikace v jednom souboru `.py` na opakování číselných soustav (KI/TIN, Teoretická informatika, 1. přednáška).

- kartičky s teorií (poziční soustavy, obecný zápis, převody),
- generované příklady na převody mezi 2, 8, 10 a 16 s postupem a kontrolou,
- aritmetika ve dvojkové soustavě (+, −, ·, :).

## Spuštění

```
python3 tzi_trener.py          # otevře se v prohlížeči (http://127.0.0.1:8000)
python3 tzi_trener.py --cli    # terminálová verze
```

Bez závislostí, stačí Python 3. Postup kartiček se ukládá do `~/.tzi_trener.json`.

Obsah vznikl s pomocí AI (Claude Sonnet 5.5, Anthropic) z mých poznámek z přednášky.

## Licence

MIT, viz [LICENSE](LICENSE).
