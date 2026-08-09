# S03 — intel społeczności kursu (materiał źródłowy)

Destylat z ~5000 linii komentarzy kursu do S03 (`aid4u-private/00-materialy-z-kursu/
12_komentarze-do-lekcje-zadania/md/s03e0*_aid4u_comments.md`), zebrany 2026-08-08.
Wersje skrócone, per-epizod, są w `../s03e01.md` … `../s03e05.md` — ten plik to pełny
kontekst, czytany selektywnie, nie przy każdym podejściu do zadania.

## Faktyczna trudność i koszt (zgłoszenia uczestników, nie domysły)

| Ep | Trudność | Realny koszt | Uwaga |
|---|---|---|---|
| e03 `reactor` | 🟢 **najłatwiejsze** | ~$0.00–0.04 | BFS kończy w 8–12 ruchach |
| e04 `negotiations` | 🟢 łatwe-średnie | <$0.01 | „zaskakująco przyjemne", nie przeinżynierować |
| e01 `evaluation` | 🟡 średnie, **pułapka pojęciowa** | **<2 centy** | jeśli płacisz więcej, robisz to źle |
| e02 `firmware` | 🔴 **najtrudniejsze** | $0.05 … **$7.20** | rozrzut kosztu ×140 zależnie od podejścia |
| e05 `savethem` | 🔴 najtrudniejsze | $0.002 … **$4.00** | „to zadanie mnie zniszczyło" |

## Per-epizod, konkrety

### e01 `evaluation`

Główna pułapka jest **pojęciowa, nie techniczna**: reguły anomalii #2 i #3 („operator
mówi OK, a dane złe" / „operator zgłasza błąd, a dane dobre") są **niezależne** od
reguły #1. Plik z idealnymi odczytami, ale notatką o awarii, **też jest anomalią**.

Punkty kontrolne z komentarzy: ~**46 plików** wypada z checków deterministycznych,
tylko ~**6** dochodzi z klasyfikacji notatek. Jeśli LLM zwraca setki — prompt za
luźny; jeśli 22 albo 43 — filtr deterministyczny jest zepsuty.

~9953 notatek → ~2000 unikalnych → **~261 unikalnych fraz** po rozbiciu na
przecinkach. Dedup + mapowanie indeksów to cały cost-optimization tego zadania.

Batche po **50–200 notatek**, model zwraca **same indeksy**, nie treść. Wysyłanie
surowych batchy 500+ powoduje timeouty/puste odpowiedzi. Degradacja długiego
kontekstu potwierdzona od ~40–50% okna kontekstowego.

ID plików liczone od 1, nie od 0 (irytowało ludzi). Zły host → `-166 task not found:
evaluation` (w tej edycji poprawny host to `hub.ag3nts.org`).

### e02 `firmware`

**Najdroższe i najbardziej karzące zadanie w zbiorze.** Powtarzające się rage-quity,
„3 godziny na trywialność", „rozwiązałem ręcznie szybciej niż agentem". Liczba
iteracji od 5 do 47.

- `cat` na `cooler.bin` eksploduje kontekst i pali dolary — wielu straciło $5-10 na
  jednym poleceniu.
- Mylący komunikat serwera: `Configuration check failed: SAFETY_CHECK is not set in
  settings.ini.` — linia JEST, tylko zakomentowana/ze złą wartością. Kosztowało kogoś
  3 godziny.
- Sekrety **case-sensitive** — godzina stracona.
- Shell API zwraca 400 dla łańcuchów poleceń (`a && b`), `cd`, `./cooler.bin`, dodatkowych
  flag — to *ograniczony* zestaw komend, nie prawdziwy bash. Modele „kreatywnieją" po
  ~10 iteracjach i wymyślają składnię Linuksa.
