from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import httpx2 as httpx
import pytest
from helpers import response, text_block, tool_use_block

from plai.llm.client import (
    GAVE_UP_MESSAGE,
    REFUSAL_MESSAGE,
    TRUNCATED_MESSAGE,
    AssistantError,
    ChatAssistant,
)


def make_assistant(responses, toolbox=None, max_iterations=5):
    client = MagicMock()
    client.messages.create.side_effect = responses
    toolbox = toolbox or MagicMock(definitions=[{"name": "t"}])
    assistant = ChatAssistant(
        client, toolbox, model="claude-test", max_iterations=max_iterations
    )
    return assistant, client, toolbox


HISTORY = [{"role": "user", "content": "hola"}]


def test_plain_answer_without_tools():
    assistant, client, _ = make_assistant([response("end_turn", text_block("Hola!"))])

    assert assistant.reply("sys", HISTORY) == "Hola!"
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-test"
    assert kwargs["system"] == "sys"
    assert kwargs["output_config"] == {"effort": "low"}
    assert "temperature" not in kwargs


def test_single_tool_call_feeds_result_back_to_model():
    tool_turn = response("tool_use", text_block("Buscando"), tool_use_block("t", {"q": "x"}, "id1"))
    assistant, client, toolbox = make_assistant(
        [tool_turn, response("end_turn", text_block("Está en Netflix"))]
    )
    toolbox.run.return_value = "Netflix"

    assert assistant.reply("sys", HISTORY) == "Está en Netflix"

    toolbox.run.assert_called_once_with("t", {"q": "x"})
    second_call_messages = client.messages.create.call_args_list[1].kwargs["messages"]
    assert second_call_messages[1] == {"role": "assistant", "content": tool_turn.content}
    assert second_call_messages[2] == {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "id1", "content": "Netflix", "is_error": False}
        ],
    }


def test_parallel_tool_calls_answered_in_one_user_message():
    tool_turn = response(
        "tool_use",
        tool_use_block("a", {}, "id1"),
        tool_use_block("b", {}, "id2"),
    )
    assistant, client, toolbox = make_assistant([tool_turn, response("end_turn", text_block("ok"))])
    toolbox.run.side_effect = ["A", "B"]

    assistant.reply("sys", HISTORY)

    results = client.messages.create.call_args_list[1].kwargs["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["id1", "id2"]
    assert [r["content"] for r in results] == ["A", "B"]


def test_failing_tool_is_reported_as_error_not_raised():
    tool_turn = response("tool_use", tool_use_block("t", {}, "id1"))
    assistant, client, toolbox = make_assistant(
        [tool_turn, response("end_turn", text_block("No pude buscarlo"))]
    )
    toolbox.run.side_effect = RuntimeError("boom")

    assert assistant.reply("sys", HISTORY) == "No pude buscarlo"
    result = client.messages.create.call_args_list[1].kwargs["messages"][-1]["content"][0]
    assert result["is_error"] is True


def test_unknown_tool_is_reported_as_error():
    from plai.llm.tools import Toolbox

    tool_turn = response("tool_use", tool_use_block("nope", {}, "id1"))
    assistant, client, _ = make_assistant(
        [tool_turn, response("end_turn", text_block("ok"))], toolbox=Toolbox(MagicMock())
    )

    assistant.reply("sys", HISTORY)
    result = client.messages.create.call_args_list[1].kwargs["messages"][-1]["content"][0]
    assert result["is_error"] is True


def test_iteration_cap_stops_runaway_tool_loops():
    tool_turn = response("tool_use", tool_use_block("t", {}, "id1"))
    assistant, client, toolbox = make_assistant([tool_turn] * 3, max_iterations=3)
    toolbox.run.return_value = "x"

    assert assistant.reply("sys", HISTORY) == GAVE_UP_MESSAGE
    assert client.messages.create.call_count == 3


def test_refusal_returns_friendly_message():
    assistant, _, _ = make_assistant([response("refusal")])
    assert assistant.reply("sys", HISTORY) == REFUSAL_MESSAGE


def test_max_tokens_returns_partial_text_or_notice():
    assistant, _, _ = make_assistant([response("max_tokens", text_block("Parcial"))])
    assert assistant.reply("sys", HISTORY) == "Parcial"

    assistant, _, _ = make_assistant([response("max_tokens")])
    assert assistant.reply("sys", HISTORY) == TRUNCATED_MESSAGE


def _api_error(cls, status):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls(
        "boom", response=httpx.Response(status, request=request), body=None
    )


@pytest.mark.parametrize(
    "error",
    [
        _api_error(anthropic.RateLimitError, 429),
        _api_error(anthropic.InternalServerError, 500),
        anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        ),
    ],
)
def test_api_errors_become_assistant_error(error):
    assistant, _, _ = make_assistant([error])
    with pytest.raises(AssistantError):
        assistant.reply("sys", HISTORY)


def test_tool_definitions_are_valid_strict_schemas():
    from plai.llm.tools import Toolbox

    for tool in Toolbox(MagicMock()).definitions:
        schema = tool["input_schema"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        for prop in schema["properties"].values():
            assert prop["description"]


def test_toolbox_dispatches_to_tmdb():
    from plai.llm.tools import Toolbox

    tmdb = SimpleNamespace(
        where_to_watch=lambda title, kind: f"{kind}:{title}",
        trailer=lambda title: f"trailer:{title}",
        now_playing=lambda: "cartelera",
    )
    toolbox = Toolbox(tmdb)
    assert toolbox.run("where_to_watch_tv_show", {"tv_show_name": "Dark"}) == "tv:Dark"
    assert toolbox.run("where_to_watch_movie", {"movie_name": "Dune"}) == "movie:Dune"
    assert toolbox.run("get_movie_or_show_trailer", {"movie_or_show_name": "X"}) == "trailer:X"
    assert toolbox.run("get_current_movies_in_theatres", {}) == "cartelera"
    with pytest.raises(KeyError):
        toolbox.run("missing", {})
