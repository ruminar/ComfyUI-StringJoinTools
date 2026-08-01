import math

import pytest

from nodes import (
    OptionalStringJoin2,
    OptionalStringJoin3,
    OptionalStringJoin5,
    OptionalStringJoin10,
    ToggleStringJoin2,
    ToggleStringJoin3,
    ToggleStringJoin5,
    ToggleStringJoin10,
    RuntimeToggleStringJoin2,
    RuntimeToggleStringJoin3,
    RuntimeToggleStringJoin5,
    RuntimeToggleStringJoin10,
    RuntimeTextInput,
    StringOutput,
    decode_separator,
)
from runtime_state import (
    MAX_RUNTIME_TEXT_BYTES,
    RUNTIME_STATE_STORE,
    RUNTIME_TEXT_STATE_STORE,
    RuntimeStateStore,
    RuntimeTextStateStore,
    StaleRuntimeTextUpdate,
)


def test_optional_join_ignores_missing_and_empty():
    assert OptionalStringJoin5().join_strings(
        ", ",
        text_1="AAA",
        text_2="",
        text_5="BBB",
    ) == ("AAA, BBB",)


def test_optional_join_all_missing_returns_empty():
    assert OptionalStringJoin10().join_strings(", ") == ("",)


def test_optional_join_preserves_whitespace_and_newlines():
    assert OptionalStringJoin3().join_strings(
        "|",
        text_1=" ",
        text_2="A\nB",
    ) == (" |A\nB",)


def test_separator_escape_sequences_are_safely_decoded():
    assert decode_separator(r"\n") == "\n"
    assert decode_separator(r"\r\n") == "\r\n"
    assert decode_separator(r"\t") == "\t"
    assert decode_separator(r"\\") == "\\"
    assert decode_separator(r"\\n") == r"\n"
    assert decode_separator(r"\u3042") == r"\u3042"
    assert decode_separator(r"\x41") == r"\x41"


def test_optional_variants_use_decoded_separators():
    variants = (
        OptionalStringJoin2,
        OptionalStringJoin3,
        OptionalStringJoin5,
        OptionalStringJoin10,
    )
    for node_class in variants:
        assert node_class().join_strings(
            r"\n",
            text_1="AAA",
            text_2="BBB",
        ) == ("AAA\nBBB",)


def test_runtime_fallback_multiple():
    result = RuntimeToggleStringJoin10().join_strings(
        separator=",",
        mode="multiple",
        enabled_mask=(1 << 0) | (1 << 2),
        selected_index=2,
        state_key="fallback-test",
        unique_id="1",
        text_1="AAA",
        text_2="BBB",
        text_3="CCC",
    )
    assert result == ("AAA,CCC",)


def test_toggle_variants_capture_settings_without_live_state_inputs():
    variants = (
        (ToggleStringJoin2, 2),
        (ToggleStringJoin3, 3),
        (ToggleStringJoin5, 5),
        (ToggleStringJoin10, 10),
    )

    for node_class, input_count in variants:
        input_types = node_class.INPUT_TYPES()
        assert "state_key" not in input_types["required"]
        assert "hidden" not in input_types
        assert list(input_types["optional"]) == [
            f"text_{index}" for index in range(1, input_count + 1)
        ]


def test_toggle_variants_use_queued_mask_and_mode():
    variants = (
        ToggleStringJoin2,
        ToggleStringJoin3,
        ToggleStringJoin5,
        ToggleStringJoin10,
    )

    for node_class in variants:
        result = node_class().join_strings(
            separator=r"\n",
            mode="multiple",
            enabled_mask=1 << 1,
            selected_index=1,
            text_1="AAA",
            text_2="BBB",
        )
        assert result == ("BBB",)

        result = node_class().join_strings(
            separator=",",
            mode="single",
            enabled_mask=(1 << 0) | (1 << 1),
            selected_index=0,
            text_1="AAA",
            text_2="BBB",
        )
        assert result == ("AAA",)


def test_toggle_cache_token_tracks_queued_settings():
    enabled_token = ToggleStringJoin2.IS_CHANGED(
        separator=r"\n",
        mode="multiple",
        enabled_mask=1,
        selected_index=0,
    )
    disabled_token = ToggleStringJoin2.IS_CHANGED(
        separator=r"\n",
        mode="multiple",
        enabled_mask=0,
        selected_index=-1,
    )
    assert enabled_token != disabled_token


