"""
S01E04 — sendit

Wypełnia deklarację transportową SPK (System Przesyłek Konduktorskich)
i wysyła ją jako string w polu answer.declaration.

Zadanie jest w pełni deterministyczne — żadnych wywołań LLM. Wszystkie
wartości pochodzą z treści zadania albo z dokumentacji pobranej do
data/input/s01e04_sendit/ (patrz tamtejszy AGENTS.md).

Nazwa zadania w hubie: sendit
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from core.config import WARSAW_TZ
from core.tasks import BaseTask, task

# ─── Dane przesyłki (treść zadania) ──────────────────────────────────────────

NADAWCA = "450202122"
PUNKT_NADAWCZY = "Gdańsk"
PUNKT_DOCELOWY = "Żarnowiec"
MASA_KG = 2800
OPIS_ZAWARTOSCI = "kasety z paliwem do reaktora"

# Gdańsk – Żarnowiec figuruje wyłącznie na liście tras WYŁĄCZONYCH
# (trasy-wylaczone.png, plik graficzny). Treść zadania każe zignorować
# status "zamknięta" — kod trasy zostaje.
TRASA = "X-01"

# Kategoria A (Strategiczna) obejmuje ogniwa paliwowe, a jako jedyna razem z B
# ma opłatę bazową 0 "pokrywaną przez System" (index.md §9.2) i jest zwolniona
# z opłat (§9.4) — czyli spełnia wymóg zerowego budżetu.
KATEGORIA = "A"
KWOTA = "0 PP"

# Treść zadania: "Nie dodawaj proszę żadnych uwag specjalnych".
UWAGI = "brak"

# ─── Parametry składu (dodatkowe-wagony.md) ──────────────────────────────────

UDZWIG_STANDARDOWY_KG = 1000  # lokomotywa + 2 wagony po 500 kg
POJEMNOSC_WAGONU_KG = 500

# ─── Wzór deklaracji (zalacznik-E.md) ────────────────────────────────────────

_NAGLOWEK = "SYSTEM PRZESYŁEK KONDUKTORSKICH - DEKLARACJA ZAWARTOŚCI"
_SEPARATOR = "-" * 54
_RAMKA = "=" * 54


# ─── Czyste funkcje ──────────────────────────────────────────────────────────


def calculate_wdp(masa_kg: int) -> int:
    """
    Liczba Wagonów Dodatkowych Płatnych (skrót rozwinięty w zalacznik-G.md).

    Skład standardowy wozi 1000 kg. Nadwyżkę rozkłada się na wagony po 500 kg,
    zaokrąglając w górę. Zwolnienie kat. A/B dotyczy *opłaty* za te wagony,
    nie ich liczby — wagony i tak trzeba doczepić, więc pole zostaje niezerowe.
    """
    nadwyzka = masa_kg - UDZWIG_STANDARDOWY_KG
    if nadwyzka <= 0:
        return 0
    return math.ceil(nadwyzka / POJEMNOSC_WAGONU_KG)


def build_declaration(data_nadania: str, wdp: int) -> str:
    """Składa deklarację dokładnie wg wzoru — kolejność pól i separatory są weryfikowane."""
    return "\n".join([
        _NAGLOWEK,
        _RAMKA,
        f"DATA: {data_nadania}",
        f"PUNKT NADAWCZY: {PUNKT_NADAWCZY}",
        _SEPARATOR,
        f"NADAWCA: {NADAWCA}",
        f"PUNKT DOCELOWY: {PUNKT_DOCELOWY}",
        f"TRASA: {TRASA}",
        _SEPARATOR,
        f"KATEGORIA PRZESYŁKI: {KATEGORIA}",
        _SEPARATOR,
        f"OPIS ZAWARTOŚCI (max 200 znaków): {OPIS_ZAWARTOSCI}",
        _SEPARATOR,
        f"DEKLAROWANA MASA (kg): {MASA_KG}",
        _SEPARATOR,
        f"WDP: {wdp}",
        _SEPARATOR,
        f"UWAGI SPECJALNE: {UWAGI}",
        _SEPARATOR,
        f"KWOTA DO ZAPŁATY: {KWOTA}",
        _SEPARATOR,
        "OŚWIADCZAM, ŻE PODANE INFORMACJE SĄ PRAWDZIWE.",
        "BIORĘ NA SIEBIE KONSEKWENCJĘ ZA FAŁSZYWE OŚWIADCZENIE.",
        _RAMKA,
    ])


# ─── Zadanie ─────────────────────────────────────────────────────────────────


@task("s01e04", hub_name="sendit")
class SendItTask(BaseTask):
    """Deklaracja transportowa SPK — bez LLM, wszystko liczone lokalnie."""

    def solve(self, data: Any) -> dict:
        dzis = datetime.now(tz=WARSAW_TZ).strftime("%Y-%m-%d")
        declaration = build_declaration(dzis, calculate_wdp(MASA_KG))
        return {"declaration": declaration}
