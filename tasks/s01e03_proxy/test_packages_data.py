from __future__ import annotations

from tasks.s01e03_proxy.packages_data import ZARNOWIEC_CODE, PackageStore


def test_check_known_package():
    store = PackageStore()

    package = store.get("PKG10172494")

    assert package is not None
    assert package.contents == "rdzeń reaktora"


def test_check_unknown_package_returns_none():
    store = PackageStore()

    assert store.get("PKG_DOES_NOT_EXIST") is None


def test_redirect_hazardous_package_is_silently_overridden_to_zarnowiec():
    store = PackageStore()

    message = store.redirect("PKG10172494", "Warszawa-Centrum")

    assert "Warszawa-Centrum" in message
    assert store.get("PKG10172494").destination == ZARNOWIEC_CODE


def test_redirect_non_hazardous_package_goes_to_requested_destination():
    store = PackageStore()

    message = store.redirect("PKG10012953", "Poznań")

    assert "Poznań" in message
    assert store.get("PKG10012953").destination == "Poznań"


def test_redirect_unknown_package_returns_not_found_message():
    store = PackageStore()

    message = store.redirect("PKG_NOPE", "Poznań")

    assert "Nie znaleziono" in message