def test_runtime_variants_use_decoded_separators():
    variants = (
        RuntimeToggleStringJoin2,
        RuntimeToggleStringJoin3,
        RuntimeToggleStringJoin5,
        RuntimeToggleStringJoin10,
    )
    for node_class in variants:
        key = f"escaped-separator-{node_class.INPUT_COUNT}"
        RUNTIME_STATE_STORE.clear(key)
        assert node_class().join_strings(
            separator=r"\t",
            mode="multiple",
            enabled_mask=3,
            selected_index=1,
            state_key=key,
            text_1="AAA",
            text_2="BBB",
        ) == ("AAA\tBBB",)


def test_runtime_cache_token_includes_decoded_separator():
    key = "separator-cache-token"
    RUNTIME_STATE_STORE.clear(key)
    RUNTIME_STATE_STORE.update(
        state_key=key,
        mode="multiple",
        enabled_mask=3,
        selected_index=1,
        input_count=2,
    )
    newline_token = RuntimeToggleStringJoin2.IS_CHANGED(
        separator=r"\n",
        state_key=key,
    )
    tab_token = RuntimeToggleStringJoin2.IS_CHANGED(
        separator=r"\t",
        state_key=key,
    )
    assert newline_token != tab_token
    RUNTIME_STATE_STORE.clear(key)


def test_runtime_variants_have_expected_inputs_and_masks():
    variants = (
        (RuntimeToggleStringJoin2, 2),
        (RuntimeToggleStringJoin3, 3),
        (RuntimeToggleStringJoin5, 5),
        (RuntimeToggleStringJoin10, 10),
    )

    for node_class, input_count in variants:
        input_types = node_class.INPUT_TYPES()
        assert list(input_types["optional"]) == [
            f"text_{index}" for index in range(1, input_count + 1)
        ]
        assert input_types["required"]["enabled_mask"][1]["max"] == (
            1 << input_count
        ) - 1
        assert input_types["required"]["selected_index"][1]["max"] == (
            input_count - 1
        )


def test_runtime_variants_join_their_last_input():
    variants = (
        (RuntimeToggleStringJoin2, 2),
        (RuntimeToggleStringJoin3, 3),
        (RuntimeToggleStringJoin5, 5),
        (RuntimeToggleStringJoin10, 10),
    )

    for node_class, input_count in variants:
        key = f"variant-{input_count}"
        RUNTIME_STATE_STORE.clear(key)
        result = node_class().join_strings(
            separator="|",
            mode="multiple",
            enabled_mask=1 << (input_count - 1),
            selected_index=input_count - 1,
            state_key=key,
            unique_id=str(input_count),
            **{
                f"text_{index}": f"value-{index}"
                for index in range(1, input_count + 1)
            },
        )
        assert result == (f"value-{input_count}",)


def test_runtime_live_state_overrides_queued_fallback():
    key = "live-override-test"
    RUNTIME_STATE_STORE.clear(key)
    RUNTIME_STATE_STORE.update(
        state_key=key,
        mode="multiple",
        enabled_mask=1 << 1,
        selected_index=1,
        input_count=10,
    )
    result = RuntimeToggleStringJoin10().join_strings(
        separator=",",
        mode="multiple",
        enabled_mask=(1 << 0) | (1 << 1),
        selected_index=0,
        state_key=key,
        unique_id="2",
        text_1="AAA",
        text_2="BBB",
    )
    assert result == ("BBB",)
    RUNTIME_STATE_STORE.clear(key)


def test_runtime_single_mode_zero_or_one():
    key = "single-test"
    RUNTIME_STATE_STORE.clear(key)
    RUNTIME_STATE_STORE.update(
        state_key=key,
        mode="single",
        enabled_mask=(1 << 1) | (1 << 4),
        selected_index=4,
        input_count=10,
    )
    result = RuntimeToggleStringJoin10().join_strings(
        separator=",",
        mode="multiple",
        enabled_mask=1023,
        selected_index=0,
        state_key=key,
        unique_id="3",
        text_2="BBB",
        text_5="EEE",
    )
    assert result == ("EEE",)

    RUNTIME_STATE_STORE.update(
        state_key=key,
        mode="single",
        enabled_mask=0,
        selected_index=-1,
        input_count=10,
    )
    result = RuntimeToggleStringJoin10().join_strings(
        separator=",",
        mode="multiple",
        enabled_mask=1023,
        selected_index=0,
        state_key=key,
        unique_id="3",
        text_2="BBB",
        text_5="EEE",
    )
    assert result == ("",)
    RUNTIME_STATE_STORE.clear(key)


