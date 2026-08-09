"""
Walidacja pobranej treści — niezależna od `HubClient`, używalna przy każdym
pobieraniu z sieci w tym projekcie (hub, `4th-devs`, dokumentacja, cokolwiek).

Powód istnienia: hub.ag3nts.org potrafi zwrócić HTTP 200 ze stroną błędu (text/html)
zamiast prawdziwego 404 dla nieistniejącego zasobu binarnego — potwierdzone empirycznie
przy przygotowaniach do s02e05 (zły URL do mapy zwrócił 200 + treść HTML zamiast
image/png). Sam status HTTP nic nie gwarantuje; trzeba zweryfikować samą treść, ZANIM
zostanie potraktowana jak prawdziwy plik binarny (np. zapisana na dysk i wczytana przez
Pillow — tam błąd formatu ujawniłby się dopiero przy próbie dekodowania, dalej od
źródła problemu).

Sprawdzanie po magic bytes, nie po nagłówku Content-Type — nagłówek też bywa
niewiarygodny (deklarowany typ i faktyczna treść mogą się rozjechać), magic bytes są
prawdą o samej treści.
"""

from __future__ import annotations

_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    # PK\x03\x04 = normalny lokalny nagłówek pliku; PK\x05\x06 = "end of central
    # directory" — sygnatura PUSTEGO archiwum ZIP (0 plików w środku). Bez drugiej
    # sygnatury `expect_binary(..., "zip")` odrzucałby prawidłowy, tylko pusty ZIP.
    "zip": (b"PK\x03\x04", b"PK\x05\x06"),
    "gif": (b"GIF8",),
    "jpeg": (b"\xff\xd8\xff",),
    "pdf": (b"%PDF-",),
}

_HTML_MARKERS = (b"<!doctype html", b"<html")


class UnexpectedContentError(Exception):
    """Pobrana treść nie pasuje do oczekiwanego formatu — mimo HTTP 200."""


def expect_binary(content: bytes, kind: str, *, source: str = "") -> bytes:
    """
    Sprawdza magic bytes treści względem znanego formatu binarnego (`kind`, np. "png",
    "zip" — patrz `_MAGIC_BYTES`). Rzuca `UnexpectedContentError` z fragmentem treści w
    diagnostyce, jeśli nie pasuje; jeśli fragment wygląda na HTML, dopisuje podpowiedź
    "soft-404" (typowa przyczyna tego konkretnego niedopasowania w tym projekcie).

    `source` to opcjonalny opis pochodzenia (np. URL) do komunikatu błędu.
    Zwraca `content` niezmienione przy sukcesie — wygodne do łańcuchowania:
    `path.write_bytes(expect_binary(hub.get_public(...), "png"))`.
    """
    signatures = _MAGIC_BYTES.get(kind)
    if signatures is None:
        raise ValueError(f"Nieznany format '{kind}' — dodaj magic bytes do _MAGIC_BYTES.")

    if not any(content.startswith(sig) for sig in signatures):
        looks_like_html = content.lstrip()[:15].lower().startswith(_HTML_MARKERS)
        hint = " (treść wygląda na stronę HTML — prawdopodobnie soft-404)" if looks_like_html else ""
        where = f" z {source}" if source else ""
        raise UnexpectedContentError(
            f"Oczekiwano formatu '{kind}'{where}, ale magic bytes nie pasują{hint}. "
            f"Pierwsze 100 bajtów: {content[:100]!r}"
        )
    return content


def expect_not_html(content: bytes, *, source: str = "") -> bytes:
    """
    Dla formatów bez magic bytes, gdzie oczekiwana treść z definicji NIE powinna być
    HTML-em (np. spodziewany `.csv`/`.log` zwrócony jako strona błędu zamiast danych).
    Nie używać dla zasobów, które legalnie SĄ HTML-em (np. `drone.html`) — tam ta
    funkcja zawsze by przechodziła bez sensu.
    """
    if content.lstrip()[:15].lower().startswith(_HTML_MARKERS):
        where = f" z {source}" if source else ""
        raise UnexpectedContentError(
            f"Oczekiwano treści nie-HTML{where}, dostano stronę HTML (prawdopodobnie "
            f"soft-404). Pierwsze 200 bajtów: {content[:200]!r}"
        )
    return content
