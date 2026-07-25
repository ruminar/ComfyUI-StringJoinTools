from nodes import (
    OptionalStringJoin3,
    OptionalStringJoin5,
    OptionalStringJoin10,
    RuntimeToggleStringJoin2,
    RuntimeToggleStringJoin3,
    RuntimeToggleStringJoin5,
    RuntimeToggleStringJoin10,
    StringOutput,
)
from runtime_state import RuntimeStateStore, RUNTIME_STATE_STORE


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