def test_revision_changes_only_when_state_changes():
    store = RuntimeStateStore()
    first = store.update(
        state_key="revision",
        mode="multiple",
        enabled_mask=3,
        selected_index=1,
        input_count=10,
    )
    same = store.update(
        state_key="revision",
        mode="multiple",
        enabled_mask=3,
        selected_index=1,
        input_count=10,
    )
    changed = store.update(
        state_key="revision",
        mode="multiple",
        enabled_mask=1,
        selected_index=0,
        input_count=10,
    )
    assert first.revision == 1
    assert same.revision == 1
    assert changed.revision == 2


def test_string_output_empty_and_passthrough():
    result = StringOutput().show_text("")
    assert result["result"] == ("",)
    assert result["ui"]["text"] == [""]
    assert result["ui"]["length"] == [0]


def test_string_output_accepts_unconnected_text_input():
    input_types = StringOutput.INPUT_TYPES()
    assert "required" not in input_types
    assert "text" in input_types["optional"]

    result = StringOutput().show_text()
    assert result["result"] == ("",)
    assert result["ui"]["text"] == [""]
    assert result["ui"]["length"] == [0]


def test_runtime_text_falls_back_only_when_live_state_is_missing():
    key = "runtime-text-fallback"
    RUNTIME_TEXT_STATE_STORE.clear(key)
    node = RuntimeTextInput()

    assert node.get_text(
        text="  queued\ntext\\n  ",
        state_key=key,
        unique_id="fallback",
    ) == ("  queued\ntext\\n  ",)

    RUNTIME_TEXT_STATE_STORE.update(
        state_key=key,
        text="",
        client_id="browser-a",
        client_sequence=1,
    )
    assert node.get_text(
        text="queued value",
        state_key=key,
        unique_id="fallback",
    ) == ("",)
    RUNTIME_TEXT_STATE_STORE.clear(key)


def test_runtime_text_live_state_preserves_text_exactly():
    key = "runtime-text-exact"
    RUNTIME_TEXT_STATE_STORE.clear(key)
    live_text = " 前後空白 \r\n日本語 😀 \\\\n\t"
    RUNTIME_TEXT_STATE_STORE.update(
        state_key=key,
        text=live_text,
        client_id="browser-a",
        client_sequence=1,
    )
    assert RuntimeTextInput().get_text(
        text="fallback",
        state_key=key,
    ) == (live_text,)
    RUNTIME_TEXT_STATE_STORE.clear(key)


def test_runtime_text_always_invalidates_comfy_cache():
    assert math.isnan(RuntimeTextInput.IS_CHANGED())
    assert math.isnan(RuntimeTextInput.IS_CHANGED(text="same"))


def test_runtime_text_store_revisions_and_session_ordering():
    store = RuntimeTextStateStore()
    first = store.update(
        state_key="ordered",
        text="A",
        client_id="browser-a",
        client_sequence=1,
    )
    same = store.update(
        state_key="ordered",
        text="A",
        client_id="browser-a",
        client_sequence=2,
    )
    changed = store.update(
        state_key="ordered",
        text="B",
        client_id="browser-a",
        client_sequence=3,
    )
    assert first.revision == 1
    assert same.revision == 1
    assert changed.revision == 2
    assert "client_id" not in changed.to_dict()
    assert "client_sequence" not in changed.to_dict()

    with pytest.raises(StaleRuntimeTextUpdate):
        store.update(
            state_key="ordered",
            text="stale",
            client_id="browser-a",
            client_sequence=2,
        )

    reloaded = store.update(
        state_key="ordered",
        text="after reload",
        client_id="browser-b",
        client_sequence=1,
    )
    assert reloaded.text == "after reload"
    assert reloaded.revision == 3


def test_runtime_text_store_validates_type_and_utf8_size():
    store = RuntimeTextStateStore()
    with pytest.raises(TypeError):
        store.update(
            state_key="invalid",
            text=None,
            client_id="browser",
            client_sequence=1,
        )
    with pytest.raises(ValueError):
        store.update(
            state_key="too-large",
            text="あ" * (MAX_RUNTIME_TEXT_BYTES // 3 + 1),
            client_id="browser",
            client_sequence=1,
        )


def test_runtime_text_input_definition_is_multiline_and_serialized():
    input_types = RuntimeTextInput.INPUT_TYPES()
    assert input_types["required"]["text"][1]["multiline"] is True
    assert input_types["required"]["text"][1]["dynamicPrompts"] is False
    assert "state_key" in input_types["required"]
    assert "revision" not in input_types["required"]
    assert input_types["hidden"]["unique_id"] == "UNIQUE_ID"
