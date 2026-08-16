"""Testy `langfuse_tool_observation()` — musi nigdy nie przerwać wykonania narzędzia."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.observability.decorators import langfuse_tool_observation


def test_yields_set_output_and_finalizes_observation_with_it():
    observation = MagicMock()
    with patch("langfuse.get_client") as mock_get_client:
        mock_get_client.return_value.start_observation.return_value = observation

        with langfuse_tool_observation("search", input={"query": "test"}) as set_output:
            set_output("wynik wyszukiwania")

    _, kwargs = mock_get_client.return_value.start_observation.call_args
    assert kwargs["as_type"] == "tool"
    assert kwargs["name"] == "search"
    assert kwargs["input"] == {"query": "test"}
    observation.update.assert_called_once_with(output="wynik wyszukiwania")
    observation.end.assert_called_once()


def test_langfuse_start_failure_does_not_raise():
    with patch("langfuse.get_client", side_effect=RuntimeError("langfuse down")):
        with langfuse_tool_observation("search") as set_output:
            set_output("wynik mimo braku telemetrii")
    # brak wyjątku = sukces tego testu


def test_exception_inside_block_still_propagates_not_swallowed():
    import pytest

    with patch("langfuse.get_client") as mock_get_client:
        mock_get_client.return_value.start_observation.return_value = MagicMock()

        with pytest.raises(ValueError, match="narzędzie wybuchło"):
            with langfuse_tool_observation("broken"):
                raise ValueError("narzędzie wybuchło")


def test_finalize_failure_does_not_raise():
    observation = MagicMock()
    observation.update.side_effect = RuntimeError("langfuse update failed")

    with patch("langfuse.get_client") as mock_get_client:
        mock_get_client.return_value.start_observation.return_value = observation

        with langfuse_tool_observation("search") as set_output:
            set_output("wynik")
    # brak wyjątku = sukces tego testu, mimo że observation.update() rzucił
