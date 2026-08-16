"""
Warstwa LLM (reguły #2/#3) — dedup + podział na frazy + batching + mapowanie indeksów.

Cały cost-optimization tego zadania: klasyfikujemy unikalne FRAZY (~261), nie
pojedyncze pliki (10 000) ani nawet unikalne notatki (~2000) — patrz
`doc/community_notes.md` dla liczb kontrolnych z komentarzy społeczności.
"""

from __future__ import annotations

_BATCH_SIZE = 100  # środek zakresu 50-200 z community_notes.md; 500+ -> timeouty/puste odpowiedzi


def normalise(note: str) -> str:
    """strip → zbicie wewnętrznych białych znaków → casefold, dla stabilnego dedupu."""
    return " ".join(note.split()).casefold()


def split_phrases(note: str) -> list[str]:
    """
    Dzieli notatkę na frazy po przecinkach — NIGDY po spacjach, bo to zniszczyłoby
    zasięg negacji (np. "no leak detected" musi zostać jedną frazą, nie trzema słowami).
    """
    return [p.strip() for p in note.split(",") if p.strip()]


def unique_notes(raw_notes: list[str]) -> dict[str, list[int]]:
    """Poziom 1 dedupu: znormalizowana notatka → lista indeksów (do `raw_notes`), które ją mają."""
    grouped: dict[str, list[int]] = {}
    for idx, note in enumerate(raw_notes):
        grouped.setdefault(normalise(note), []).append(idx)
    return grouped


def unique_phrases(notes: list[str]) -> dict[str, set[str]]:
    """Poziom 2 dedupu: unikalna fraza → zbiór (znormalizowanych) notatek, które ją zawierają."""
    phrase_to_notes: dict[str, set[str]] = {}
    for note in notes:
        for phrase in split_phrases(note):
            phrase_to_notes.setdefault(phrase, set()).add(note)
    return phrase_to_notes


def batches(items: list[str], size: int = _BATCH_SIZE) -> list[list[str]]:
    """Dzieli listę na kolejne kawałki po `size` elementów."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def map_local_indices(local_indices: list[int], batch: list[str]) -> list[str]:
    """
    Mapuje lokalne indeksy (0..len(batch)-1) zwrócone przez model z powrotem na
    treść fraz. Indeks spoza zakresu jest ODRZUCANY z ostrzeżeniem — model, który
    zhalucynuje numer albo zwróci coś innego niż `int`, nie może po cichu skazić
    zbioru anomalii.
    """
    import logfire

    result = []
    for i in local_indices:
        if not isinstance(i, int) or not (0 <= i < len(batch)):
            logfire.warning(f"s03e01: indeks poza zakresem batcha: {i!r} (batch size={len(batch)})")
            continue
        result.append(batch[i])
    return result


def note_says_failure(note: str, is_failure: dict[str, bool]) -> bool:
    """Notatka zgłasza problem, jeśli KTÓRAKOLWIEK jej fraza jest oznaczona jako failure."""
    return any(is_failure.get(phrase, False) for phrase in split_phrases(note))
