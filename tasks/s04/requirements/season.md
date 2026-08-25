# S04+S05 — plan końcówki: 5 flag z 10 zadań

Stan na 2026-08-25: **18 flag głównych** (`.flags.json` + `s01e03_proxy` poza plikiem).
Do certyfikatu brakuje **2** — `s05e03`, `s04e05` i `s04e03` zaliczone, patrz
„Co faktycznie zadziałało".
Stan wyjściowy tego dokumentu (2026-08-20) to 15 flag i 5 do zdobycia. Zostało **10 zadań** — więc po raz pierwszy w tym projekcie
możemy **wybierać**, a nie zaliczać wszystko po kolei. Ten plik trzyma wybór i kolejność;
uzasadnienia źródłowe w `source/tool-inventory.md` i `source/community-intel.md`.

## Ranking wszystkich 10 zadań

| Zadanie                    | Istota                                               | Zero-LLM?           | Infra | Brakujące zdolności             | Ryzyko kosztowe | Trudność wg społeczności        | Ocena       |
| -------------------------- | ---------------------------------------------------- | ------------------- | ----- | ------------------------------- | --------------- | ------------------------------- | ----------- |
| ~~**s05e03**~~ `shellaccess` | zdalny `grep` po archiwum, odpowiedź wypisana `echo` | ✅ całkowicie       | brak  | brak                            | **$0.00 (fakt)** | 🟢 najłatwiejsze                | **✅ 2026-08-24** |
| ~~**s04e05**~~ `foodwarehouse` | SQLite RO + SHA1 + zamówienie na miasto          | ✅                  | brak  | brak                            | **$0.00 (fakt)** | 🟢 „poszło od strzała"          | **✅ 2026-08-24** |
| ~~**s04e03**~~ `domatowo`  | 11×11, 300 pkt akcji, znajdź i ewakuuj               | ✅                  | brak  | brak                            | **$0.00 (fakt)** | 🟢 „nie jest zbyt trudne"       | **✅ 2026-08-25** |
| **s04e04** `filesystem`    | 2,6 kB notatek → 3 katalogi w wirtualnym FS          | 🟡 hybryda          | brak  | brak                            | $0.15–0.26      | 🟡 polska semantyka             | **4**       |
| **s05e04** `goingthere`    | 3×12, hinty PL/ENG, SHA1 disarm                      | 🟡 hybryda          | brak  | parser hintów (mały)            | grosze          | 🟡 jedna pułapka pojęciowa      | **5**       |
| s04e01 `okoeditor`         | 3 edycje wpisów + `done`                             | ✅                  | brak  | sesja HTTP + strip HTML         | $0–0.14         | 🟡 milcząca weryfikacja         | 6 (rezerwa) |
| s05e05 `timetravel`        | maszyna czasu, 3 skoki                               | ✅ (z obejściem BE) | brak  | brak (jeśli backend działa)     | $0–5            | 🔴 bez obejścia najtrudniejsze  | 7 (rezerwa) |
| s04e02 `windpower`         | harmonogram turbiny w **40 s**                       | ✅ (jedyna droga)   | brak  | async/równoległość              | $0–0.04         | 🔴 „po 8 godzinach poddaję się" | 8 (rezerwa) |
| s05e01 `radiomonitoring`   | strumień transkrypcji + binarek → raport             | ❌                  | brak  | **vision/OCR (AID-59)** + audio | $0.01–0.50      | 🔴                              | ODRZUCONE   |
| s05e02 `phonecall`         | rozmowa audio z operatorem                           | ❌                  | brak  | **TTS + STT**                   | **$5 / 12 h**   | 🔴🔴 rage-quit sezonu           | ODRZUCONE   |

## Rekomendowana piątka — kolejność ataku

`s05e03 → s04e05 → s04e03 → s04e04 → s05e04`

Kolejność jest rosnąca po ryzyku, nie po numerze epizodu. Każdy krok domyka jedną flagę
i nie zostawia niedokończonego stanu, którego potrzebowałby następny.

