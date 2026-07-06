#!/usr/bin/env zsh
# s01e02_findhim — TaskWarrior tree (goals -> core_task -> std_task)
# Skill: 001-papaver-tw-integration (TW 3.x, UUID-safe depends)
#
# Uruchom LOKALNIE (nie w sandboxie Cowork — tu nie ma dostępu do TW):
#   zsh tasks/s01e02_findhim/setup_tw.sh
#
# Idempotencja: NIE jest idempotentny — uruchom raz. Jeśli trzeba powtórzyć,
# najpierw usuń poprzednie taski: `task project:aid4u.s01e02 delete`

set -euo pipefail

# --- twadd-child (z SKILL.md, powielone tu na wypadek braku w .zshrc) ---
twadd-child() {
  local parent_id=$1; shift
  local parent_uuid
  parent_uuid=$(task _get "${parent_id}".uuid)
  task add "$@" depends:"${parent_uuid}"
}

add_id() {
  task add "$@" | grep -oE 'Created task [0-9]+' | grep -oE '[0-9]+'
}

child_id() {
  local parent=$1; shift
  twadd-child "$parent" "$@" | grep -oE 'Created task [0-9]+' | grep -oE '[0-9]+'
}

PROJECT="aid4u.s01e02"

# --- Level 1: goal ---
GOAL=$(add_id "s01e02 findhim: namierz osobę blisko elektrowni, ustal accessLevel, wyślij /verify" \
  project:"$PROJECT" priority:H due:+7d +goals +research)

# --- Level 2+3: Research ---
CORE1=$(child_id "$GOAL" "Research: dane wejściowe i kształt API" \
  project:"$PROJECT" priority:H due:+1d +core_task +research)
child_id "$CORE1" "Odtwórz i zapisz listę podejrzanych z S01E01 (name, surname, birthYear) do tasks/s01e02_findhim/data/suspects.json" \
  project:"$PROJECT" priority:H due:+1d +std_task +research
child_id "$CORE1" "Pobierz findhim_locations.json, sprawdź strukturę (kod PWR0000PL, lat/lon)" \
  project:"$PROJECT" priority:M due:+1d +std_task +research
child_id "$CORE1" "Dry-run POST /api/location dla jednej osoby — sprawdź kształt odpowiedzi" \
  project:"$PROJECT" priority:M due:+1d +std_task +research
child_id "$CORE1" "Dry-run POST /api/accesslevel dla tej samej osoby — sprawdź kształt odpowiedzi" \
  project:"$PROJECT" priority:M due:+1d +std_task +research

# --- Level 2+3: TDD ---
CORE2=$(child_id "$GOAL" "TDD: testy przed implementacją" \
  project:"$PROJECT" priority:H due:+2d +core_task +testing)
child_id "$CORE2" "Test haversine_distance (znane punkty, oczekiwana odległość)" \
  project:"$PROJECT" priority:H due:+2d +std_task +testing
child_id "$CORE2" "Test find_nearest_plant (dopasowanie osoby do elektrowni)" \
  project:"$PROJECT" priority:H due:+2d +std_task +testing
child_id "$CORE2" "Test parsowania birthYear z pełnej daty (np. 1987-08-07 -> 1987)" \
  project:"$PROJECT" priority:M due:+2d +std_task +testing
child_id "$CORE2" "uv run pytest -- potwierdź że nowe testy failują (czerwone)" \
  project:"$PROJECT" priority:M due:+2d +std_task +testing

# --- Level 2+3: Implementacja ---
CORE3=$(child_id "$GOAL" "Implementacja pipeline'u findhim" \
  project:"$PROJECT" priority:H due:+3d +core_task +feature)
child_id "$CORE3" "Zaimplementuj haversine_distance + find_nearest_plant" \
  project:"$PROJECT" priority:H due:+3d +std_task +feature
child_id "$CORE3" "Zaimplementuj klientów API: get_locations, get_access_level" \
  project:"$PROJECT" priority:H due:+3d +std_task +feature
child_id "$CORE3" "Złóż pipeline: podejrzani -> lokalizacje -> odległość -> accessLevel" \
  project:"$PROJECT" priority:H due:+3d +std_task +feature
child_id "$CORE3" "Dodaj setup_observability() + instrumentację Langfuse" \
  project:"$PROJECT" priority:M due:+3d +std_task +feature
child_id "$CORE3" "uv run pytest -- potwierdź zielone testy" \
  project:"$PROJECT" priority:H due:+3d +std_task +testing

# --- Level 2+3: Weryfikacja ---
CORE4=$(child_id "$GOAL" "Weryfikacja przed wysyłką" \
  project:"$PROJECT" priority:H due:+4d +core_task +testing)
child_id "$CORE4" "uv run run.py solve s01e02 --dry-run -- sprawdź wynik" \
  project:"$PROJECT" priority:H due:+4d +std_task +testing
child_id "$CORE4" "Ręczny sanity-check: odległość do elektrowni + accessLevel wiarygodne" \
  project:"$PROJECT" priority:M due:+4d +std_task +testing
child_id "$CORE4" "Zastosuj skill verification-before-completion" \
  project:"$PROJECT" priority:H due:+4d +std_task +testing

# --- Level 2+3: Submission ---
CORE5=$(child_id "$GOAL" "Submission i potwierdzenie flagi" \
  project:"$PROJECT" priority:H due:+4d +core_task)
child_id "$CORE5" "uv run run.py solve s01e02 -- wyślij do hub.ag3nts.org" \
  project:"$PROJECT" priority:H due:+4d +std_task
child_id "$CORE5" "Potwierdź flagę FLG w output / uv run run.py status" \
  project:"$PROJECT" priority:H due:+4d +std_task
child_id "$CORE5" "Wpisz flagę na hub.ag3nts.org, oznacz GOAL jako done" \
  project:"$PROJECT" priority:H due:+4d +std_task

echo ""
echo "Utworzono drzewo TW dla s01e02 (project:${PROJECT})."
echo "Start:"
echo "  task ${CORE1} start   # pierwszy std_task w Research"
echo "Podgląd:"
echo "  task project:${PROJECT} list"
