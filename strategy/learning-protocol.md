# Learning Protocol — AI_Devs 4 (aid4u)

> **Status:** Living Document | v0.1.0
> **Ścieżka docelowa w repo:** `docs/strategy/learning-protocol.md`
> **Ostatnia aktualizacja:** 2026-06-24

---

## Loop nauki — przegląd

Każde zadanie kursowe przechodzi przez poniższe fazy. Fazy [a]–[d] są aktywne.
Faza [e] jest zaplanowana do wdrożenia **po zakończeniu kursu** (patrz sekcja niżej).

```
[a] Inicjacja → [b] Weryfikacja → [c] Internalizacja → [d] Aplikacja
                                                              ↓
                                                    [e] Utrwalanie (FUTURE)
```

---

## Fazy aktywne

### [a] Inicjacja
**Cel:** wzbudzenie ciekawości i kontekstu przed pracą

- `[a_1]` Zaciekawienie — AI prezentuje temat zadania z perspektywy "po co to istnieje"
- `[a_2]` Podsunięcie materiałów edukacyjnych — powiązane fragmenty lekcji (via NotebookLM MCP),
  przykłady z repozytorium kursu

**Narzędzia:** `aid4u-task-kickoff` skill (NotebookLM MCP query)

---

### [b] Weryfikacja
**Cel:** upewnienie się że rozumiem zadanie i jego kontekst koncepcyjny

- `[b_1]` Zrozumienie koncepcji — seria pytań AI sprawdzających wiedzę teoretyczną
- `[b_2]` Zrozumienie zadania — seria pytań AI sprawdzających interpretację polecenia

**Narzędzia:** `aid4u-task-kickoff` skill

---

### [c] Internalizacja
**Cel:** własna synteza i wizja przed napisaniem kodu

- `[c_1]` Przetworzenie/synteza konceptów — własnymi słowami, bez podpowiedzi AI
- `[c_2]` Własna wizja rozwiązania — jak *ja* wyobrażam sobie rozwiązanie zadania

> **WAŻNE:** AI słucha, nie podpowiada. Dopiero po wyrażeniu własnej wizji
> AI może ją komentować i przycinać do MVP.
>
> **Zasada strzyżenia owcy:** jeśli zadanie nie ma flagi `done`, ZAWSZE wybieramy MVP.
> Wszystkie wodotryski trafiają do backlogu zadania (`task <UUID> annotate "backlog: ..."`)
> AI robi to stanowczo ale uprzejmie.

**Koniec fazy [c]:** wywiad uznaje się za zakończony gdy AI oceni,
że uczestnik rozumie zadanie na tyle żeby zacząć je realizować.

**Narzędzia:** `aid4u-task-kickoff` skill

---

### [d] Aplikacja — rzeczywista praca (≈95% czasu zadania)
**Cel:** brudzenie rąk kodem, nauka przez realne problemy

- `[d_1]` Praktyczna realizacja zadania (kod, eksperymenty, debugowanie)
- `[d_2]` Praktyczne zrozumienie tematu — insight który przychodzi *przez* robienie

**Output startu fazy [d]:**
1. Lista tasków TW wg hierarchii (patrz sekcja "Hierarchia tasków")
2. Graf zależności w Mermaid (`aid4u-task-kickoff` generuje go na końcu wywiadu)

**Narzędzia:** `001-jeremy-taskwarrior-integration` (adapted), `neurodivergent-visual-org`

---

## Hierarchia tasków TW

Wszystkie poziomy są pełnoprawnymi taskami TW (nie adnotacjami).
Ukończone zadania znikają z aktywnych widoków — to feature, nie kosmetyka.

| Poziom | Tag | Limit czasu | Opis |
|--------|-----|-------------|------|
| 1 | `+goals` | brak | Główny cel do osiągnięcia w zadaniu. Fundament ukończenia. |
| 2 | `+core_task` | ≤3h (opt. 1h) | Czynności konieczne do osiągnięcia `goal`. |
| 3 | `+std_task` | ≤30min | Konkretne, wąskie czynności. Mniej abstrakcji. |
| 4 | `+micro_task` | ≤5min | Bardzo konkretne akcje. Brak XP — ale nadal TW task. |

