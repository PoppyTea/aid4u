# tasks/s03/requirements/

## Purpose
Indeks rzeczy do zrobienia/sprawdzenia przed sezonem 3 — zarówno przed **całym
sezonem** (dług wykryty po przeglądzie S02, infrastruktura wspólna dla wielu zadań),
jak i przed **każdym pojedynczym zadaniem** (`s03eXX.md`). Materiał źródłowy (pełny
raport narzędzi + destylat komentarzy społeczności) w `source/`.

To jest INSTANCJA sezonowa ogólnej procedury opisanej w
`strategy/season-transition.md` — tamten plik trzyma kroki i kryteria, ten folder
trzyma konkretne fakty i decyzje dla S03.

## Ownership
- `season.md`: wymagania/dług przed startem CAŁEGO sezonu.
- `s03e01.md` … `s03e05.md`: checklisty przed KONKRETNYM zadaniem.
- `source/`: materiał źródłowy — pełny raport narzędzi (kategorie: konieczne / nice
  to have / fun and educational / wymagające upgradu) i destylat ~5000 linii
  komentarzy kursu do S03. Referencyjny, nie do czytania w całości przy każdym
  podejściu do zadania — `s03eXX.md` linkuje do konkretnych sekcji zamiast
  duplikować treść.

## Local Contracts
- Przed podejściem do KAŻDEGO zadania S03 (od `s03e01` włącznie): obowiązkowy
  przegląd odpowiedniego `s03eXX.md` — to jest "faza prep" z
  `strategy/season-transition.md`, nie osobny rytuał do wymyślania na nowo.
- `season.md` czyta się RAZ, na starcie sezonu — nie przy każdym zadaniu.
- Ten folder nie ma `__init__.py` i nie może go dostać — patrz `../AGENTS.md`.

## Work Guidance
- Kończąc któreś z zadań S03, zaktualizuj odpowiedni `s03eXX.md` (status: zrobione +
  co faktycznie zadziałało, nie tylko co planowano) zamiast zostawiać go jako martwą
  prognozę — ten sam błąd, którego unikamy przy `tasks/AGENTS.md` per-epizod.
- Realne infrastrukturalne poprawki wykryte przy pracy nad S03 (nowe metody
  `HubClient`, nowe moduły `core/`) dokumentuje się jak zawsze w `core/AGENTS.md` —
  ten folder trzyma PLAN i CHECKLISTĘ, nie zastępuje właściwej dokumentacji kodu.

## Verification
(none yet — patrz backlog w `season.md` o preflight/testach integracyjnych)

## Child DOX Index
- `source/`: materiał źródłowy (raport narzędzi + intel społeczności), nieużywany
  w runtime.
