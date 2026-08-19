"""Testy core/runtime/killswitch.py — Warstwy 1/2 jednostkowo (izolowane od repo), Warstwa 0 realnie."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from core.runtime import killswitch


@pytest.fixture(autouse=True)
def _isolated_run_dir(monkeypatch, tmp_path):
    """
    Przekierowuje ścieżki `.run/` na `tmp_path` i neutralizuje `os.setsid()` dla
    wszystkich testów w tym pliku OPRÓCZ `TestPanicScriptKillsEntireProcessGroup`
    (ten test celowo działa na prawdziwym `.run/` repo i prawdziwym `panic.sh` — nie
    da się go sensownie izolować, bo skrypt bashowy rozwiązuje ścieżkę względem
    swojej lokalizacji, nie przez Pythona).

    Bez tego testy jednostkowe: (a) czytałyby/pisały PRAWDZIWY `.run/` repozytorium —
    kolizja z rzeczywistym przebiegiem uruchomionym równolegle; (b) wołałyby prawdziwy
    `os.setsid()` na PROCESIE pytest, odłączając go od sesji terminala w trakcie
    przebiegu testów (realny efekt uboczny, nie tylko teoretyczny).
    """
    run_dir = tmp_path / ".run"
    monkeypatch.setattr(killswitch, "_RUN_DIR", run_dir)
    monkeypatch.setattr(killswitch, "_PGID_FILE", run_dir / "current.pgid")
    monkeypatch.setattr(killswitch, "_STOP_FILE", run_dir / "STOP")
    monkeypatch.setattr(os, "setsid", lambda: None)
    killswitch.end_run()
    yield
    killswitch.end_run()


class TestCheckAbort:
    """Warstwa 1 — plik-wartownik .run/STOP."""

    def test_passes_when_no_stop_file_and_no_budget(self):
        """Bez wartownika i bez budżetu check_abort() jest cichym no-opem."""
        killswitch.check_abort()  # nie powinno rzucić

    def test_raises_after_request_stop(self):
        """Obecność .run/STOP musi być wykrywana i sygnalizowana jako AbortRun."""
        killswitch.request_stop()

        with pytest.raises(killswitch.AbortRun, match="STOP"):
            killswitch.check_abort()

    def test_end_run_clears_stop_file(self):
        """end_run() sprząta wartownika — kolejny check_abort() nie powinien już rzucać."""
        killswitch.request_stop()
        killswitch.end_run()

        killswitch.check_abort()  # nie powinno już rzucić


class TestStartRunClearsStaleStop:
    """
    start_run() musi czyścić wartownika z POPRZEDNIEGO przebiegu — inaczej
    request_stop() wywołane bez aktywnego zadania (albo ocalałe po twardym SIGKILL,
    które omija finally/end_run()) ubija KAŻDY kolejny przebieg na starcie, po cichu.
    """

    def test_stale_stop_file_does_not_abort_new_run(self):
        """Wartownik osierocony przed startem nie powinien przetrwać start_run()."""
        killswitch.request_stop()  # symuluje osierocony wartownik sprzed przebiegu

        killswitch.start_run()

        killswitch.check_abort()  # nie powinno rzucić — stary wartownik wyczyszczony


class TestRunBudget:
    """Warstwa 2 (per-run) — budżet wall-clock."""

    def test_no_limit_never_raises(self):
        """max_seconds=None oznacza brak budżetu — check_time() nigdy nie rzuca."""
        budget = killswitch.RunBudget(max_seconds=None)
        budget.check_time()  # nie powinno rzucić niezależnie od czasu

    def test_raises_after_max_seconds_elapsed(self):
        """Po przekroczeniu max_seconds check_time() rzuca AbortRun z czytelnym komunikatem."""
        budget = killswitch.RunBudget(max_seconds=0.01)
        time.sleep(0.05)

        with pytest.raises(killswitch.AbortRun, match="budżet czasu"):
            budget.check_time()

    def test_does_not_raise_before_max_seconds(self):
        """Świeżo utworzony budżet z dużym limitem nie rzuca natychmiast."""
        budget = killswitch.RunBudget(max_seconds=10.0)
        budget.check_time()  # nie powinno rzucić — dopiero się zaczęło

    def test_zero_seconds_is_a_valid_immediate_budget(self):
        """max_seconds=0 to poprawny (choć ekstremalny) budżet 'przerwij natychmiast', nie 'brak budżetu'."""
        budget = killswitch.RunBudget(max_seconds=0)
        time.sleep(0.01)

        with pytest.raises(killswitch.AbortRun):
            budget.check_time()


class TestStartRunActivatesBudget:
    """start_run(max_seconds=...) musi być widoczny przez check_abort(), nie tylko RunBudget bezpośrednio."""

    def test_check_abort_raises_once_budget_exceeded(self):
        """Budżet ustawiony przez start_run() jest sprawdzany automatycznie w check_abort()."""
        killswitch.start_run(max_seconds=0.01)
        time.sleep(0.05)

        with pytest.raises(killswitch.AbortRun):
            killswitch.check_abort()

    def test_check_abort_silent_without_max_seconds(self):
        """start_run(max_seconds=None) nie aktywuje żadnego budżetu."""
        killswitch.start_run(max_seconds=None)
        killswitch.check_abort()  # nie powinno rzucić

    def test_zero_seconds_activates_budget_not_disables_it(self):
        """start_run(max_seconds=0) NIE jest tym samym co max_seconds=None — 0 jest falsy w Pythonie, ale to poprawny budżet."""
        killswitch.start_run(max_seconds=0)
        time.sleep(0.01)

        with pytest.raises(killswitch.AbortRun):
            killswitch.check_abort()

    def test_negative_max_seconds_is_rejected(self):
        """Ujemny budżet czasu nie ma sensu — start_run() odrzuca go jawnie zamiast cicho ignorować."""
        with pytest.raises(ValueError, match="max_seconds"):
            killswitch.start_run(max_seconds=-1)


class TestTruncateToolResult:
    """Warstwa 2 (per-call) — obcinanie wyniku narzędzia, bez przerywania przebiegu."""

    def test_short_result_unchanged(self):
        """Wynik poniżej limitu wraca bez zmian."""
        assert killswitch.truncate_tool_result("ok", max_bytes=100) == "ok"

    def test_long_result_truncated_and_marked(self):
        """Wynik powyżej limitu jest ucięty i opatrzony czytelnym znacznikiem z oryginalnym rozmiarem."""
        long_result = "x" * 1000
        truncated = killswitch.truncate_tool_result(long_result, max_bytes=100)

        assert len(truncated.encode("utf-8")) < 1000
        assert "OBCIĘTO" in truncated
        assert "1000" in truncated  # oryginalny rozmiar w komunikacie

    def test_result_including_marker_never_exceeds_max_bytes(self):
        """Zwrócony string (treść + znacznik) mieści się CAŁKOWICIE w max_bytes, nie tylko sama treść."""
        long_result = "x" * 1000
        max_bytes = 100

        truncated = killswitch.truncate_tool_result(long_result, max_bytes=max_bytes)

        assert len(truncated.encode("utf-8")) <= max_bytes


def _process_alive(pid: int) -> bool:
    """Sprawdza czy proces o danym PID żyje, wysyłając sygnał 0 (bez efektu ubocznego)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.skipif(os.name != "posix", reason="grupy procesów są specyficzne dla POSIX")
