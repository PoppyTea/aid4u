# Bezpieczeństwo pętli agentowej — uzasadnienia osłon

## Purpose
Trzyma **dlaczego** dla osłon pętli agentowej. Same kontrakty (co gwarantuje kod) żyją
w `core/AGENTS.md` — tutaj są powody, kompromisy i historia, która je uzasadnia.

Ten podział istnieje, bo `core/AGENTS.md` urósł 2026-08-20 o połowę w jeden dzień,
głównie o narrację przy pięciu osłonach. Kontrakt ma być skanowalny; uzasadnienie ma
być odnajdywalne. To dwie różne potrzeby i dwa różne pliki — ten sam wzorzec, co
`observability.md`.

## Ownership
Osłony wprowadzone przed `s03e02` (AID-48, AID-62, AID-46, AID-18, AID-47, AID-50).
Kod: `core/llm/tool_errors.py`, `core/runtime/killswitch.py`, `core/hub/throttle.py`,
`core/runtime/command_guard.py`, `core/llm/adapters/gemini.py`.

## Punkt wyjścia
Każda udokumentowana strata $4-10 w komentarzach kursu do S03E02 wynikała z **braku
osłony**, nie ze złego rozumowania modelu. Ten sam epizod: $0.05 na tanim modelu wobec
$7.20 za **nieudaną** próbę. Rozrzut ×140 nie bierze się z jakości modelu, tylko z tego,
czy pętla ma bezpieczniki.

## Dlaczego błąd narzędzia musi dotrzeć do modelu (AID-48)
Do 2026-08-20 każdy wyjątek zwijał się do stałego `"ERROR: Tool execution failed."`.
Model nie odróżniał wtedy „rate limit, poczekaj" od „zły argument, popraw" — więc albo
ponawiał w kółko to samo błędne wywołanie, albo poddawał się przy błędzie przejściowym.

**Odwrócenie wcześniejszego kontraktu.** Poprzedni test wymuszał, żeby treść wyjątku
NIE docierała do modelu. Obawa była słuszna, ale środek zbyt szeroki: wycinał całą
informację diagnostyczną, żeby nie wyciekł sekret. Właściwym narzędziem jest redakcja,
nie milczenie.

**Redakcja obowiązuje też wobec telemetrii.** `logfire.exception()` dołącza AKTYWNY
wyjątek z surową treścią, a hub przyjmuje `apikey` w query stringu — więc logowanie
wyjątku wpisywałoby żywy klucz do Logfire. Świadomie tracimy traceback: typ i komunikat
niosą diagnozę, a nadrzędny span `tool.<nazwa>` trzyma kontekst wywołania.

## Dlaczego budżet kosztu jest bezpiecznikiem, nie prewencją (AID-62)
Cenę wywołania znamy dopiero **po** jego wykonaniu, więc limit ogranicza przekroczenie
do jednego wywołania, nie do zera. Alternatywą byłoby szacowanie kosztu przed wysłaniem,
co przy nieznanej długości odpowiedzi jest zgadywaniem.

**Domyślnie włączony ($1),** bo straty brały się z osłony, o której ktoś zapomniał, a nie
z jej braku w kodzie.

**`max_cost=0` znaczy „bez limitu", choć `max_seconds=0` znaczy „przerwij natychmiast".**
Asymetria jest celowa: budżet „przerwij przy pierwszym groszu" nie ma zastosowania,
a flaga „wyłącz domyślną osłonę" ma.

**Cicha awaria osłony jest groźniejsza niż jej brak.** Liczenie kosztu jest best-effort;
gdyby przy ustawionym budżecie cena się nie policzyła, przebieg wyglądałby na chroniony,
nie będąc. Stąd `record_cost(None)` krzyczy. To nie paranoja — ten sam `except Exception`
ukrywał martwe `genai_prices.calculate()` przez wiele tygodni.

**Akumulacja zmiennoprzecinkowa.** Sto wywołań po $0.01 daje `1.0000000000000007`, więc
budżet $1.00 przerywał przebieg, w którym wydano dokładnie tyle, ile wolno. Porównanie ma
margines nanodolara — dotyczy błędu reprezentacji, nie pobłażliwości wobec budżetu.

