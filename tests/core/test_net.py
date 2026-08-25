"""Testy core/net.py — walidacja treści niezależna od HubClient, bez sieci."""

from __future__ import annotations

import pytest

from core.net import UnexpectedContentError, expect_binary, expect_not_html


class TestExpectBinary:
    """expect_binary() — sprawdzenie magic bytes względem znanego formatu."""

    def test_valid_png_passes_and_returns_content(self):
        """Poprawny nagłówek PNG przechodzi i treść wraca niezmieniona."""
        content = b"\x89PNG\r\n\x1a\n" + b"rest of png data"
        assert expect_binary(content, "png") == content

    def test_valid_zip_passes(self):
        """Normalny (niepusty) ZIP z lokalnym nagłówkiem pliku przechodzi."""
        content = b"PK\x03\x04" + b"rest of zip data"
        assert expect_binary(content, "zip") == content

    def test_empty_zip_archive_passes(self):
        """
        Pusty ZIP (sama sygnatura 'end of central directory') też jest poprawnym ZIP-em, nie ma
        zostać odrzucony.
        """
        content = b"PK\x05\x06" + b"\x00" * 18  # standardowy pusty EOCD record
        assert expect_binary(content, "zip") == content

    def test_wrong_magic_bytes_raises(self):
        """Treść bez pasującej sygnatury rzuca UnexpectedContentError."""
        with pytest.raises(UnexpectedContentError, match="magic bytes"):
            expect_binary(b"not a png at all", "png")

    def test_soft_404_html_gets_specific_hint(self):
        """
        Strona HTML zamiast oczekiwanego binarnego pliku dostaje podpowiedź 'soft-404' w
        komunikacie błędu.
        """
        # Dokładnie ten przypadek, który spowodował dodanie tego modułu: hub zwraca
        # 200 + HTML zamiast oczekiwanego pliku binarnego.
        html_error_page = b"<html><body>404 not found</body></html>"

        with pytest.raises(UnexpectedContentError, match="soft-404"):
            expect_binary(html_error_page, "png")

    def test_unknown_kind_raises_value_error(self):
        """Nieznany format (brak w _MAGIC_BYTES) rzuca ValueError, nie cichy fałszywy negatyw."""
        with pytest.raises(ValueError, match="Nieznany format"):
            expect_binary(b"anything", "not-a-real-format")

    def test_source_included_in_error_message(self):
        """Opcjonalny parametr source trafia do treści komunikatu błędu, ułatwiając debugowanie."""
        with pytest.raises(UnexpectedContentError, match="https://example.com/file.png"):
            expect_binary(b"bad", "png", source="https://example.com/file.png")


class TestExpectNotHtml:
    """expect_not_html() — dla formatów, które NIE powinny być stroną HTML."""

    def test_plain_text_passes(self):
        """Zwykły tekst (np. CSV) przechodzi bez zmian."""
        content = b"col1,col2\nval1,val2\n"
        assert expect_not_html(content) == content

    def test_binary_zip_like_content_passes(self):
        """Treść binarna niezaczynająca się od znaczników HTML też przechodzi."""
        content = b"PK\x03\x04binary zip bytes"
        assert expect_not_html(content) == content

    def test_html_content_raises(self):
        """Treść zaczynająca się od <html> jest odrzucana z podpowiedzią 'soft-404'."""
        with pytest.raises(UnexpectedContentError, match="soft-404"):
            expect_not_html(b"<html><body>error page</body></html>")

    def test_doctype_html_raises(self):
        """Treść z <!DOCTYPE html> jest równie odrzucana jak goły <html>."""
        with pytest.raises(UnexpectedContentError):
            expect_not_html(b"<!DOCTYPE html><html></html>")

    def test_leading_whitespace_before_html_still_detected(self):
        """Białe znaki przed <html> nie omijają detekcji — content.lstrip() radzi sobie z tym."""
        with pytest.raises(UnexpectedContentError):
            expect_not_html(b"   \n  <html>")
