# S04+S05 — inwentarz zdolności (materiał źródłowy)

Rekonesans 2026-08-20, po zamknięciu S03 (15 flag głównych). **Do certyfikatu brakuje
5 flag, a zostało 10 zadań** — dlatego ten plik obejmuje OBA sezony naraz i traktuje je
jako jedną kampanię wyboru, nie dwa osobne przeglądy sezonowe. Destylat komentarzy
społeczności: `community-intel.md`. Ranking i kolejność ataku: `../season.md`.

Wszystkie dane wejściowe sprawdzone empirycznie 2026-08-20 (rozmiary z `curl -o /dev/null`,
nie z domysłu).

## Czym są zadania S04/S05

| Ep | Zadanie | Istota | Charakter |
|---|---|---|---|
| s04e01 | `okoeditor` | 3 edycje wpisów w panelu OKO przez API + `done` | **Scraper sesyjny.** API jest tylko do ZAPISU (`help`/`update`/`done`), dane czyta się z HTML panelu |
| s04e02 | `windpower` | Harmonogram turbiny w oknie **40 sekund** | **Wyścig z zegarem.** Async queue + równoległość; LLM w pętli praktycznie dyskwalifikuje |
| s04e03 | `domatowo` | Mapa 11×11, 300 pkt akcji, znajdź człowieka, wezwij helikopter | **Czysty algorytm** + budżet zasobów (wariant s03e05) |
| s04e04 | `filesystem` | 2,6 kB notatek Natana → 3 katalogi plików w wirtualnym FS | **Ekstrakcja z polskiego tekstu.** Malutkie dane, `reset` gratis |
| s04e05 | `foodwarehouse` | SQLite RO + podpis SHA1 + jedno zamówienie na miasto | **Deterministyczna integracja.** 677 B danych wejściowych |
| s05e01 | `radiomonitoring` | Strumień transkrypcji + binarek Base64 → 4 pola raportu | **Multimodalność.** Wymaga OCR/vision i transkrypcji audio |
| s05e02 | `phonecall` | Rozmowa audio z operatorem (base64 MP3) | **TTS+STT round-trip** z niedeterministycznym walidatorem |
| s05e03 | `shellaccess` | Zdalny shell nad archiwum logów w `/data` | **`grep` + `echo`.** Odpowiedź to dosłownie wypisany JSON |
| s05e04 | `goingthere` | Siatka 3×12, hinty po angielsku, SHA1 disarm radaru | **Parser wskazówek + model ruchu.** Restart po crashu darmowy |
| s05e05 | `timetravel` | Maszyna czasu: API + panel WWW, 3 skoki | **Human-in-the-loop… chyba że użyje się backendu FE** (patrz niżej) |

## Rozmiary danych wejściowych (zmierzone, nie szacowane)

| Zasób | Rozmiar | Uwaga |
|---|---|---|
| `dane/natan_notes.zip` (e04.04) | **2 620 B** | Cały korpus zadania mieści się w jednym promptcie. Żadnego pipeline'u dedup nie trzeba |
| `dane/food4cities.json` (e04.05) | **677 B** | j.w. |
| `dane/timetravel.md` (e05.05) | 26 476 B | Dokumentacja urządzenia — czytana raz, parsowana kodem |
| `domatowo_preview` (e04.03) | 136 302 B | HTML; dane leci z `POST /domatowo_backend.php`, nie z inline'u |
| `goingthere_preview` (e05.04) | 28 658 B | j.w., `POST /goingthere_backend` (401 bez apikey) |
| `timetravel_preview` (e05.05) | 64 815 B | j.w., `/timetravel_backend` (400 bez apikey) |
| `oko.ag3nts.org/` (e04.01) | 19 188 B | Panel logowania; podstrony podobnego rzędu |
| e05.01 `listen` | nieznany | Strumień, nie plik. Binarki w Base64 potrafią być duże — patrz ostrzeżenie w treści zadania |

**Wniosek kosztowy:** poza s05e01 żadne z tych zadań nie ma danych, które mogłyby wysadzić
kontekst. Ryzyko kosztowe S04/S05 leży w **pętli** (liczba iteracji agenta), nie w rozmiarze
wejścia — odwrotnie niż w S03E01.

## Zdolności — trzy kategorie

### ✅ MAMY (reuse, zero kosztu wejścia)