class TestPanicScriptKillsEntireProcessGroup:
    """
    Warstwa 0, test REALNY (nie mock) — dokładnie to, o co proszono w planie: sprawdź
    że panic.sh zabija nie tylko proces-lidera, ale i jego dzieci. Gdyby zabijał tylko
    lidera, dziecko (np. długo działające polecenie shell w s03e02) zostałoby sierotą
    i dalej by działało mimo "zabitego" przebiegu.

    Celowo NIE korzysta z fixture'a `_isolated_run_dir` — operuje na prawdziwym
    `.run/` repozytorium, bo `panic.sh` (bash) rozwiązuje tę ścieżkę względem swojej
    własnej lokalizacji na dysku, niezależnie od stanu Pythona/monkeypatch.
    """

    def test_kills_parent_and_child(self):
        """panic.sh musi ubić i proces-lidera, i jego dziecko, nie tylko lidera."""
        repo_root = Path(__file__).resolve().parents[3]
        run_dir = repo_root / ".run"
        run_dir.mkdir(exist_ok=True)
        pgid_file = run_dir / "current.pgid"

        # Proces-lider odpala WŁASNE dziecko (sleep) w tle i czeka na nie — panic.sh
        # musi zabić oboje.
        parent = subprocess.Popen(
            ["bash", "-c", "sleep 60 & echo $!; wait"],
            start_new_session=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            pgid = os.getpgid(parent.pid)
            pgid_file.write_text(str(pgid))
            child_pid = int(parent.stdout.readline().strip())

            time.sleep(0.3)
            assert _process_alive(parent.pid), "proces-lider nie wystartował"
            assert _process_alive(child_pid), "dziecko nie wystartowało"

            result = subprocess.run(
                ["bash", str(repo_root / "scripts" / "panic.sh")],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, result.stderr

            parent.wait(timeout=5)
            time.sleep(0.2)

            assert not _process_alive(parent.pid), "panic.sh nie zabił procesu-lidera"
            assert not _process_alive(child_pid), (
                "panic.sh zabił tylko lidera — dziecko zostało sierotą (dokładnie ten "
                "błąd, przed którym ma chronić grupowanie procesów)"
            )
            assert not pgid_file.exists(), "panic.sh powinien posprzątać plik PGID"
        finally:
            # Siatka bezpieczeństwa, gdyby asercja padła przed panic.sh — nie zostawiaj
            # sierocego `sleep 60` po nieudanym teście.
            if _process_alive(parent.pid):
                try:
                    os.killpg(os.getpgid(parent.pid), 9)
                except ProcessLookupError:
                    pass
            parent.stdout.close()
            pgid_file.unlink(missing_ok=True)

    def test_refuses_to_kill_own_process_group(self):
        """panic.sh musi odmówić, jeśli plik PGID wskazuje na jego WŁASNĄ grupę procesów."""
        repo_root = Path(__file__).resolve().parents[3]
        run_dir = repo_root / ".run"
        run_dir.mkdir(exist_ok=True)
        pgid_file = run_dir / "current.pgid"

        try:
            # Uruchamiamy panic.sh w NOWEJ grupie i wpisujemy do pliku PGID dokładnie
            # tę grupę — symuluje nieaktualny/uszkodzony plik wskazujący na skrypt
            # zamiast na prawdziwy przebieg do ubicia.
            proc = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f'echo "$(ps -o pgid= -p $$ | tr -d " ")" > "{pgid_file}"; '
                    f'exec bash "{repo_root}/scripts/panic.sh"',
                ],
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _stdout, stderr = proc.communicate(timeout=10)

            assert proc.returncode != 0
            assert "WŁASNĄ grupę" in stderr
        finally:
            pgid_file.unlink(missing_ok=True)