- **Rate limit ≈ 30 req/min**, zwraca `{"rate_limited": true}`/429/503/ban.
  Niepotwierdzone podejrzenie: każdy 429 wydłuża okno — naiwne retry co 30s pętli się
  w nieskończoność. Fix: wychodzący rate limiter ze stałym opóźnieniem + obsługa
  stanu ban/wait. Po banie/`reboot` trzeba **odtworzyć całą konfigurację w kolejności**.
- Zakaz `/etc`, `/root`, `/proc`, oraz respektowanie `.gitignore` **w każdym katalogu**
  (cache'ować zawartość). Modele łamią to notorycznie — wymuszać w kodzie, nie w
  promptcie (staff explicite błogosławi hardcodowaną blacklistę).
- Historia shella to zamierzona ścieżka podpowiedzi (pokazuje jak binarka była
  wywołana z argumentami).
- Kształt rozwiązania (spoiler): hasło w `/home/operator/notes/pass.txt`, edycja
  `settings.ini` (odkomentować `SAFETY_CHECK`, `test_mode.enabled=false`, cooling
  `enabled=true`), `cooler.bin <hasło>`, kod `ECCS-…`.

**Modele — najostrzejszy podział w całym sezonie:**
- ✅ Zadziałały: `claude-sonnet-4-6` (często pierwszorazowe, ale **drogie**),
  `gpt-5-mini`, `gpt-5.2`/`gpt-5.4` (18-33 iteracje), `deepseek-v3`,
  `mistral-small-3.1` (15 iteracji!), `gemini-3-flash-preview` (15-26 iteracji),
  `gemini-3.1-flash-lite-preview` (11-37 iteracji), `glm-5-turbo` jako planner +
  `gpt-4o-mini` jako executor.
- ❌ Zawiodły/zapętlały się: `gpt-4o-mini` (nie potrafił nawet wywołać narzędzia
  shell), `gpt-4.1`, `gpt-4-nano`, `haiku-4.5`, `gpt-oss-20B`, małe modele lokalne.
  **Wyniki są wysoce niepowtarzalne** — ten sam model bywa i zwycięzcą, i katastrofą
  u różnych osób.

Koszty: Sonnet 4.6: **$7.20 (nieudane)**, **~$4 (nieudane, zabiło budżet $5 w 5 min)**,
$3, $1.8, $0.7, $0.637. Gemini/Flash na tym samym zadaniu: **$0.046, $0.0534, $0.05,
$0.12, "poniżej centa"**. Najlepszy pełny przebieg: $0.41 / 117 requestów / 12m38s.

### e03 `reactor`

Zdecydowanie najłatwiejszy epizod. „Najszybsze zadanie ever", „rozwiązane zwykłym
BFS, po co agenci", wielu pierwszorazowych sukcesów w 7-15 krokach. Dominująca
krytyka: to nie jest edukacyjne — API zwraca pełny stan planszy, więc LLM nie jest
ściśle potrzebny.

- Deterministyczny solver kończy w 8-12 ruchach; pętle LLM w 7-15.
- LLM-y genuinely słabe w rozumowaniu przestrzennym 2D — wchodzą w bloki. Dwa
  potwierdzone fixy: pre-digest planszy (tabela markdown / jawne hinty o
  niebezpieczeństwie) zamiast surowego outputu API; **programistyczny override**
  (jeśli LLM mówi `right` a pole zajęte, wymuś `wait`) — staff explicite popiera tę
  hybrydę.
- Few-shot przykłady „w sytuacji X rób Y" naprawiły `gpt-5-mini`. Włączenie
  `reasoning` dało `gpt-5.4-nano` ~100% trafności następnego ruchu.
- Feeduj modelowi tylko LOKALNE sąsiedztwo planszy, nie całość — oszczędza tokeny.

Modele: ✅ `gpt-5-mini`, `o4-mini`, `4o-mini`, `gpt-5.2`, `gpt-5.4-nano` z reasoning,
`gpt-oss-120b:free`, `llama3.2-vision:11b`, `qwen3:14b`, `Qwen3.5-27B`,
`ministral-3:14b`, `glm-5-turbo`. ❌ `gemini-3-flash-preview` (wchodzi w bloki),
`Qwen3.5-35B-A3B` (gorszy niż mniejszy 27B), `gemma-4-26b-a4b-it:free`
(rate-limitowany po 3 requestach).

### e04 `negotiations`

Dobrze oceniane, łatwe-do-średnich („zaskakująco przyjemne"). Prawie wszyscy
skończyli tego samego dnia. Powracająca rada: nie przeinżynierowywać.

- 🚨 Hub wymaga **DOKŁADNIE 2 narzędzi**: `Field "tools" must contain exactly 2
  elements`. Jeśli projekt potrzebuje jednego — zarejestruj to samo dwa razy.
- `/verify` zwraca `-500 "No results yet..."` nawet gdy wszystko poszło dobrze — po
  prostu ponów. `https://hub.ag3nts.org/debug` pokazuje realny ruch z cudzym agentem
  — najbardziej niedoceniane narzędzie tego epizodu.
- Zły host → `-166 task not found: negotiations (AI_Devs 3)`.
- **Pułapka w danych**: zduplikowane kody przedmiotów, np. `Akumulator AGM 48V
  150Ah,06OTEA` i `Akumulator kwasowy 12V 200Ah,06OTEA` dzielą kod. Kluczowanie
  słownika po kodzie po cichu nadpisze jeden wpis drugim.
- Zapytania cudzego agenta są krótkie i precyzyjne — sprawia to, że naiwne
  dopasowanie top-1 vector search wygląda na wystarczające; w produkcji by nie było.

Tooling: **ngrok + Express.js na :3000** to kanoniczny stack w wątku, także
**FastAPI** z pojedynczym `/api/search`. Retrieval: SQLite jako narzędzie `query`
(chwalone przez staff — „model potrzebował 1 zapytania za każdym razem"), FTS
w pamięci, embeddingi + top-k + LLM re-rank, dopasowanie rdzeni wyrazów, albo czysto
deterministyczna mapa CSV→JSON bez LLM w ogóle. `promptfoo` do testów wyjścia
narzędzia. Ostrzeżenie: „fuzzy matching to miecz obosieczny — loguj wszystko jako
JSONL".

Model ledwo ma znaczenie — LLM tylko wyciąga nazwę przedmiotu z zapytania.
`4o-mini` + SQLite wystarczyło. Koszt LLM <$0.01, ale dwa drogie incydenty z
asystentami kodującymi: ~$5.2 tokenów Copilot Premium na wygenerowanie boilerplate'u,
i ~$5 stracone gdy Claude Code obciął duże pliki danych, a potem próbował je
"naprawić" wczytując w całości do kontekstu.

### e05 `savethem`

Najtrudniejszy razem z e02, najczęściej pokonuje agentów. „To zadanie mnie
zniszczyło", „$4 poszło", „mój ulubiony wykład, ale najtrudniejsze zadanie". Dwa
odrębne tryby porażki, prawie każdy trafia w co najmniej jeden.

**Tryb porażki 1 — odkrywanie narzędzi.** Agenci niezawodnie znajdują `/api/maps` i
`/api/vehicles`, ale **prawie nigdy sami nie odkrywają `/api/books`**, gdzie żyje
legenda mapy (symbole W/G/S/T) i reguły ruchu. Agenci pętlą się pytając `/api/maps`
o legendę, której tam nie ma, potem **halucynują legendę z nieistniejącymi
symbolami**. `https://hub.ag3nts.org/api/wehicles` (literówka, jak zwraca ją
toolsearch) **404-uje** — poprawna pisownia też bywa 404 dla części osób. Do
zapytania o mapę wystarczy sama nazwa miasta.

**Tryb porażki 2 — planowanie trasy.** „Planowanie trasy przez LLM to totalna
porażka; napisanie pathfindera w Pythonie jest trywialne." Agenci nie radzą sobie z
rozumowaniem o wspólnym budżecie paliwo+jedzenie i wybierają pojazdy które giną na
wodzie.

Kluczowa nieodkrywalna mechanika: **`dismount`** — trzeba zejść z pojazdu i dokończyć
pieszo. Modele tego nie odkrywają same. Zweryfikowany fragment promptu:
*"It is possible that other actions that we don't know about can be used. For
example, we know that it is possible to get off current vehicle."*

Przykładowe rozwiązane wystąpienie: rakieta paliwo 1/jedzenie 0.1 na ruch (nie może
przejść wody/przepaści), samochód jedzenie 1/paliwo 0.7 (ginie na wodzie), koń
jedzenie 1.6/paliwo 0, marsz jedzenie 2.5/paliwo 0. Zwycięska trasa: rakieta 8 ruchów
lądem → `dismount` → marsz 3 pola przez wodę. Suma: jedzenie 8.3/10, paliwo 8/10 —
budżet ciasny, plan zachłanny zawodzi.

**Zwycięska architektura (potwierdzona niezależnie kilka razy):** dwie fazy. (1) tani/
słaby explorer-agent odkrywa narzędzia, zrzuca WSZYSTKO (mapa, pojazdy, books) do
plików/pamięci. (2) osobny planner dostaje tylko strawiony stan — deterministyczny
Python/BFS z symulacją paliwo+jedzenie, albo silny model zmuszony wypisać trasę
krok po kroku `(x, y, fuel, food, action)` przed zgłoszeniem. Podawanie
`lastRouteError` z powrotem do kolejnej próby planu, dynamiczne system prompty,
narzędzie `plan_route` które SYMULUJE przed zgłoszeniem — wszystko pojawia się w
udanych opisach. Narzędzie `Think` zgłoszone jako ignorowane przez model.

Modele: ✅ `gemini-3.1-pro-preview` ($0.35), `sonnet-4.6` (zwykle 2. próba),
`gpt-5.4` (część: pierwszorazowe, część: totalna porażka), `gpt-5-mini` (jedna
osoba: pierwsza próba, 12 requestów, $0.0436), `GLM-5.1`,
`inception/mercury-2` (~30% skuteczności). ❌ `gpt-4.1-mini`/`4.1` (pętla 20x na tym
samym złym zapytaniu o mapę), `gemini-3.1-flash-lite-preview` (odmawia użycia
odkrytego narzędzia), `gemini-2.0-flash`, darmowe Mistral medium/large, `gpt-4o-mini`,
wszystkie testowane modele lokalne.

## Trzy lekcje przekrojowe, które zmieniają nasze domyślne nawyki

1. **Budżetuj po klasie modelu, nie po „mocy".** Ten sam e02: Sonnet 4.6 →
   $0.7–$7.20 (część prób nieudanych), Gemini 3 Flash / 3.1 Flash-Lite → $0.05. To
   niuansuje wniosek z s02e04 („Haiku zawiódł, Sonnet rozwiązał") — tam pętla była
   krótka i osłonięta. W długiej, nieosłoniętej pętli shellowej ten sam wybór jest
   kosztową katastrofą. Operacyjnie: zaczynaj tanio, twardy limit iteracji ~30-50,
   eskaluj tylko ten pod-krok który faktycznie zawodzi.
2. **Wyniki są niepowtarzalne między ludźmi.** Ten sam model bywa raportowany i jako
   zwycięzca, i jako katastrofa. Traktuj wybór modelu jak eksperyment — dokładnie
   teza lekcji e01 (evals jako sposób na świadomy dobór modelu).
3. **Czytaj komunikaty błędów Huba sceptycznie.** `-166 task not found` = zły host
   (w tej edycji `hub.ag3nts.org`), `-500` = ponów, „SAFETY_CHECK is not set" = zła
   wartość, a 404 na URL-u zwróconym przez sam `toolsearch` jest normalne.