**Zasada minimalnej granularności:**
- Domyślnie: `goals` + `core_task`
- Niższe poziomy dodawane na żądanie lub gdy temat jest złożony/nowy
- Można pominąć poziomy jeśli uczestnik sprawnie porusza się w temacie

**Wyjątki i reguły kontekstowe:**

1. **Tryb hiperfocus (rosnące momentum):**
   Jeśli sesja wykazuje wyraźnie rosnące momentum (szybkie ukończenia kolejnych tasków,
   brak przerw w TimeWarrior), granularność zostaje **zamrożona na aktualnym poziomie**
   do końca sesji. Nie zwiększamy ceremonii gdy coś "idzie".
   Koniec sesji = duże przerwy między taskami w TimeWarrior
   (TimeWarrior jako detektor stanu sesji — dodatkowa przewaga micro-tasków jako TW tasks).

2. **Zadania z sezonu 01 (`s01`):**
   Domyślnie stosujemy **najwyższą granularność** (wszystkie 4 poziomy).
   Uzasadnienie: s01 to fundament — lepiej przesadzić z dokładnością niż pominąć.

**Projekt TW:** `project:aid4u.sXX.eYY`
Przykład: `project:aid4u.s01.e02`

**Zależności — zawsze UUID, nie numeric ID (TW 3.x):**
```bash
PARENT=$(task _get <id>.uuid)
task add "opis" project:aid4u.s01.e02 +core_task depends:$PARENT
```

**Pomocnicza funkcja ZSH (wymagana przez skill):**
```zsh
twadd-child() {
  local parent_id=$1; shift
  local parent_uuid=$(task _get ${parent_id}.uuid)
  task add "$@" depends:${parent_uuid}
}
# użycie: twadd-child 42 "opis zadania" project:aid4u.s01.e02 +std_task
```

---

## [e] Utrwalanie — PLAN PRZYSZŁY

> ⚠️ **Status: BACKLOG — wdrożenie po zakończeniu kursu AI_Devs 4 (po 01.09.2026)**
> Zapisane teraz bo wizja jest świeża. Nie implementować przedwcześnie.

### Opis

Po ukończeniu zadania (lub na bieżąco podczas sesji) system zbiera sygnały
że uczestnik czegoś nie rozumie dobrze, tworzy materiały do aktywnych powtórek
i planuje je w TW.

### Komponenty

#### [e_1] Zbieranie sygnałów niepewności

**Dwa tryby (hybrydowe):**

1. **Automatyczny (AI)** — AI śledzi wzorce podczas sesji:
   - ponowne pytanie o to samo
   - "aa ok" / "rozumiem" bez pogłębiania
   - prośba o uproszczenie / analogię
   - odpowiedzi powierzchowne na pytania koncepcyjne

2. **Manualny (uczestnik)** — trigger słowny lub tag:
   - słowa kluczowe: "zaznacz to", "wróćmy do tego", "nie do końca"
   - tag `+review_this` na tasku
   - (do ustalenia: czy wystarczy jedno słowo kluczowe)

> ⚠️ **Ryzyko:** false negatives — jeśli uczestnik nie sygnalizuje
> niezrozumienia (lub udaje że rozumie), AI tego nie wykryje.
> Tryb manualny jest zabezpieczeniem.

#### [e_2] Generowanie materiałów do powtórek

Materiały tworzone na podstawie: zebranych sygnałów + materiałów lekcyjnych
+ repozytorium kursu.

**Taksonomia typów zadań (do zdefiniowania dokładniej przed implementacją):**

