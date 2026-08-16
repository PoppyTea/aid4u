"""
Prompt klasyfikatora fraz — jedyne miejsce w tym zadaniu, gdzie LLM w ogóle bierze
udział (patrz `solution.py`: reguły #1/#4 są w 100% deterministyczne). Rejestrowany
w Langfuse przez `sync_prompt()` (`core/observability/prompts.py`) — treść TUTAJ jest
źródłem prawdy, Langfuse to tylko rejestr do porównywania wersji/kosztu.
"""

from __future__ import annotations

PROMPT_NAME = "s03e01-phrase-classifier"

SYSTEM_CLASSIFY = (
    "Jesteś klasyfikatorem notatek operatora elektrowni. Dla każdej podanej frazy "
    "oceń, czy zgłasza ona PROBLEM/AWARIĘ/BŁĄD sensora lub odczytu (np. 'reading "
    "unstable', 'sensor malfunction', 'leak detected', 'error found', 'requires "
    "attention'). Fraza, która mówi że wszystko jest w porządku/stabilne/normalne, "
    "NIE zgłasza problemu.\n\n"
    "Zwróć WYŁĄCZNIE listę indeksów (liczby całkowite, pozycja frazy na liście "
    "wejściowej licząc od 0) tych fraz, które zgłaszają problem. Nigdy nie zwracaj "
    "treści frazy — tylko numer pozycji. Jeśli żadna fraza nie zgłasza problemu, "
    "zwróć pustą listę."
)


def build_batch_prompt(phrases: list[str]) -> str:
    """Buduje prompt użytkownika dla jednego batcha — frazy numerowane LOKALNIE (od 0)."""
    numbered = "\n".join(f"{i}. {phrase}" for i, phrase in enumerate(phrases))
    return f"Frazy do oceny:\n{numbered}"
