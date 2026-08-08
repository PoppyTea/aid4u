"""Testy core/runtime/killswitch.py — Warstwy 1/2 jednostkowo, Warstwa 0 realnie."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from core.runtime import killswitch


@pytest.fixture(autouse=True)
def _clean_run_dir():
    """Każdy test startuje i kończy bez .run/STOP ani aktywnego budżetu."""
    killswitch.end_run()
    yield
    killswitch.end_run()


class TestCheckAbort:
    """Warstwa 1 — plik-wartownik .run/STOP."""

    def test_passes_when_no_stop_file_and_no_budget(self):
        killswitch.check_abort()  # nie powinno rzucić

    def test_raises_after_request_stop(self):
        killswitch.request_stop()

        with pytest.raises(killswitch.AbortRun, match="STOP"):
            killswitch.check_abort()

    def test_end_run_clears_stop_file(self):
        killswitch.request_stop()
        killswitch.end_run()

        killswitch.check_abort()  # nie powinno już rzucić


class TestRunBudget:
    """Warstwa 2 (per-run) — budżet wall-clock."""

    def test_no_limit_never_raises(self):
        budget = killswitch.RunBudget(max_seconds=None)
        budget.check_time()  # nie powinno rzucić niezależnie od czasu

    def test_raises_after_max_seconds_elapsed(self):
        budget = killswitch.RunBudget(max_seconds=0.01)
        time.sleep(0.05)

        with pytest.raises(killswitch.AbortRun, match="budżet czasu"):
            budget.check_time()

    def test_does_not_raise_before_max_seconds(self):
        budget = killswitch.RunBudget(max_seconds=10.0)
        budget.check_time()  # nie powinno rzucić — dopiero się zaczęło


class TestStartRunActivatesBudget:
    """start_run(max_seconds=...) musi być widoczny przez check_abort(), nie tylko RunBudget bezpośrednio."""

    def test_check_abort_raises_once_budget_exceeded(self):
        killswitch.start_run(max_seconds=0.01)
        time.sleep(0.05)

        with pytest.raises(killswitch.AbortRun):
            killswitch.check_abort()

    def test_check_abort_silent_without_max_seconds(self):
        killswitch.start_run(max_seconds=None)
        killswitch.check_abort()  # nie powinno rzucić


class TestTruncateToolResult:
    """Warstwa 2 (per-call) — obcinanie wyniku narzędzia, bez przerywania przebiegu."""

    def test_short_result_unchanged(self):
        assert killswitch.truncate_tool_result("ok", max_bytes=100) == "ok"

    def test_long_result_truncated_and_marked(self):
        long_result = "x" * 1000
        truncated = killswitch.truncate_tool_result(long_result, max_bytes=100)

        assert len(truncated.encode("utf-8")) < 1000
        assert "OBCIĘTO" in truncated
        assert "1000" in truncated  # oryginalny rozmiar w komunikacie


def _process_alive(pid: int) -> bool:
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
    """

    def test_kills_parent_and_child(self):
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
            pgid_file.unlink(missing_ok=True)