| Typ | Opis | Przykład |
|-----|------|---------|
| `fill_blank` | Uzupełnij brakujący kod | `def process(data): return ____` |
| `predict_output` | Co zwróci ta funkcja? | Podany kod → oczekiwany output |
| `spot_bug` | Co jest nie tak? | Kod z błędem logicznym |
| `explain_concept` | Wyjaśnij w 2 zdaniach | "Czym jest RAG?" |
| `write_from_tests` | Napisz implementację | Gotowe testy → kod |
| `trace_flow` | Prześledź przepływ danych | Diagram → opis co się dzieje |

> ⚠️ **Wymaganie:** przed implementacją skilla odpytującego
> każdy typ musi mieć konkretne instrukcje oceny odpowiedzi
> (szczególnie dla typów z kodem — jak ocenić poprawność?).

#### [e_3] Planowanie powtórek w TW

Projekt TW: `project:review.aid4u` (podprojekt osobny od zadań kursu — do potwierdzenia)

**SRS — decyzja do podjęcia przed implementacją:**

| Opcja | Zalety | Wady |
|-------|--------|------|
| **Anki** (zewnętrzne) | Prawdziwe SRS, sprawdzone | Dodatkowe narzędzie, integracja |
| **TW + hook** | Jeden system | Prymitywne fixed intervals, nie true SRS |

Zalecenie: zacząć od TW + hook (prymitywne ale spójne z ekosystemem),
Anki rozważyć jeśli powtórki okażą się niewystarczające.

Prymitywny SRS przez hook `on-modify`:
- task done → nowy task z `due:+2d`
- drugi done → `due:+7d`
- trzeci done → `due:+21d`
- itd. (wartości do kalibracji)

**Powiadomienia:** ntfy.sh (już w ekosystemie)

#### [e_4] Skill wykonawczy do odpytywania

> ⚠️ **Najbardziej mglisty element — wymaga osobnej specyfikacji przed implementacją**
>
> Kwestie do rozwiązania:
> - Kto/co triggeruje sesję odpytywania?
> - Jak długa jest sesja (liczba pytań, timebox)?
> - Jak oceniane są odpowiedzi otwarte?
> - Jak oceniany jest kod napisany jako odpowiedź?
> - Co się dzieje gdy odpowiedź jest częściowo poprawna?

### Infrastruktura danych

- **Teraz (jeśli potrzebne):** JSON file w repo
- **Po kursie:** SQLite (nie PostgreSQL — dla solo projektu serwer to overkill)
- **Daleka przyszłość:** PostgreSQL tylko jeśli pojawi się realny powód (multi-device, sharing)

### Powiązane skille (do stworzenia)

- `aid4u-review-capture` — zbieranie sygnałów i generowanie materiałów
- `aid4u-quiz` — skill odpytujący (wymaga specyfikacji typów zadań)

---

## Powiązane skille i narzędzia

| Skill / Narzędzie | Faza | Status |
|-------------------|------|--------|
| `aid4u-task-kickoff` | [a][b][c] | 🔜 do stworzenia |
| `aid4u-learning-mode` | [a][b] | ✅ istnieje |
| `001-jeremy-taskwarrior-integration` | [d] | 🔧 wymaga adaptacji TW 3.x |
| `neurodivergent-visual-org` | [d] | ✅ istnieje |
| `aid4u-neurowarrior-progress` | [d] | ✅ istnieje |
| `aid4u-review-capture` | [e] | 📋 backlog (post-kurs) |
| `aid4u-quiz` | [e] | 📋 backlog (post-kurs) |

---

## Backlog — pomysły do rozważenia w przyszłości

- **Hermes-style progressive skill unlock:** skille zaczynają pasywnie obserwować,
  odblokowują się gdy uczestnik wykaże zrozumienie tematu.
  Zasada: zrozumienie → dostęp do AI superpower (nie odwrotnie).
  *Duży projekt, zdecydowanie post-kurs.*

- **XP per umiejętność** (nie tylko per task) — tracking wiedzy domenowej
  osobno od trackingu postępu w zadaniach.

- **Eksport do Anki** z NotebookLM jako źródłem materiałów.
