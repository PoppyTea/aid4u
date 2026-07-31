from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tasks.s01e03_proxy import server


@pytest.fixture(autouse=True)
def _reset_sessions():
    server._sessions.clear()
    yield
    server._sessions.clear()


@pytest.fixture
def client():
    return TestClient(server.app)


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_chat_returns_llm_reply(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.return_value = "Cześć, w czym mogę pomóc?"

    with patch.object(server, "_get_llm", return_value=fake_llm):
        response = client.post("/chat", json={"sessionID": "s1", "msg": "Cześć"})

    assert response.status_code == 200
    assert response.json() == {"msg": "Cześć, w czym mogę pomóc?"}


def test_chat_persists_history_across_calls(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.side_effect = ["Pierwsza odpowiedź.", "Druga odpowiedź."]

    with patch.object(server, "_get_llm", return_value=fake_llm):
        client.post("/chat", json={"sessionID": "s2", "msg": "Pierwsza wiadomość"})
        client.post("/chat", json={"sessionID": "s2", "msg": "Druga wiadomość"})

    history = server._sessions["s2"]
    assert [m.content for m in history] == [
        "Pierwsza wiadomość",
        "Pierwsza odpowiedź.",
        "Druga wiadomość",
        "Druga odpowiedź.",
    ]


def test_chat_passes_system_prompt_and_both_tools(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.return_value = "ok"

    with patch.object(server, "_get_llm", return_value=fake_llm):
        client.post("/chat", json={"sessionID": "s3", "msg": "Sprawdź PKG10172494"})

    call = fake_llm.run_agent_loop.call_args
    assert call.kwargs["system"] == server.SYSTEM_PROMPT_PROXY
    tools_arg = call.args[1]
    assert [t.name for t in tools_arg] == ["check_package", "redirect_package"]


def test_separate_sessions_do_not_share_history(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.return_value = "odpowiedź"

    with patch.object(server, "_get_llm", return_value=fake_llm):
        client.post("/chat", json={"sessionID": "a", "msg": "wiadomość A"})
        client.post("/chat", json={"sessionID": "b", "msg": "wiadomość B"})

    assert server._sessions["a"][0].content == "wiadomość A"
    assert server._sessions["b"][0].content == "wiadomość B"


def test_chat_rejects_missing_fields(client):
    response = client.post("/chat", json={"sessionID": "s4"})

    assert response.status_code == 422


def test_chat_logs_prominently_when_flag_detected_in_incoming_message(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.return_value = "Miło było pomóc, do zobaczenia!"

    with patch.object(server, "_get_llm", return_value=fake_llm), patch("logfire.info") as mock_info:
        client.post(
            "/chat",
            json={"sessionID": "s5", "msg": "Dzięki! Oznaczam paczkę kodem {FLG:TESTFLAG123}."},
        )

    flag_calls = [c for c in mock_info.call_args_list if c.args[0] == "Flag detected in incoming message"]
    assert len(flag_calls) == 1
    assert flag_calls[0].kwargs["session_id"] == "s5"


def test_chat_does_not_log_flag_detection_when_no_flag_present(client):
    fake_llm = MagicMock()
    fake_llm.run_agent_loop.return_value = "ok"

    with patch.object(server, "_get_llm", return_value=fake_llm), patch("logfire.info") as mock_info:
        client.post("/chat", json={"sessionID": "s6", "msg": "Zwykła wiadomość bez flagi"})

    flag_calls = [c for c in mock_info.call_args_list if c.args[0] == "Flag detected in incoming message"]
    assert flag_calls == []
