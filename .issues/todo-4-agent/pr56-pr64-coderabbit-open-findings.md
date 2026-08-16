# Todo dla agenta — PR #56, #64 (CodeRabbit) + R6-R8 (Qodo-derived)

Odpowiednik dla człowieka: `summaries-4-human/pr56-pr64-coderabbit-open-findings.md`.
Kontekst pełny tam — tu wyłącznie pozycje do wykonania, bez powtarzania uzasadnień technicznych.

| # | Priorytet | Uzasadnienie | Kiedy naprawić | Źródło |
|---|---|---|---|---|
| R6 | Średni | `tasks/s02e03_failure` ma flagę zdobytą (`{FLG:SQUASHIT}` w `.flags.json`) — bug nie blokuje niczego dziś. Ale wzorzec (własna pętla `/verify` w `solve()` bez nadpisania `_submit()`) wróci, jeśli e02 (`firmware`) potrzebuje podobnej iteracji — `core-stack-decision.md` już to zakładał jako "A1, wraca w S03". | Przed e02, TYLKO jeśli e02 faktycznie implementuje własną pętlę `/verify` w `solve()` (do potwierdzenia przy prep e02) | `.claude/review-rules.md` R6; `tasks/s02e03_failure/solution.py` (brak `_submit()`) |
| R7 | Średni | Ten sam plik co R6, ten sam profil ryzyka — teoretyczny dopóki zadanie nie jest re-runowane. | Razem z R6, jeśli w ogóle | `.claude/review-rules.md` R7; `tasks/s02e03_failure/solution.py:270-271` |
| R8 | Nieznany | Dokument źródłowy sam zaznacza: realne ryzyko zależy od tego, czy ktoś łapie wyjątki httpx wokół `get_data`/`get_public` — nie sprawdzone. | unknown — najpierw `rg -n "get_data|get_public" -B2 -A6 tasks/ core/`, dopiero potem ocena pilności | `.claude/review-rules.md` R8; `core/hub/client.py` (`_get_data_plain`, `_get_data_503_tolerant`, `get_public` bez `reraise=True`) |
| A | Niski | Zadanie zaliczone w ~5 rundach bez trafienia w ten edge case na żywych danych. Ryzyko czysto teoretyczne, aktywuje się tylko przy ponownym uruchomieniu z innym/większym logiem. | unknown — tylko jeśli s02e03 jest kiedyś rewalidowane | `summaries-4-human/pr56-pr64-coderabbit-open-findings.md` sekcja A; `tasks/s02e03_failure/solution.py` (`_hard_trim`/`_restore_component`) |
| B | Niski | Jak A — teoretyczne, niepotwierdzone w realnym przebiegu, który zdobył flagę. | unknown | jw. sekcja B |
| C | Niski | Kosmetyka dokumentacji (literówki, wording `≤` vs `<`, markdownlint) — zero wpływu na działanie. | unknown — przy najbliższej okazji edycji tych plików | jw. sekcja C |
| D | — (rozstrzygnięte) | Autor: apikey huba w `doc/zadanie.md` świadomie zostaje, nie rotować bez nowej decyzji. Nie jest to już otwarta pozycja — zapisane dla śladu, żeby nie wracało jako "nowy" finding przy kolejnym skanie. | n/d | jw. sekcja D |
| E | Wysoki | Kill switch to żywa infrastruktura używana przy KAŻDYM `solve()`, nie zamknięty epizod. Stary `.run/STOP` po cichu blokuje kolejny run bez czytelnej przyczyny — myląca awaria, nie tylko brzydki edge case. | Przed następną sesją intensywnie używającą `solve()`/kill switcha | `summaries-4-human/pr56-pr64-coderabbit-open-findings.md` sekcja E; `core/runtime/killswitch.py` (`start_run()`) |
| F | Niski | Wymaga jawnego `--max-seconds 0`/ujemnej wartości ze strony użytkownika — nie aktywuje się organicznie. Realne, ale rzadkie. | unknown | jw. sekcja F; `run.py` |
| G | Średni-Wysoki | Testy dotykające prawdziwego `.run/` mogą realnie przerwać aktywny `solve()`, jeśli `pytest` odpali się równolegle — a w tej sesji (i ogólnie w tym workflow) testy i praca nad zadaniem często zachodzą na siebie w czasie. Nie teoretyczne — wprost pasuje do sposobu pracy w tym repo. | Przed najbliższą sesją, w której testy i aktywny `solve()` mogłyby się nakładać w czasie | jw. sekcja G; `tests/core/runtime/test_killswitch.py` |
| H | Niski | Dokument źródłowy sam ocenia ryzyko jako niskie (osłania `os.setsid()`), a poprawka to Heavy Lift (wymaga nowego mechanizmu identyfikacji runu). Zła relacja koszt/ryzyko na dziś. | unknown, odłożone świadomie | jw. sekcja H; `scripts/panic.sh` |
| I | Niski | Czysty lint (`ruff RUF059`), zero wpływu funkcjonalnego. | Przy najbliższej edycji `test_killswitch.py` | jw. sekcja I; `tests/core/runtime/test_killswitch.py:260` |

## Sugerowana kolejność, jeśli robione w jednej sesji

E → G (żywa infrastruktura, realne ryzyko przy typowym sposobie pracy) → R6/R7 (razem, bo ten sam
plik) → reszta wg uznania, R8 dopiero po sprawdzeniu wywołujących.