| Co | Gdzie | Obsługuje |
|---|---|---|
| `HubClient.submit()` z retry 503/429 | `core/hub/client.py` | wszystkie 10 zadań — cały protokół S04/S05 to `POST /verify` |
| `HubClient.get_public()` | `core/hub/client.py` | `natan_notes.zip`, `food4cities.json`, `timetravel.md`, wszystkie `*_preview` |
| `HubClient.post_api()` + throttle 429 | `core/hub/client.py` | s05e04 (`/api/frequencyScanner`, `/api/getmessage`) — jedyne zadanie z S04/S05 sięgające po `/api/*` |
| `core.net.expect_binary()` / `expect_not_html()` | `core/net.py` | s04e04 (zip), s05e04 (skaner potrafi zwrócić `502` z pełnym HTML — patrz intel) |
| Kill switch 3-warstwowy + budżet $1 | `core/runtime/` | s04e02 (pętla polling), s05e04 (restart po crashu), s05e05 (polling `internalMode`) |
| Bramka poleceń (allowlista) | `core/runtime/` | s05e03 — zdalny shell; nasza własna bramka chroni przed poleceniem destrukcyjnym po TEJ stronie |
| Deterministyczne planowanie ścieżki / front Pareto | wzorzec z `s03e03_reactor`, `s03e05_savethem` | s04e03 (11×11, 300 pkt), s05e04 (3×12) — dokładnie ten sam kształt problemu |
| `LocalCache` | `core/hub/cache.py` | s04e02 — cache'owanie `help`/dokumentacji POZA oknem 40 s to warunek konieczny (intel) |
| `zipfile`, `hashlib`, `sqlite3` (stdlib) | — | s04e04 (zip), s04e02 (MD5), s04e05 (SHA1), s05e04 (SHA1) |
| `run_agent_loop()` + propagacja błędów narzędzi (AID-48) | `core/llm/` | opcjonalne — żadne z rekomendowanej piątki tego nie wymaga |

### ❌ DO ZBUDOWANIA (koszt wejścia, per zadanie)

| Co | Dla kogo | Rozmiar roboty | Status w Linear |
|---|---|---|---|
| **Sesja HTTP z ciasteczkami + strip HTML** (login form → `Set-Cookie` → nawigacja) | **s04e01 (blokujące)** | mały — `httpx.Client(follow_redirects=False)` + zbieranie `set-cookie`; wzorzec z komentarzy jest 1:1 przepisywalny | brak issue |
| **Równoległe/asynchroniczne wywołania huba** | **s04e02 (blokujące)** | średni — cała warstwa providerów jest synchroniczna; tu wystarczy `httpx.AsyncClient` obok `HubClient`, bez ruszania `core/llm/` | częściowo AID-„warstwa async" (opisana w S03 tool-inventory, bez własnego numeru) |
| **Vision / multimodalność** (`LLMMessage.content: str` → bloki treści) | **s05e01 (blokujące)** | duży — `types.py` + `base.py` + 4 adaptery | **AID-59, status „Odłożone"** |
| **TTS + STT** | **s05e02 (blokujące)** | duży — zero kodu w `core/`, do tego wybór dostawcy (ElevenLabs / edge-tts / Piper / Whisper) i strojenie jakości głosu | brak issue — bo dotąd niepotrzebne |
| **Parser wskazówek żeglarskich → `go/left/right`** | s05e04 | mały — tablica fraz, ~20 wzorców; alternatywa: jedno tanie wywołanie LLM na kolumnę (11 wywołań) | brak issue |

### 🟡 NICE TO HAVE (przyspiesza, nie blokuje)

- **Rejestr narzędzi / `@tool` ze schematem z sygnatury (AID-49, Backlog).** Rekomendowana
  piątka jest w całości deterministyczna, więc to nie wchodzi na ścieżkę krytyczną.
  Wraca dopiero gdybyśmy sięgnęli po s04e01 w wariancie agentowym.
- **Adapter OpenRouter (AID-61, Backlog).** Komentarze pokazują, że społeczność masowo
  jechała na OpenRouterze (`gemini-3-flash-preview`, darmowe Qwen-y). Dla nas to
  wyłącznie oszczędność, nie odblokowanie — dla zadań deterministycznych bez znaczenia.
- **Embeddingi (AID-54, Low).** Nigdzie w S04/S05 niewymagane. s04e04 (polska odmiana:
  „koparki" → „koparka") załatwia jedno tanie wywołanie LLM albo słownik ręczny nad 2,6 kB.
- **Automatyzacja przeglądarki (Playwright/Selenium).** Byłaby potrzebna dla s05e05
  (panel WWW) i pomocna dla s04e01 — **ale dla s05e05 istnieje backend omijający front**
  (niżej), a s04e01 wystarczy zwykły `httpx` + `set-cookie`. **Nie budujemy.**
  Referencja gdyby się zmieniło: `4th-devs/03_03_browser`.
- **VPS / ngrok (AID-58, Odłożone).** ⚠️ **Żadne z 10 zadań S04/S05 nie wymaga publicznego
  endpointu.** Odwrotnie niż w S03 (e04). Ten dług można zignorować do końca kursu.

