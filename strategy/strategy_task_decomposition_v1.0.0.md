# Instrukcja dla agenta: dekompozycja zadania → JSON dla ./scripts/tw-import.py

## Kontekst

Jesteś agentem wspomagającym pracę nad kursem AI_Devs 4 (aid4u).
Twoim zadaniem jest przeanalizowanie opisu zadania kursowego i wyprodukowanie
pliku JSON zgodnego z formatem przyjmowanym przez `tw-import.py`.

Skrypt `tw-import.py` oczekuje struktury:

```json
{
  "_meta": { ... },
  "tasks": [ { "ref": "...", "description": "...", ... } ]
}
```

Pełna specyfikacja pól w sekcji **Format JSON** poniżej.

---

## Zasoby do przejrzenia przed pracą

Przed rozpoczęciem dekompozycji przejrzyj dostępne zasoby w tej kolejności:

1. **Treść zadania** — opis z hubu kursu (https://hub.ag3nts.org)
2. **Plik lekcji** — odpowiedni `sXXeYY_*.md` z katalogu projektu (jeśli istnieje)
3. **CLAUDE.md** — zasady projektu, wzorzec implementacji tasków
4. **llm-strategy.md** — hierarchia providerów, kiedy eskalować
5. **NotebookLM / notatki z lekcji** — jeśli dostępne przez MCP

---

## Proces dekompozycji krok po kroku

### Krok 1 — Zrozum zadanie

Odpowiedz sobie na pytania:
- Co konkretnie musi zrobić program? (wejście → wyjście)
- Czy zadanie wymaga publicznego endpointu HTTP? (jeśli tak → potrzebny VPS)
- Jakie są pułapki i nieoczywiste elementy? (format danych, limity API, autoryzacja)
- Jaki jest minimalny zestaw kroków do uzyskania flagi `{FLG:XXXXX}`?

### Krok 2 — Wyodrębnij fazy

Każde zadanie kursowe składa się zazwyczaj z faz:

| Faza | Przykładowe kroki |
|------|------------------|
| **Analiza** | Przeczytaj lekcję, zrozum format danych, sprawdź API |
| **TDD** | Napisz testy (test_solution.py) zanim zaczniesz implementację |
| **Implementacja** | Stwórz solution.py z klasą dziedziczącą BaseTask |
| **Weryfikacja** | dry-run, lokalne testy, sprawdź logi Langfuse/Logfire |
| **Submission** | `uv run run.py solve sXXeYY`, sprawdź flagę |
| **VPS** (jeśli trzeba) | deployment serwera, test endpointu |

### Krok 3 — Rozbij na atomowe taski

Każdy task powinien:
- Trwać **5–15 minut** (max 20 min dla kroków z czekaniem)
- Mieć **jeden jasny warunek ukończenia** (co sprawdzasz żeby wiedzieć że gotowe)
- Być **wykonalny bez zaglądania do innej dokumentacji** (adnotacje mają to zapewniać)

**Reguły nazewnictwa:**
- `ref`: format `sXXeYY_NNN` gdzie NNN = trzycyfrowy numer (001, 002, ...)
- `description`: po polsku, konkretne (nie "zaimplementuj rozwiązanie" ale "napisz metodę solve() zwracającą listę nazwisk")

### Krok 4 — Przypisz atrybuty

| Atrybut | Zasada |
|---------|--------|
| `project` | Zawsze `aid4u.sXXeYY` (sub-projekt per zadanie kursowe) |
| `priority` | `H` = blokuje flagę, `M` = ważne ale nie blokuje, `L` = nice-to-have |
| `tags` | Patrz tabela tagów poniżej |
| `est` | Realistyczny czas z buforem 1.5× (np. 10min → `PT10M`) |
| `depends_refs` | Lista `ref`-ów które muszą być done przed tym taskiem |
| `annotations` | Lista kroków/komend do wykonania (patrz sekcja Adnotacje) |

**Tabela tagów:**
```
tdd          — pisanie testów
impl         — implementacja kodu
verify       — weryfikacja/testowanie
submit       — wysyłanie do hubu kursu
api          — interakcja z zewnętrznym API
llm          — wywołania LLM
browser      — wymaga przeglądarki
terminal     — komendy w terminalu
docker       — Docker/kontenery
deploy       — deployment na VPS
research     — analiza/czytanie
```

### Krok 5 — Napisz adnotacje

Adnotacje to **instrukcja obsługi** taska — co konkretnie zrobić, żeby go ukończyć.

**Format każdej adnotacji:**
- Jedna konkretna czynność lub komenda
- Komendy gotowe do skopiowania (z prawdziwymi parametrami, nie placeholderami)
- Ostatnia adnotacja zawsze zaczyna się od `DONE gdy:` — warunek ukończenia

**Przykład dobrej adnotacji:**
```
"uv run pytest tasks/s01e01_people/test_solution.py -v"
"Dodaj fixture z przykładowymi danymi z treści zadania"
"DONE gdy: wszystkie testy w pliku przechodzą (minimum 3 testy)"
```

**Przykład złej adnotacji:**
```
"Napisz testy"      ← za ogólne
"Sprawdź czy działa" ← brak kryterium
```

---

## Format JSON

```json
{
  "_meta": {
    "description": "sXXeYY — krótki opis zadania kursowego",
    "tw_version_min": "3.0",
    "uda_required": {
      "est": {
        "type": "duration",
        "label": "Estimate",
        "taskrc_line": "uda.est.type=duration\nuda.est.label=Estimate"
      }
    }
  },
  "tasks": [
    {
      "ref": "sXXeYY_001",
      "description": "Opis zadania po polsku — konkretny i jednoznaczny",
      "project": "aid4u.sXXeYY",
      "priority": "H",
      "tags": ["research", "terminal"],
      "depends_refs": [],
      "est": "PT10M",
      "annotations": [
        "Pierwsza komenda lub krok",
        "Druga komenda lub krok",
        "DONE gdy: konkretny warunek ukończenia"
      ]
    }
  ]
}
```

**Uwagi:**
- `est` w formacie ISO 8601 duration: `PT5M` = 5 minut, `PT20M` = 20 minut
- `depends_refs` może zawierać `ref`-y z innych plików JSON (cross-project zależności)
- `annotations` jest opcjonalne, ale mocno zalecane dla złożonych kroków

---

## Wzorzec implementacji zadania kursowego

Każde zadanie kursowe w aid4u ma strukturę:

```
tasks/
└── sXXeYY_nazwa/
    ├── __init__.py          # eksport klasy
    ├── solution.py          # @task("sXXeYY") class NazwaTask(BaseTask)
    ├── prompts.py           # stałe z promptami (opcjonalne)
    └── test_solution.py     # TDD: najpierw testy, potem implementacja
```

Minimalna lista tasków dla typowego zadania kursowego (bez endpointu):

1. `_001` Przeczytaj lekcję i treść zadania, zidentyfikuj format wejścia/wyjścia `[research]`
2. `_002` Utwórz strukturę katalogów i puste pliki `[terminal, impl]`
3. `_003` Napisz testy jednostkowe (TDD — przed implementacją) `[tdd, terminal]`
4. `_004` Zaimplementuj logikę rozwiązania `[impl, llm]`
5. `_005` Uruchom testy, popraw błędy `[verify, terminal]`
6. `_006` dry-run: `uv run run.py solve sXXeYY --dry-run` `[verify, terminal]`
7. `_007` Wyślij rozwiązanie i zdobądź flagę `[submit, terminal]`

Dla zadań wymagających serwera HTTP dodaj fazę VPS z taskami analogicznymi
do `aid4u.vps.start` (v01–v08).

---

## Przykład — pełny JSON dla zadania z 3 taskami

```json
{
  "_meta": {
    "description": "s01e01 — People: wyodrębnij imiona z tekstu i sprawdź w API",
    "tw_version_min": "3.0",
    "uda_required": {
      "est": {
        "type": "duration",
        "label": "Estimate",
        "taskrc_line": "uda.est.type=duration\nuda.est.label=Estimate"
      }
    }
  },
  "tasks": [
    {
      "ref": "s01e01_001",
      "description": "Przeczytaj lekcję i zidentyfikuj format danych wejściowych/wyjściowych",
      "project": "aid4u.s01e01",
      "priority": "H",
      "tags": ["research"],
      "depends_refs": [],
      "est": "PT15M",
      "annotations": [
        "Otwórz plik projektu: s01e01_lesson-programowanie-interakcji-z-modelem-jezykowym.md",
        "Sprawdź co hub zwraca: uv run run.py solve s01e01 --dry-run",
        "Zidentyfikuj: co jest wejściem? co musi być wyjściem? jaki format odpowiedzi?",
        "DONE gdy: rozumiesz jakie dane przychodzą z hubu i co musisz odesłać"
      ]
    },
    {
      "ref": "s01e01_002",
      "description": "Napisz testy jednostkowe dla logiki ekstrakcji imion (TDD)",
      "project": "aid4u.s01e01",
      "priority": "H",
      "tags": ["tdd", "terminal"],
      "depends_refs": ["s01e01_001"],
      "est": "PT20M",
      "annotations": [
        "Edytuj: tasks/s01e01_people/test_solution.py",
        "Napisz test dla przypadku podstawowego (tekst z jednym imieniem)",
        "Napisz test dla brzegowego (brak imion, wiele imion, zduplikowane)",
        "uv run pytest tasks/s01e01_people/test_solution.py -v  # powinny FAILOWAĆ",
        "DONE gdy: testy istnieją i failują (czerwone) — to jest poprawny stan TDD"
      ]
    },
    {
      "ref": "s01e01_003",
      "description": "Zaimplementuj metodę solve() i doprowadź testy do zieleni",
      "project": "aid4u.s01e01",
      "priority": "H",
      "tags": ["impl", "llm", "terminal"],
      "depends_refs": ["s01e01_002"],
      "est": "PT20M",
      "annotations": [
        "Edytuj: tasks/s01e01_people/solution.py",
        "Domyślny model: gemini-2.5-flash (patrz llm-strategy.md przy problemach)",
        "uv run pytest tasks/s01e01_people/test_solution.py -v  # cel: wszystkie zielone",
        "uv run run.py solve s01e01 --dry-run  # test bez wysyłania",
        "uv run run.py solve s01e01  # wyślij i sprawdź flagę",
        "DONE gdy: flaga {FLG:XXXXX} widoczna w output lub uv run run.py status"
      ]
    }
  ]
}
```

---

## Checklist przed zapisaniem pliku JSON

- [ ] Każdy `ref` jest unikalny w całym pliku
- [ ] Każdy `depends_refs` wskazuje na istniejący `ref`
- [ ] Każdy task ma przynajmniej jedną adnotację
- [ ] Ostatnia adnotacja każdego taska zaczyna się od `DONE gdy:`
- [ ] `est` jest w formacie `PT{N}M` (nie `"10min"` — to stary format)
- [ ] `project` zawiera `aid4u.` prefix
- [ ] Plik jest poprawnym JSON (walidacja: `python -m json.tool plik.json`)
- [ ] Import test: `python tw-import.py plik.json --dry-run`