1. **s05e03 `shellaccess`** — najtańsza flaga w całym kursie i zarazem najtańszy test, czy
   hub w ogóle wpuszcza nas do S05 bez zaliczonych e01/e02 (patrz „Do sprawdzenia
   empirycznie" #1). Robimy ją pierwszą właśnie dlatego, że jest jednocześnie zadaniem
   i sondą.
2. **s04e05 `foodwarehouse`** — 677 B danych, `reset` gratis, jedna znana pułapka
   (niepełny odczyt tabeli `destinations`). Zero nowego kodu w `core/`.
3. **s04e03 `domatowo`** — powtórka `s03e03_reactor` + `s03e05_savethem`: planowanie pod
   budżetem zasobów. Mamy sprawdzony wzorzec, wskazówka „najwyższe bloki" zawęża
   przeszukiwanie przed pierwszym ruchem.
4. **s04e04 `filesystem`** — jedyne z piątki, gdzie LLM realnie coś wnosi (normalizacja
   polskiej odmiany), ale nad 2,6 kB tekstu to jedno tanie wywołanie, nie pipeline.
   `batch_mode` + `reset` czynią próby darmowymi.
5. **s05e04 `goingthere`** — ostatnie, bo wymaga najwięcej kodu (parser hintów, SHA1,
   retry na losowe błędy API). Za to mamy największą przewagę informacyjną w całej
   dziesiątce: znamy błąd, na którym wykłada się większość uczestników.

## Dlaczego pozostałe pięć odpada

- **s05e02 `phonecall` — odrzucone twardo.** Wymaga TTS+STT (zero kodu w `core/`), a
  walidator jest niedeterministyczny: to samo nagranie raz przechodzi, raz nie. Zgłoszenia:
  „ponad 5h i $5", dwa niezależne „12 godzin". Do tego moderacja komercyjnych modeli potrafi
  odmówić („przemyt ludzi"). Najgorszy możliwy stosunek wysiłku do flagi.
- **s05e01 `radiomonitoring` — odrzucone.** Jedyne zadanie wymagające przebudowy `core/llm/`
  (vision, AID-59 „Odłożone"). Koszt wejścia większy niż całe zadanie.
- **s04e02 `windpower` — pierwsza rezerwa techniczna, nie odrzucone.** Deterministycznie
  pęka w 26 s i kosztuje $0, więc merytorycznie jest w naszym typie. Odpada z piątki
  wyłącznie przez ryzyko harmonogramowe: limit 40 s wymaga równoległych wywołań (nie mamy
  warstwy async) i strojenia, a społeczność raportuje tydzień prób. Jeśli któraś z piątki
  się posypie, to jest pierwszy zamiennik.
- **s04e01 `okoeditor` — druga rezerwa.** Jedyny koszt to sesyjny scraper HTTP (mały), ale
  ma najgorszy tryb porażki w zestawie: wszystkie trzy `update` zwracają `code:110`, a
  `done` mimo to odrzuca, bez wskazania który warunek nie przeszedł. Debugowanie na ślepo.
- **s05e05 `timetravel` — trzecia rezerwa.** Obejście frontendu (`/timetravel_backend`)
  sprowadza je do skryptu HTTP i sprawdziliśmy, że endpoint żyje — ale zostaje 26 kB
  dokumentacji do sparsowania, stanowa bateria do zarządzania i trzy skoki po kolei.
  Najlepszy kandydat na szóstą flagę, gdyby piątka poszła gładko.

## Blokery do zdjęcia

### Przed całą piątką (raz, ~jedna sesja)

- **Nic infrastrukturalnego.** Żadne z pięciu nie wymaga publicznego endpointu, ngroka,
  VPS-a, embeddingów, vision ani rejestru narzędzi. `HubClient` w obecnym kształcie
  (`submit`, `get_public`, `post_api`) pokrywa cały protokół.
- **AID-58 (ngrok→VPS) można zignorować do końca kursu** — w S04/S05 nie ma odpowiednika
  s03e04.
- Utworzyć foldery zadań (`tasks/s04e03_domatowo/` itd.) zgodnie z kontraktem
  `tasks/AGENTS.md` (płasko pod `tasks/`, każdy z własnym `AGENTS.md`).

### Przed konkretnym zadaniem

- ✅ **s05e03 — sprawdzone, kolizji nie ma.** Domyślna `GuardPolicy` przepuszcza cały
  potrzebny zestaw (`grep`, `echo`, `ls`, `cat`, `find`, `head`, `tail`, `wc`), łącznie
  z `echo '{"date":…}'` — znaki JSON nie są metaznakami powłoki. Poszerzanie allowlisty
  okazało się niepotrzebne; `jq` zostało poza nią świadomie (bez potoku niewiele wnosi,
  a potoki bramka odrzuca z zasady).
- **s04e05:** żaden.
- **s04e03:** żaden (wzorzec planowania z S03 jest gotowy).
- **s04e04:** wybrać model do normalizacji polskiej odmiany. Intel wskazuje
  `gemini-3-flash` jako pewniaka; nasz domyślny `claude-haiku-4-5` jest niesprawdzony na
  tym konkretnym zadaniu.
- **s05e04:** dopisać walidację treści odpowiedzi skanera (`core.net.expect_not_html()`) —
  `/api/frequencyScanner` potrafi zwrócić `502` z pełnym HTML przy statusie sugerującym
  sukces.

## Do sprawdzenia empirycznie (zanim uznamy plan za pewny)

W S03 dwukrotnie okazało się, że intel społeczności był nieaktualny wobec żywych danych.
Kolejność poniżej to kolejność ryzyka.

1. ✅ **ROZSTRZYGNIĘTE 2026-08-24 — gatingu NIE MA.** `{"task":"shellaccess",
   "answer":{"cmd":"ls -la"}}` wróciło `{"code":100,"message":"Command executed."}` bez
   zaliczonych s05e01/s05e02. Fabuła nawiązuje do wcześniejszych epizodów, ale to
   ciągłość narracyjna, nie techniczna. **Konsekwencja: wybrana piątka zostaje bez
   zmian**, w tym s05e04. Ryzyko, które mogło wywrócić plan w całości, zdjęte pierwszym
   wywołaniem — dokładnie po to s05e03 było pierwsze.
2. ✅ **ROZSTRZYGNIĘTE 2026-08-24 — NIE zależy.** `{"tool":"help"}` oddaje pełną
   dokumentację API bez zaliczonego e04. Fabuła jest ciągłością narracyjną, nie
   techniczną. Kolejność 2↔4 bez zmian.
3. **Czy dane s04e02 są te same, co w edycji kursu?** Staff podał konkretne wartości:
   3 sztormy (04-03 18:00 → 25 m/s, 04-06 18:00 → 22 m/s, 04-07 18:00 → 28 m/s), próg
    > 14 m/s, dokładnie 4 punkty konfiguracji. **Daty są z kwietnia 2026 — prawie na pewno
    > przesunięte.** Próg i liczba punktów mogą być stałe, ale zakładać tego nie wolno.
    > Dotyczy tylko rezerwy, nie piątki.
4. **Czy `/timetravel_backend` przyjmuje nasz klucz?** Endpoint odpowiada (400 bez klucza),
   ale nie wiemy, czy `POST` z kluczem faktycznie ustawia PT-A/PT-B/PWR, czy tylko czyta.
   **Test:** `GET ?apikey=…`. Dotyczy rezerwy.
5. **Czy backendy podglądów oddają więcej niż oficjalne API?** `POST /domatowo_backend.php`
   i `POST /goingthere_backend` istnieją osobno od `/verify`. W S03 analogiczny plik
   podglądu oddał legendę mapy taniej niż API. Jeśli `goingthere_backend` zwraca pozycję
   skały w NASTĘPNEJ kolumnie, cały parser hintów staje się zbędny. **Test:** jeden `POST`
   z kluczem, przed pisaniem parsera.
6. ✅ **ROZSTRZYGNIĘTE 2026-08-24 — jest paginowana, i to nie jedyna pułapka.**
   Każda odpowiedź niesie `totalTableRows` i `limit`; dla `destinations` to `40` przy
   `limit: 30`, więc naiwny `select *` gubi 10 wierszy. `limit 30 offset 30` działa.
   **Druga pułapka, nieprzewidziana przez intel:** klucze w `food4cities.json` są z małej
   (`domatowo`), a `destinations.name` z wielkiej (`Domatowo`) — `where name = 'domatowo'`
   zwraca zero wierszy. Społeczność zlepiała te dwa problemy w jeden („miasto zniszczone");
   naprawa jednego bez drugiego nadal daje niekompletne zamówienie.
7. **Czy ID/indeksowanie zaczyna się od 1 czy od 0?** W S03E05 backend indeksował od 1 przy
   mapie od 0 — kosztowało to podejście. Dotyczy s04e03 (współrzędne typu `F6`) i s05e04
   (wiersze 1-3, kolumny 1-12).

## Co faktycznie zadziałało

### s05e03 `shellaccess` — ✅ 2026-08-24, `{FLG:HUGEFILE}`, $0.00

Za pierwszym podejściem, cztery zapytania do huba (trzy `grep`-y + zgłoszenie), zero LLM.
Plan zakładał „najtańszą flagę w całym kursie" i to się potwierdziło — ale trzy rzeczy
wyszły inaczej, niż zapowiadał rekonesans:

- **Archiwum nie jest jednym plikiem tekstowym.** Fabuła mówiła „nie jest to typowa baza
  danych, a prosty plik tekstowy"; realnie `/data` trzyma trzy pliki połączone kluczami
  (`time_logs.csv` + `locations.json` + `gps.json`), przy czym **klucze mają inne nazwy
  po obu stronach** (`location`→`location_id`, `place`→`entry_id`). To jest cała trudność
  tego zadania i nie było jej w żadnym źródle — wyszła z sondy.
- **Hub odpowiada HTTP 400 na zbyt duży stdout.** `grep -n Rafał` (37 trafień) wywraca
  zapytanie, `grep -c` na tym samym wzorcu przechodzi. Nieudokumentowane; wygląda jak
  awaria, bo `raise_for_status()` zamienia to w wyjątek. Zapytania muszą być wąskie
  z założenia — ma to znaczenie dla każdego kolejnego zadania z eksploracją przez hub.
- **Zdalny shell zjada cudzysłowy przed podziałem na tokeny**, więc wzorzec ze spacją
  (`"location_id": 219`) rozpada się na dwa argumenty. Wzorce muszą być jednym tokenem.

Potwierdziło się natomiast wszystko z `community-intel.md`: pułapka „dzień przed"
(w archiwum faktycznie nie ma o tym śladu), ostrzeżenie przed `printf`, i ocena
trudności. Deterministyczna ścieżka dała dodatkowy zysk, którego rekonesans nie
przewidział: **omija raportowane odmowy modeli Anthropic** przy „szukaniu ciała",
bo nie wykonuje żadnego wywołania providera.

Operacyjne szczegóły przeniesione do `tasks/s05e03_shellaccess/AGENTS.md`.

### s04e05 `foodwarehouse` — ✅ 2026-08-24, `{FLG:JUSTEATIT}`, $0.00

Za pierwszym podejściem, zero LLM. Ranking przewidywał „🟢 poszło od strzała" i to się
potwierdziło, ale intel społeczności **zlepiał dwie odrębne pułapki w jedną**:

- **Stronicowanie** (przewidziane, punkt #6): `destinations` ma 40 wierszy przy `limit: 30`.
- **Rozjazd wielkości liter** (nieprzewidziane): `food4cities.json` ma `domatowo`,
  `destinations.name` ma `Domatowo`. To ta pułapka faktycznie generowała forumowe pytanie
  „czy domatowo trzeba pominąć, bo miasto zniszczone" — a odpowiedź staffu naprowadzała
  na stronicowanie, czyli na tę drugą. Naprawa jednej bez drugiej nadal daje niekompletny
  komplet zamówień.

Trzecia, drobniejsza: `signatureGenerator` zwraca podpis w polu `hash`, choć `orders.create`
oczekuje go jako `signature`. `help` opisuje parametry wejściowe narzędzi, nie kształt ich
odpowiedzi — to samo dotyczyło s05e03.

Rzeczy, które okazały się nieistotne mimo pozorów: cztery zaszczepione zamówienia dla miast
spoza pliku (`done` przechodzi mimo nich, `orders.delete` niepotrzebne) i wybór twórcy
(wystarczy dowolny aktywny użytkownik roli 2 „Obsługa transportów" — wszystkie zaszczepione
zamówienia mają twórców właśnie z tej roli, i stąd wzięliśmy tę rolę, a nie z nazwy).

Operacyjne szczegóły przeniesione do `tasks/s04e05_foodwarehouse/AGENTS.md`.

### s04e03 `domatowo` — ✅ 2026-08-25, `{FLG:WEVEGOTHIM}`, $0.00

160 z 300 punktów akcji, zero LLM. Ranking i intel trafiły: „deterministycznie wychodzi
najlepiej", a jedyny sposób przegrania to przepalenie punktów. Wskazówka z sygnału
(„najwyższe bloki") zawęża 121 pól planszy do 14 jeszcze przed pierwszym ruchem.

Trzy rzeczy, których nie było w żadnym źródle i które kosztowały po jednym nieudanym
przebiegu każda:

- **`callHelicopter` kusi jako detektor trafienia** — kosztuje 0 punktów i zwraca 400,
  dopóki nikt nie potwierdził człowieka, więc wygląda na darmowy i autorytatywny test.
  Ale wywołanie testujące JEST ewakuacją: `--dry-run` przeszedł tak przez całą planszę
  i naprawdę zakończył misję. Detekcja idzie przez `getLogs` (też 0 punktów).
- **Limit 8 zwiadowców jest globalny na operację, nie na desant.** Dwa pełne
  czterosobowe desanty wyczerpują go w całości, a trzeci `create` odbija się od API
  z HTTP 400 — po wydaniu punktów na dwa poprzednie budynki.
- **Słownik komunikatów `inspect` jest otwarty.** Przebieg zdobywający flagę przyniósł
  trzy sformułowania spoza listy zebranej dzień wcześniej. Klasyfikator zwraca `None`
  dla nieznanego zdania zamiast `False` i zlicza takie przypadki — zabezpieczeniem jest
  ta gałąź, nie kompletność listy.

Model kosztu też trzeba było zmierzyć, nie przepisać: `move` raportuje `path_steps`
wliczając pole startowe, a nalicza za `path_steps - 1`.

Operacyjne szczegóły przeniesione do `tasks/s04e03_domatowo/AGENTS.md`.
