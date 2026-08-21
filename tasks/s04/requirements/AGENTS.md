# tasks/s04/requirements/

## Purpose
Rekonesans końcówki kursu: **10 pozostałych zadań (S04E01–E05, S05E01–E05), z których
trzeba wybrać 5** dających certyfikat. To INSTANCJA procedury z
`strategy/season-transition.md`, ale w trybie SELEKCJI, nie przygotowania do całego sezonu —
pierwszy raz w tym projekcie mamy więcej zadań niż potrzebnych flag.

## Ownership
- `season.md`: ranking wszystkich 10 zadań, rekomendowana piątka z kolejnością ataku,
  jawne powody odrzucenia pozostałych, blokery i lista rzeczy do sprawdzenia empirycznie.
  **To jest plik do czytania przed startem końcówki.**
- `source/tool-inventory.md`: zdolności potrzebne w S04/S05 w podziale mamy / do
  zbudowania / nice-to-have, zmierzone rozmiary danych wejściowych, potwierdzone drogi
  „cheesy" (obejście frontendu s05e05, `echo` w s05e03).
- `source/community-intel.md`: destylat ~9 800 linii komentarzy per zadanie — trudność,
  koszt, modele, pułapki, cytaty ze wskazaniem pliku i linii.

Per-zadaniowych plików `s04eXX.md` **celowo nie ma** (w odróżnieniu od `tasks/s03/`).
Powód: pięć z dziesięciu zadań nie zostanie tkniętych, a checklista dla zadania, którego
nie robimy, to martwy dokument. Wiedza per-zadanie żyje w `source/community-intel.md`
i przenosi się do `AGENTS.md` folderu zadania w momencie, gdy ten folder powstaje.

## Local Contracts
- Przed podejściem do KAŻDEGO z wybranej piątki: przegląd odpowiedniej sekcji
  `source/community-intel.md` + bloku „Przed konkretnym zadaniem" w `season.md`.
- `season.md` czyta się RAZ, na starcie końcówki.
- Lista „Do sprawdzenia empirycznie" w `season.md` ma pierwszeństwo przed intelem —
  w S03 dwukrotnie okazało się, że dane są łatane między edycjami kursu.
- Ten folder nie ma `__init__.py` i nie może go dostać — patrz `../AGENTS.md`.

## Work Guidance
- Kończąc któreś z zadań, zaktualizuj `season.md` (co faktycznie zadziałało vs co
  planowano) i przenieś operacyjne szczegóły do `AGENTS.md` folderu zadania — ten folder
  trzyma WYBÓR i UZASADNIENIE, nie zastępuje dokumentacji kodu.
- Jeśli któreś z piątki się posypie, rezerwy są uszeregowane w `season.md`
  (`s04e02` → `s04e01` → `s05e05`), z jawnym powodem, dlaczego są rezerwami.

## Verification
(none yet — rekonesans, nie kod)

## Child DOX Index
- `source/`: materiał źródłowy (inwentarz zdolności + intel społeczności), nieużywany
  w runtime.