## Drogi „cheesy" — potwierdzone i do zweryfikowania

1. **s05e05 `timetravel` — obejście całego frontendu.** W komentarzach jest zakodowana
   base64 instrukcja (`s05e05_aid4u_comments.md:170`), po zdekodowaniu:
   > „Wykorzystaj BE endpoint `https://hub.ag3nts.org/timetravel_backend`.
   > Pobranie aktualnej konfiguracji: `GET apikey=...`.
   > Ustawienie parametrów: `POST {"apikey":..., "mode":"active", "PTA":true, "PTB":false, "PWR":28}`.
   > Aktywacja podróży kiedy `fluxDensity = 100`: `POST /verify {"action":"timeTravel"}`"

   **Sprawdzone 2026-08-20: endpoint żyje** — `GET` bez klucza zwraca
   `{"code":-1,"message":"Invalid or missing apikey."}` (HTTP 400). To zamienia zadanie
   „asystent dla człowieka klikającego w UI" w zwykły skrypt HTTP. Treść zadania mówi
   wprost, że PT-A/PT-B/PWR ustawia się „w interfejsie WWW, a nie przez `/verify`" — i to
   jest prawda, tyle że interfejs ma własny backend.

2. **s05e03 `shellaccess` — odpowiedź da się wypisać, nie wyliczyć.** Podpowiedź base64
   w treści zadania (`s05e03_zadanie.md`) po zdekodowaniu mówi wprost:
   > „Poprawną odpowiedź możesz wyprodukować przez JSON, albo poskładać samodzielnie i wykonać:
   > `echo '{"date":"2020-01-01","city":"nazwa miasta","longitude":10.000001,"latitude":12.345678}'`"

   Czyli: `grep` po `/data`, przeczytanie wyniku oczami, jeden `echo`. Zero LLM, zero parsera.

3. **s04e01 `okoeditor` — brak akcji `create`.** `help` wystawia wyłącznie
   `help`/`update`/`done` (`s04e01_aid4u_comments.md:396-450`), a strona `uzytkownicy` jest
   read-only. Trzeci punkt zadania („spraw, aby na liście incydentów pojawił się raport o
   Komarowie") **nie ma** dedykowanej ścieżki — trzeba przerobić istniejący wpis przez
   `update`. To nie jest obejście, to jedyna droga; warto wiedzieć zawczasu, bo agent będzie
   szukał nieistniejącego `create`.

4. **Backendy podglądów (do zweryfikowania).** `POST /domatowo_backend.php` (HTTP 405 na GET:
   „Invalid method. Use POST.") i `POST /goingthere_backend` (HTTP 401 bez klucza) istnieją
   i są osobne od `/verify`. W S03 analogiczny plik podglądu oddał legendę mapy taniej niż
   API. **Niesprawdzone: czy zwracają więcej stanu niż oficjalne API** (np. całą mapę
   s04e03 zamiast `getMap`, albo pozycję skały w NASTĘPNEJ kolumnie w s05e04, co
   wyeliminowałoby parsowanie hintów). Wymaga jednego `POST` z kluczem — patrz lista
   weryfikacji w `../season.md`.

## Czego S04/S05 NIE wymagają (w odróżnieniu od S03)

- publicznego endpointu / ngroka / VPS — **żadne zadanie**
- bazy wektorowej / embeddingów — **żadne zadanie**
- dynamicznego odkrywania narzędzi (AID-50) — **żadne zadanie**
- modelu klasy Sonnet+ — komentarze pokazują `gemini-3-flash`, `gpt-4.1-nano`, darmowe
  Qwen-y i modele lokalne dowożące większość zadań; jedyne miejsca, gdzie mocniejszy model
  cokolwiek dawał, to s04e01 i s05e05, a oba planujemy robić deterministycznie

## Referencje z `4th-devs/` (fork, TypeScript)

Sprawdzone pod kątem gotowych dem do przepisania:
- `05_04_api` / `05_04_ui` — lekcja s05e04 (rakieta), warstwa API+UI
- `05_02_voice` — s05e02 (odrzucone, ale gdyby wróciło)
- `01_04_audio`, `01_04_image_recognition` — s05e01 (odrzucone)
- `03_03_browser` — automatyzacja przeglądarki (niepotrzebna, patrz wyżej)
- `04_01_garden`, `04_04_system`, `04_05_apps` — lekcje S04, tematycznie, nie 1:1 pod zadania

Dla rekomendowanej piątki **nie ma dema wartego przepisania** — to zadania integracyjne
z API Centrali, a nie ćwiczenia z biblioteki.
