"""Testy `reactor.py` — offline, zero sieci. Model fizyki + BFS na syntetycznych
planszach, plus test regresyjny wobec prawdziwych odpowiedzi API zapisanych przez
`scripts/probe_api.py` (`data/input/s03e03_reactor/`)."""

from __future__ import annotations

import json
from pathlib import Path

from tasks.s03e03_reactor.reactor import (
    GOAL_COL,
    START_COL,
    Block,
    ReactorState,
    apply_command,
    solve_bfs,
    state_from_api,
)

_PROBE_DIR = Path("data/input/s03e03_reactor")


def _load_probe(name: str) -> dict:
    return json.loads((_PROBE_DIR / name).read_text(encoding="utf-8"))


class TestBlockAdvance:
    """Odbicie na granicach — reguła wyprowadzona z sondy (patrz docstring reactor.py)."""

    def test_moves_one_row_in_current_direction(self):
        block = Block(col=2, top_row=2, direction="up")
        assert block.advance() == Block(col=2, top_row=1, direction="down")

    def test_bounces_at_top_boundary(self):
        block = Block(col=2, top_row=1, direction="down")
        assert block.advance() == Block(col=2, top_row=2, direction="down")

    def test_bounces_at_bottom_boundary(self):
        block = Block(col=5, top_row=3, direction="down")
        assert block.advance() == Block(col=5, top_row=4, direction="up")

    def test_moves_away_from_bottom_after_bounce(self):
        block = Block(col=5, top_row=4, direction="up")
        assert block.advance() == Block(col=5, top_row=3, direction="up")

    def test_occupies_death_row_only_at_max_top_row(self):
        assert Block(col=2, top_row=4, direction="up").occupies_death_row()
        assert not Block(col=2, top_row=3, direction="down").occupies_death_row()


class TestApplyCommandCollision:
    """
    Kolizja sprawdzana PO przesunięciu bloków, nie przed — potwierdzone empirycznie
    (patrz docstring `reactor.py`). Te testy kodują dokładnie te dwa zmierzone
    przypadki na żywym API.
    """

    def test_move_into_column_about_to_be_occupied_is_crushed(self):
        # Zmierzone na żywo: top_row=3,direction=down PRZED ruchem -> po ruchu
        # top_row=4 (zajmuje wiersz 5) -> zgniecenie, mimo że przed ruchem kolumna
        # była pusta w wierszu 5.
        state = ReactorState(player_col=1, blocks=(Block(col=2, top_row=3, direction="down"),))
        assert apply_command(state, "right") is None

    def test_move_into_column_about_to_be_vacated_is_safe(self):
        # Zmierzone na żywo: top_row=4,direction=up PRZED ruchem (kolumna ZAJĘTA w
        # wierszu 5) -> po ruchu top_row=3 (wycofał się) -> bezpiecznie.
        state = ReactorState(player_col=1, blocks=(Block(col=2, top_row=4, direction="up"),))
        result = apply_command(state, "right")
        assert result is not None
        assert result.player_col == 2
        assert result.blocks == (Block(col=2, top_row=3, direction="up"),)

    def test_waiting_in_own_column_can_also_crush(self):
        # Zmierzone na żywo: `wait` nie chroni, jeśli blok WŁASNEJ kolumny wejdzie
        # w wiersz 5 w tym samym ticku.
        state = ReactorState(player_col=2, blocks=(Block(col=2, top_row=3, direction="down"),))
        assert apply_command(state, "wait") is None

    def test_start_and_goal_columns_never_have_blocks_to_check(self):
        state = ReactorState(player_col=START_COL, blocks=())
        result = apply_command(state, "wait")
        assert result is not None
        assert result.player_col == START_COL

    def test_cannot_move_left_past_start_column(self):
        state = ReactorState(player_col=START_COL, blocks=())
        assert apply_command(state, "left") is None

    def test_cannot_move_right_past_goal_column(self):
        state = ReactorState(player_col=GOAL_COL, blocks=())
        assert apply_command(state, "right") is None


class TestSolveBfs:
    def test_already_at_goal_returns_empty_plan(self):
        state = ReactorState(player_col=GOAL_COL, blocks=())
        assert solve_bfs(state) == []

    def test_empty_board_walks_straight_right(self):
        state = ReactorState(player_col=START_COL, blocks=())
        path = solve_bfs(state)
        assert path == ["right"] * (GOAL_COL - START_COL)

    def test_finds_path_around_a_blocking_column(self):
        # Kolumna 2 zgniata przy natychmiastowym `right`; BFS musi wstawić `wait`
        # (albo więcej) przed przejściem, zamiast zwrócić trasę, która zgniata.
        state = ReactorState(player_col=1, blocks=(Block(col=2, top_row=3, direction="down"),))
        path = solve_bfs(state)
        assert path is not None
        assert path[0] != "right"  # natychmiastowe right = zgniecenie, sprawdzone wyżej

        # Odtwórz trasę krok po kroku — musi dotrzeć do celu bez ani jednego None.
        current = state
        for command in path:
            current = apply_command(current, command)
            assert current is not None, f"trasa BFS przechodzi przez zgniecenie na {command!r}"
        assert current.player_col == GOAL_COL

    def test_respects_max_depth(self):
        state = ReactorState(player_col=START_COL, blocks=())
        assert solve_bfs(state, max_depth=0) is None


class TestStateFromApi:
    def test_parses_player_and_blocks_sorted_by_column(self):
        response = {
            "player": {"col": 3, "row": 5},
            "blocks": [
                {"col": 4, "top_row": 1, "bottom_row": 2, "direction": "down"},
                {"col": 2, "top_row": 3, "bottom_row": 4, "direction": "up"},
            ],
        }
        state = state_from_api(response)
        assert state.player_col == 3
        assert [b.col for b in state.blocks] == [2, 4]


class TestRegressionAgainstLiveProbe:
    """
    Test regresyjny wobec PRAWDZIWYCH odpowiedzi API zapisanych przez
    `scripts/probe_api.py` (`data/input/s03e03_reactor/probe-04-wait.json` →
    `probe-05-right.json`, sekwencja start→wait→wait→wait→right→reset z
    2026-08-17). Jeśli hub kiedyś zmieni fizykę bloków, ten test to wykryje
    niezależnie od testów syntetycznych powyżej.
    """

    def test_model_predicts_next_observed_state_after_right(self):
        before = state_from_api(_load_probe("probe-04-wait.json"))
        after_live = state_from_api(_load_probe("probe-05-right.json"))

        predicted = apply_command(before, "right")

        assert predicted is not None, "prawdziwe API nie zgniotło robota na tym ruchu"
        assert predicted.player_col == after_live.player_col
        assert predicted.blocks == after_live.blocks
