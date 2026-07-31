from __future__ import annotations

from unittest.mock import MagicMock

from core.llm.classify import ClassificationResult, classify


def test_classify_returns_the_llm_structured_result():
    llm = MagicMock()
    llm.structured.return_value = ClassificationResult(
        matches=True, reasoning="wspomniano rdzeń reaktora"
    )

    result = classify(
        llm,
        "Chodzi o paczkę z rdzeniem reaktora.",
        category_description="paczka zawiera niebezpieczny ładunek",
    )

    assert result.matches is True
    assert result.reasoning == "wspomniano rdzeń reaktora"


def test_classify_returns_false_for_non_matching_content():
    llm = MagicMock()
    llm.structured.return_value = ClassificationResult(matches=False, reasoning="zwykła przesyłka")

    result = classify(
        llm,
        "Standardowa paczka z częściami zamiennymi.",
        category_description="paczka zawiera niebezpieczny ładunek",
    )

    assert result.matches is False


def test_classify_embeds_category_and_text_in_the_prompt():
    llm = MagicMock()
    llm.structured.return_value = ClassificationResult(matches=False, reasoning="ok")

    classify(
        llm,
        "Chodzi o paczkę z rdzeniem reaktora.",
        category_description="paczka zawiera niebezpieczny ładunek",
    )

    call_args = llm.structured.call_args
    assert call_args.args[1] is ClassificationResult
    prompt = call_args.args[0][0].content
    assert "niebezpieczny ładunek" in prompt
    assert "rdzeniem reaktora" in prompt


def test_classify_uses_default_system_prompt_when_none_given():
    llm = MagicMock()
    llm.structured.return_value = ClassificationResult(matches=False, reasoning="ok")

    classify(llm, "tekst", category_description="kategoria")

    call_kwargs = llm.structured.call_args.kwargs
    assert call_kwargs["system"]  # non-empty default


def test_classify_passes_through_custom_system_prompt():
    llm = MagicMock()
    llm.structured.return_value = ClassificationResult(matches=False, reasoning="ok")

    classify(llm, "tekst", category_description="kategoria", system="Bądź surowy.")

    assert llm.structured.call_args.kwargs["system"] == "Bądź surowy."