## Dlaczego 429 nie jest ponawiane (AID-46)
Shell API `s03e02` ma limit ~30 req/min, a intel społeczności podejrzewa, że **każde 429
przedłuża okno blokady**. Jeśli tak, poprzedni backoff (6 prób, 3-30 s) nie był neutralny —
każda próba dokładała karę.

Stąd zmiana polityki, nie dołożenie limitera: odstęp wymuszany **przed** wysłaniem (to
jedyny moment, w którym mamy kontrolę), a po 429 jedno długie odczekanie i najwyżej jedna
ponowna próba. Drugie 429 propaguje do modelu, który dzięki AID-48 widzi czytelny sygnał
i sam decyduje.

Jeden throttle na klienta, nie na endpoint — hub limituje **per klucz API**, więc
liczenie odstępu osobno dla `/api/shell` i `/api/toolsearch` łamałoby limit.

`/verify` zostaje bez zmian: ma serwerowo sterowaną ścieżkę przez `retry_after` w ciele.

## Dlaczego allowlista, nie blacklista (AID-47)
Blacklista odpowiada na „czego zabronić", więc każdy niewymieniony sposób zniszczenia
czegoś przechodzi. `rm -rf /` jest tylko jednym z wielu: `mkfs`, `dd of=/dev/sda`,
`shred`, `truncate`, `chmod -R 000`. Allowlista odpowiada na „co wolno" — reszta odpada
domyślnie, łącznie z tym, o czym nie pomyśleliśmy. Przy poleceniach powłoki ta różnica
jest kategorialna, nie stopniowa.

**Domyślna polityka nie zawiera żadnego polecenia zapisującego.** Zadanie potrzebujące
zapisu dokłada je jawnie przez `with_commands()` — decyzją widoczną w diffie i w review,
nie przez przeoczenie.

### Dwa obejścia znalezione sondą, nie czytaniem kodu
- **`//etc/passwd` przechodziło.** `posixpath.normpath` zachowuje dokładnie dwa wiodące
  ukośniki, bo POSIX zostawia ich znaczenie implementacji. Blokada `/etc` była dla tej
  formy zapisu ozdobą.
- **Globy przechodziły.** Powłoka rozwija je po swojej stronie, a bramka porównuje tekst
  SPRZED rozwinięcia, więc `/et[c]/passwd`, `/etc*/passwd` i `/et?/passwd` trafiały
  w `/etc`. Zakaz obowiązuje tylko w tokenach wyglądających na ścieżkę, żeby nie psuć
  wzorców `grep`; świadomym kosztem jest odrzucenie `ls /opt/*`.

To jest powód, dla którego testy bramki są pisane pod **rodziny ataku**, nie pod happy
path — obu tych dziur nie dało się zobaczyć, czytając kod.

### Czego bramka nie zrobi
Sprawdza tekst polecenia, nie stan systemu plików, więc dowiązanie symboliczne do
zakazanego katalogu jest dla niej niewidoczne. Przy pracy lokalnej właściwą odpowiedzią
jest sprawdzenie po `realpath`, nie kolejna reguła tekstowa.

## Dlaczego unikalne `ToolCall.id` to bloker, nie drobiazg (AID-18)
Adapter Gemini przy braku `id` z SDK wstawiał samą nazwę narzędzia, więc dwa wywołania
tego samego narzędzia w jednej odpowiedzi dostawały identyczny identyfikator.

Waga bierze się ze strategii kosztowej: „zaczynaj tanio" znaczy tu „zaczynaj od Gemini",
bo to Gemini rozwiązuje `s03e02` za $0.05 wobec $7.20 na Sonnecie. Tania ścieżka **jest**
ścieżką Gemini, więc pętla agentowa na tym adapterze musi być poprawna, zanim epizod
w ogóle warto zaczynać.

## Work Guidance
- Osłona, która może zawieść po cichu, jest gorsza niż jej brak — brak przynajmniej
  widać. Każda ma mieć głośną ścieżkę awaryjną.
- Kontrolę egzekwuj w kodzie, nigdy w promptcie. Staff kursu błogosławi hardcode wprost,
  bo modele łamią reguły promptowe notorycznie.
- Testy osłon pisz pod próby obejścia. Test happy path nie odróżnia osłony działającej
  od ozdoby.

## Verification
- `uv run pytest tests/core/runtime/ tests/core/hub/ tests/core/llm/` — testy osłon
- Rodziny obejść: `tests/core/runtime/test_command_guard.py`

## Child DOX Index
- None.
