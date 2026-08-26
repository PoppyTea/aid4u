# s05e04_goingthere Module

## Purpose
Przelot rakietą naziemną przez siatkę 3×12 do bazy w Grudziądzu: unikanie skał na
podstawie wskazówek radiowych i rozbrajanie radarów systemu OKO. **Zero LLM.**

**Rozwiązane (2026-08-26)** — flaga `{FLG:FINALDESTINATION}`, koszt $0.00, 11 ruchów,
4 rozbrojone radary, zero rozbić. **Domyka certyfikat: 20/25.**

## Ownership
- `rocket.py`: **cała logika, funkcje czyste, zero I/O** — parser wskazówek żeglarskich,
  wybór bezpiecznego ruchu, hash rozbrajający, ratowanie zniekształconej odpowiedzi skanera.
- `solution.py`: `@task("s05e04", hub_name="goingthere")` — pętla gry, ponawianie zapytań
  do zagłuszanego API.
- `test_solution.py`: 48 testów offline, w tym **14 dosłownych komunikatów z żywego API**
  sparowanych z prawdziwą pozycją skały.
- `doc/`: treść zadania i fabuła.

## Local Contracts
- **`solve()` NIE wykonuje ostatniego ruchu** — prowadzi rakietę do kolumny 11 i zwraca
  `{"command": …}` wjeżdżający do kolumny 12. Wysyła go `BaseTask._submit()`, więc flaga
  wraca z jednego, jawnego zgłoszenia.
- `start` na wejściu resetuje planszę i losuje nową mapę, więc przebieg jest powtarzalny;
  rozbicie nic nie kosztuje poza czasem.
- Układ współrzędnych zmierzony, nie założony: **`left` = port = wiersz o jeden MNIEJ**
  (w górę), `right` = starboard = w dół. Każda z trzech komend przesuwa o kolumnę
  do przodu, także `left`/`right`.

## Trzy niezależne sposoby zginięcia
1. **Skała w następnej kolumnie** — o niej mówi wskazówka radiowa.
2. **Skała we własnej kolumnie** — patrz Pułapki, to ten najczęściej pomijany.
3. **Radar systemu OKO** — ruch bez rozbrojenia kończy się zestrzeleniem.

Do tego wyjście poza siatkę i konieczność wylądowania dokładnie w wierszu bazy.

## Pułapki (zweryfikowane na żywo)
- 🔴 **Rakieta rusza się najpierw w PIONIE, potem do przodu.** Skała w kolumnie, w której
  właśnie stoisz, blokuje docelowy wiersz tak samo jak ta z przodu — mimo że jest „obok".
  Sama wskazówka radiowa nie wystarcza; drugie źródło (`currentColumn.freeRows`) przychodzi
  za darmo w każdej odpowiedzi `/verify`. To jest ten błąd, na którym wykłada się
  większość uczestników.
- 🔴 **Zagłuszanie psuje NAZWY PÓL skanera, nie tylko składnię.** `frequency` przychodzi
  jako `frEpUeNCy`, `detectionCode` jako `beTeCTi0NC0be`, cudzysłów bywa backtickiem,
  przecinki znikają. Ani `json.loads()`, ani szukanie nazw pól wprost nie ma szans —
  stąd dopasowanie rozmyte progiem podobieństwa, nie tablica konkretnych podmian.
- 🔴 **Nawet komunikat „czysto" jest zniekształcony**: realnie `"Its cleeear"`, nie
  `"It's clear!"` z treści zadania. Dosłowne porównanie uznaje to za namierzenie.
- 🔴 **Sformułowanie wskazówki jest STAŁE dla pozycji.** Pięć zapytań pod rząd zwróciło
  identyczne zdanie — wariant językowy zmienia się między grami, nie w obrębie jednej.
  Ponawianie zapytania nie jest więc drogą do rozpoznania trudnej wskazówki; jedyną drogą
  jest poszerzenie słownika.
- 🟡 **„right now" udaje kierunek.** Zwroty czasowe trzeba wyciąć przed parsowaniem,
  inaczej zdanie wskazuje dwa kierunki naraz i staje się nieczytelne.
- 🟡 **Hub odrzuca każdy zły ruch tym samym kodem 400** — rozbicie, zestrzelenie i wyjście
  poza siatkę wyglądają identycznie, dopóki nie przeczyta się treści odpowiedzi. Dlatego
  `_advance()` przechwytuje `HTTPStatusError` i dokleja ciało do komunikatu.
- 🟡 **Skaner potrafi zwrócić `502` z pełnym HTML-em** przy statusie sugerującym sukces —
  walidacja treści (`expect_not_html()`) jest warunkiem koniecznym, nie ozdobą.
- ⚠️ `/goingthere_backend` **istnieje, ale nie da się go użyć** — odpowiada `401`
  z własnym kodem `-1000` na każdą formę klucza (`apikey`/`key`, w JSON, w query,
  w nagłówkach). Punkt #5 listy „Do sprawdzenia empirycznie" zamknięty na „nie":
  skrót omijający parser wskazówek nie istnieje.

## Model języka wskazówek
Komunikaty opisują **jeden z trzech kierunków** jako zajęty, resztę jako wolną. Parser
klasyfikuje człony zdania na „wolne"/„zajęte" i wskazuje skałę na dwa sposoby: wprost
(jeden kierunek zajęty) albo przez eliminację (dwa wolne ⇒ skała w trzecim). Eliminacja
jest konieczna — część komunikatów w ogóle nie nazywa kierunku skały („…lurking beside
**the opposite window**").

**Przeczenia odwracają sens członu**, bo obie strony występują w obu wariantach:
„The hazard is **not** trailing your wings" (boki wolne) kontra „you have room … but
**not** in the direction the craft is facing" (przód zajęty). Warunek poprawności: każde
słowo siedzi w kategorii zgodnej ze swoim **znaczeniem**, nie z wymową całego zdania —
wpisanie `not trust` do zajętych obok `trust` w wolnych odwracało sens dwa razy.

Zdanie nierozpoznane podnosi `HintUnreadable` zamiast zgadywać: rozbicie kosztuje restart
od kolumny 1.

## Work Guidance
- **Wskazówkę pobieramy tylko wtedy, gdy realnie rozstrzyga.** Skała we własnej kolumnie
  i krawędź siatki potrafią same zostawić jedno wyjście; pytanie o wskazówkę kosztuje
  wtedy wywołanie zagłuszanego API i daje kolejną okazję do nieczytelnego zdania.
- Zmierzone ~21% wywołań skanera kończy się błędem. To jest zamierzone przez autorów
  („By design… tak ma być"), więc ponawianie jest częścią rozwiązania, nie ostrożnością.
- Nowe, nierozpoznane sformułowanie → dopisz słowo do właściwej kategorii w `rocket.py`
  i dołóż je do `REAL_HINTS` w testach razem z prawdziwym kierunkiem.

## Verification
- `uv run pytest tasks/s05e04_goingthere/` — 48 testów, zero sieci.
- `uv run run.py solve s05e04 --dry-run` — pełny przelot na żywo, ostatni ruch wypisany
  zamiast wysłania.
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
