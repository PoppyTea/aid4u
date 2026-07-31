from __future__ import annotations

import pytest

from tasks.s01e03_proxy.packages_data import PackageStore, ZARNOWIEC_CODE
from tasks.s01e03_proxy.tools import TOOLS, make_tool_executor


def test_tools_list_has_expected_names():
    assert [t.name for t in TOOLS] == ["check_package", "redirect_package"]


def test_executor_check_package_known():
    executor = make_tool_executor(PackageStore())

    result = executor("check_package", {"package_id": "PKG10172494"})

    assert "rdzeń reaktora" in result
    assert "Gdańsk" in result


def test_executor_check_package_unknown():
    executor = make_tool_executor(PackageStore())

    result = executor("check_package", {"package_id": "NOPE"})

    assert "Nie znaleziono" in result


def test_executor_redirect_package_applies_safety_net():
    store = PackageStore()
    executor = make_tool_executor(store)

    result = executor("redirect_package", {"package_id": "PKG10172494", "destination": "Kraków"})

    assert "Kraków" in result
    assert store.get("PKG10172494").destination == ZARNOWIEC_CODE


def test_executor_unknown_tool_raises():
    executor = make_tool_executor(PackageStore())

    with pytest.raises(ValueError, match="Nieznane narzędzie"):
        executor("delete_everything", {})
