"""Prompty do kompresji opisów zdarzeń w logu awarii (s02e03)."""

SYSTEM_COMPRESS = """Jesteś technikiem przygotowującym skondensowany log awarii elektrowni do
analizy przyczyny. Dla każdej pozycji wejściowej skróć opis zdarzenia, zachowując przy tym
KONIECZNIE:
- wszystkie identyfikatory podzespołów zapisane WIELKIMI LITERAMI (np. ECCS8, WTANK07,
  STMTURB12) — przepisz je dosłownie, bez zmian ani skracania,
- sedno zdarzenia: co się stało, jaki parametr/próg, jaki skutek lub podjęta akcja.

Usuń zbędne słowa, powtórzenia i formalizmy kancelaryjne. Nie dodawaj informacji, których nie
ma w oryginale. Zwróć wynik dla KAŻDEGO indeksu z wejścia — dokładnie tyle samo pozycji ile
dostałeś, żaden indeks nie może zniknąć."""


def build_compress_user_prompt(entries: list[dict], *, target_tokens_per_entry: int) -> str:
    """
    Buduje prompt użytkownika z listą {index, level, text} do skompresowania.

    `target_tokens_per_entry` to jawny, liczbowy budżet — bez niego model
    "skraca trochę" i zatrzymuje się daleko od realnego limitu (potwierdzone
    empirycznie: kolejne rundy z samym hasłem "skróć mocniej" zeszły z ~1870
    do ~1590 do ~1511 tokenów, wciąż nad twardym limitem 1500). Model i tak
    nie trzyma tego budżetu dokładnie — ostateczną gwarancję daje
    deterministyczne przycięcie w `solution.py::_hard_trim`, nie ten prompt.
    """
    lines = [f"{e['index']}. [{e['level']}] {e['text']}" for e in entries]
    body = "\n".join(lines)
    return (
        f"Skompresuj poniższe zdarzenia z logu awarii do MAKS. {target_tokens_per_entry} "
        "tokenów na wpis (to twardy budżet, nie sugestia — pojedyncze krótkie zdanie, bez "
        f"owijania w bawełnę). Zwróć jeden wpis na każdy indeks wejściowy:\n\n{body}"
    )
