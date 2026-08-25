import pytest
from pathlib import Path
from core.hub.cache import LocalCache


@pytest.fixture
def temp_cache_dir(tmp_path, monkeypatch):
    """Fixture do patchowania _CACHE_ROOT."""
    cache_root = tmp_path / ".cache"
    monkeypatch.setattr("core.hub.cache._CACHE_ROOT", cache_root)
    return cache_root


def test_init_creates_directory(temp_cache_dir):
    """Test inicjalizacji cache'a z utworzeniem katalogu."""
    LocalCache(subdir="test_dir")
    expected_dir = temp_cache_dir / "test_dir"
    assert expected_dir.exists()
    assert expected_dir.is_dir()


def test_get_and_set(temp_cache_dir):
    """Testowanie metod get i set."""
    cache = LocalCache()
    key = "test_key"
    data = b"test_data"

    # Przed zapisem powinno być None
    assert cache.get(key) is None

    # Zapis
    cache.set(key, data)

    # Po zapisie powinno zwrócić dane
    cached_data = cache.get(key)
    assert cached_data == data


def test_get_or_fetch(temp_cache_dir):
    """Testowanie metody get_or_fetch."""
    cache = LocalCache()
    key = "fetch_key"
    data = b"fetched_data"

    fetch_calls = 0

    def mock_fetch():
        nonlocal fetch_calls
        fetch_calls += 1
        return data

    # Pierwsze wywołanie - cache miss, powinno wywołać fetch_fn
    result1 = cache.get_or_fetch(key, mock_fetch)
    assert result1 == data
    assert fetch_calls == 1

    # Drugie wywołanie - cache hit, nie powinno wywoływać fetch_fn
    result2 = cache.get_or_fetch(key, mock_fetch)
    assert result2 == data
    assert fetch_calls == 1


def test_get_or_fetch_tracks_last_key(temp_cache_dir):
    """
    last_key musi wskazywać ostatnio użyty klucz — używane przez BaseTask do nazwania pliku w
    data/run-history/.
    """
    cache = LocalCache()
    assert cache.last_key is None

    cache.get_or_fetch("people.csv", lambda: b"dane")
    assert cache.last_key == "people.csv"

    cache.get_or_fetch("other.png", lambda: b"inne dane")
    assert cache.last_key == "other.png"


def test_invalidate(temp_cache_dir):
    """Testowanie unieważniania klucza."""
    cache = LocalCache()
    key = "invalidate_key"
    data = b"data_to_invalidate"

    # Zapisz dane do cache
    cache.set(key, data)
    assert cache.get(key) == data

    # Unieważnij klucz
    cache.invalidate(key)

    # Powinno być usunięte z cache
    assert cache.get(key) is None

    # Unieważnianie klucza, który nie istnieje, nie powinno rzucać błędu
    try:
        cache.invalidate(key)
    except Exception as e:
        pytest.fail(f"Invalidate na usuniętym kluczu rzuciło błąd: {e}")
