from __future__ import annotations

from typing import Any

try:
    from .runtime_state import (
        RUNTIME_STATE_STORE,
        RUNTIME_TEXT_STATE_STORE,
        VALID_MODES,
    )
except ImportError:
    from runtime_state import (
        RUNTIME_STATE_STORE,
        RUNTIME_TEXT_STATE_STORE,
        VALID_MODES,
    )


CATEGORY = "String Join Tools"
VERSION = "0.2.0"
BUILD = "v2"


def _valid_non_empty_strings(values: list[Any]) -> list[str]:
    return [value for value in values if isinstance(value, str) and value != ""]


def decode_separator(value: str) -> str:
    """Decode only the separator escape sequences supported by this package."""
    if not isinstance(value, str):
        return ""

    decoded: list[str] = []
    index = 0
    while index < len(value):
        if value.startswith("\\r\\n", index):
            decoded.append("\r\n")
            index += 4
        elif value.startswith("\\n", index):
            decoded.append("\n")
            index += 2
        elif value.startswith("\\t", index):
            decoded.append("\t")
            index += 2
        elif value.startswith("\\\\", index):
            decoded.append("\\")
            index += 2
        else:
            decoded.append(value[index])
            index += 1
    return "".join(decoded)


class _OptionalStringJoinBase:
    INPUT_COUNT = 2
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "join_strings"
    CATEGORY = CATEGORY
    DESCRIPTION = (
        "Joins connected non-empty STRING inputs in socket order. "
        "Unconnected inputs and empty strings are ignored. "
        "If no usable string exists, returns an empty string."
    )

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            f"text_{index}": (
                "STRING",
                {
                    "forceInput": True,
                    "tooltip": (
                        "Optional STRING input. Missing inputs and exact empty strings "
                        "are ignored."
                    ),
                },
            )
            for index in range(1, cls.INPUT_COUNT + 1)
        }
        return {
            "required": {
                "separator": (
                    "STRING",
                    {
                        "default": ", ",
                        "multiline": False,
                        "dynamicPrompts": False,
                        "tooltip": (
                            "Inserted only between usable strings. "
                            r"Supports \n, \r\n, \t, and \\."
                        ),
                    },
                ),
            },
            "optional": optional,
        }

    def join_strings(self, separator: str = ", ", **kwargs: Any):
        values = [
            kwargs.get(f"text_{index}")
            for index in range(1, self.INPUT_COUNT + 1)
        ]
        parts = _valid_non_empty_strings(values)
        safe_separator = decode_separator(separator)
        return (safe_separator.join(parts),)


class OptionalStringJoin2(_OptionalStringJoinBase):
    INPUT_COUNT = 2


class OptionalStringJoin3(_OptionalStringJoinBase):
    INPUT_COUNT = 3


class OptionalStringJoin5(_OptionalStringJoinBase):
    INPUT_COUNT = 5


class OptionalStringJoin10(_OptionalStringJoinBase):
    INPUT_COUNT = 10


class _RuntimeToggleStringJoinBase:
    INPUT_COUNT = 10
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "join_strings"
    CATEGORY = CATEGORY
    DESCRIPTION = (
        "Joins queued STRING inputs using the latest live toggle and mode state "
        "at node execution time. Saved values are used as a fallback."
    )

    @classmethod
    def INPUT_TYPES(cls):
        max_mask = (1 << cls.INPUT_COUNT) - 1
        optional = {
            f"text_{index}": (
                "STRING",
                {
                    "forceInput": True,
                    "tooltip": (
                        "Optional queued STRING input. Its generated value is accepted "
                        "or rejected at execution time by the live toggle."
                    ),
                },
            )
            for index in range(1, cls.INPUT_COUNT + 1)
        }
        return {
            "required": {
                "separator": (
                    "STRING",
                    {
                        "default": ", ",
                        "multiline": False,
                        "dynamicPrompts": False,
                        "tooltip": r"Supports \n, \r\n, \t, and \\.",
                    },
                ),
                "mode": (
                    ["multiple", "single"],
                    {"default": "multiple"},
                ),
                "enabled_mask": (
                    "INT",
                    {
                        "default": max_mask,
                        "min": 0,
                        "max": max_mask,
                        "step": 1,
                    },
                ),
                "selected_index": (
                    "INT",
                    {
                        "default": 0,
                        "min": -1,
                        "max": cls.INPUT_COUNT - 1,
                        "step": 1,
                    },
                ),
                "state_key": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "dynamicPrompts": False,
                    },
                ),
            },
            "optional": optional,
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @classmethod
    def _resolve_state_key(cls, state_key: str, unique_id: Any) -> str:
        key = state_key.strip() if isinstance(state_key, str) else ""
        return key or f"string-join-tools-node-{unique_id}"

    @classmethod
    def _normalise_fallback_state(
        cls,
        *,
        mode: str,
        enabled_mask: int,
        selected_index: int,
    ) -> tuple[str, int, int]:
        mode_value = mode if mode in VALID_MODES else "multiple"
        max_mask = (1 << cls.INPUT_COUNT) - 1
        mask = int(enabled_mask) & max_mask
        selected = int(selected_index)

        if not 0 <= selected < cls.INPUT_COUNT:
            selected = -1

        if mode_value == "single":
            if mask == 0:
                selected = -1
            else:
                if selected < 0 or not (mask & (1 << selected)):
                    selected = (mask & -mask).bit_length() - 1
                mask = 1 << selected

        return mode_value, mask, selected

    @classmethod
    def IS_CHANGED(
        cls,
        separator=", ",
        mode="multiple",
        enabled_mask=None,
        selected_index=0,
        state_key="",
        unique_id=None,
        **kwargs,
    ):
        fallback_mask = (
            (1 << cls.INPUT_COUNT) - 1
            if enabled_mask is None
            else int(enabled_mask)
        )
        key = cls._resolve_state_key(state_key, unique_id)
        live_state = RUNTIME_STATE_STORE.get(key)
        decoded_separator = decode_separator(separator)
        if live_state is not None:
            return (
                f"{key}|live|{live_state.revision}|{live_state.mode}|"
                f"{live_state.enabled_mask}|{live_state.selected_index}|"
                f"{decoded_separator!r}"
            )
        return (
            f"{key}|fallback|{mode}|{fallback_mask}|"
            f"{int(selected_index)}|{decoded_separator!r}"
        )

    def join_strings(
        self,
        separator: str,
        mode: str,
        enabled_mask: int,
        selected_index: int,
        state_key: str,
        unique_id=None,
        **kwargs: Any,
    ):
        key = self._resolve_state_key(state_key, unique_id)
        live_state = RUNTIME_STATE_STORE.get(key)

        if live_state is not None:
            active_mode = live_state.mode
            active_mask = live_state.enabled_mask
            active_selected = live_state.selected_index
        else:
            active_mode, active_mask, active_selected = self._normalise_fallback_state(
                mode=mode,
                enabled_mask=enabled_mask,
                selected_index=selected_index,
            )

        active_mode, active_mask, active_selected = self._normalise_fallback_state(
            mode=active_mode,
            enabled_mask=active_mask,
            selected_index=active_selected,
        )

        values = [
            kwargs.get(f"text_{index + 1}")
            for index in range(self.INPUT_COUNT)
            if active_mask & (1 << index)
        ]
        parts = _valid_non_empty_strings(values)
        safe_separator = decode_separator(separator)
        return (safe_separator.join(parts),)


class _ToggleStringJoinBase(_RuntimeToggleStringJoinBase):
    """Queue-snapshot toggle join that never reads server-side live state."""

    DESCRIPTION = (
        "Joins the non-empty STRING inputs enabled when the prompt is queued. "
        "Later toggle changes do not affect already queued jobs."
    )

    @classmethod
    def INPUT_TYPES(cls):
        input_types = super().INPUT_TYPES()
        input_types["required"].pop("state_key", None)
        input_types.pop("hidden", None)
        for input_definition in input_types["optional"].values():
            input_definition[1]["tooltip"] = (
                "Optional queued STRING input. Whether it is included is captured "
                "when the prompt is queued."
            )
        return input_types

    @classmethod
    def IS_CHANGED(
        cls,
        separator=", ",
        mode="multiple",
        enabled_mask=None,
        selected_index=0,
        **kwargs,
    ):
        fallback_mask = (
            (1 << cls.INPUT_COUNT) - 1
            if enabled_mask is None
            else int(enabled_mask)
        )
        active_mode, active_mask, active_selected = cls._normalise_fallback_state(
            mode=mode,
            enabled_mask=fallback_mask,
            selected_index=selected_index,
        )
        return (
            f"queued|{active_mode}|{active_mask}|{active_selected}|"
            f"{decode_separator(separator)!r}"
        )

    def join_strings(
        self,
        separator: str,
        mode: str,
        enabled_mask: int,
        selected_index: int,
        **kwargs: Any,
    ):
        _, active_mask, _ = self._normalise_fallback_state(
            mode=mode,
            enabled_mask=enabled_mask,
            selected_index=selected_index,
        )
        values = [
            kwargs.get(f"text_{index + 1}")
            for index in range(self.INPUT_COUNT)
            if active_mask & (1 << index)
        ]
        parts = _valid_non_empty_strings(values)
        return (decode_separator(separator).join(parts),)


class ToggleStringJoin2(_ToggleStringJoinBase):
    INPUT_COUNT = 2


class ToggleStringJoin3(_ToggleStringJoinBase):
    INPUT_COUNT = 3


class ToggleStringJoin5(_ToggleStringJoinBase):
    INPUT_COUNT = 5


class ToggleStringJoin10(_ToggleStringJoinBase):
    INPUT_COUNT = 10


class RuntimeToggleStringJoin2(_RuntimeToggleStringJoinBase):
    INPUT_COUNT = 2


class RuntimeToggleStringJoin3(_RuntimeToggleStringJoinBase):
    INPUT_COUNT = 3


class RuntimeToggleStringJoin5(_RuntimeToggleStringJoinBase):
    INPUT_COUNT = 5


class RuntimeToggleStringJoin10(_RuntimeToggleStringJoinBase):
    INPUT_COUNT = 10


class RuntimeTextInput:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "get_text"
    CATEGORY = CATEGORY
    DESCRIPTION = (
        "Returns the latest server-accepted live text at execution time. "
        "The text captured when queued is used only while no live state exists."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
                "state_key": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "dynamicPrompts": False,
                    },
                ),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @staticmethod
    def _resolve_state_key(state_key: str, unique_id: Any) -> str:
        key = state_key.strip() if isinstance(state_key, str) else ""
        return key or f"string-join-tools-runtime-text-{unique_id}"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # A constant token would let prompt caching freeze the value seen when the
        # queue was submitted. NaN deliberately makes every queued job execute.
        return float("NaN")

    def get_text(self, text: str = "", state_key: str = "", unique_id=None):
        key = self._resolve_state_key(state_key, unique_id)
        try:
            live_state = RUNTIME_TEXT_STATE_STORE.get(key)
        except Exception:
            live_state = None
        if live_state is not None:
            return (live_state.text,)
        return (text if isinstance(text, str) else "",)


class StringOutput:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "show_text"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Displays a STRING and its character count, then returns it unchanged."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "text": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
        }

    def show_text(self, text: str = ""):
        safe_text = text if isinstance(text, str) else ("" if text is None else str(text))
        return {
            "ui": {
                "text": [safe_text],
                "length": [len(safe_text)],
            },
            "result": (safe_text,),
        }


NODE_CLASS_MAPPINGS = {
    "StringJoinTools_OptionalJoin2": OptionalStringJoin2,
    "StringJoinTools_OptionalJoin3": OptionalStringJoin3,
    "StringJoinTools_OptionalJoin5": OptionalStringJoin5,
    "StringJoinTools_OptionalJoin10": OptionalStringJoin10,
    "StringJoinTools_ToggleJoin2": ToggleStringJoin2,
    "StringJoinTools_ToggleJoin3": ToggleStringJoin3,
    "StringJoinTools_ToggleJoin5": ToggleStringJoin5,
    "StringJoinTools_ToggleJoin10": ToggleStringJoin10,
    "StringJoinTools_RuntimeToggleJoin2": RuntimeToggleStringJoin2,
    "StringJoinTools_RuntimeToggleJoin3": RuntimeToggleStringJoin3,
    "StringJoinTools_RuntimeToggleJoin5": RuntimeToggleStringJoin5,
    "StringJoinTools_RuntimeToggleJoin10": RuntimeToggleStringJoin10,
    "StringJoinTools_RuntimeTextInput": RuntimeTextInput,
    "StringJoinTools_StringOutput": StringOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringJoinTools_OptionalJoin2": "Optional String Join (2)",
    "StringJoinTools_OptionalJoin3": "Optional String Join (3)",
    "StringJoinTools_OptionalJoin5": "Optional String Join (5)",
    "StringJoinTools_OptionalJoin10": "Optional String Join (10)",
    "StringJoinTools_ToggleJoin2": "Toggle String Join (2)",
    "StringJoinTools_ToggleJoin3": "Toggle String Join (3)",
    "StringJoinTools_ToggleJoin5": "Toggle String Join (5)",
    "StringJoinTools_ToggleJoin10": "Toggle String Join (10)",
    "StringJoinTools_RuntimeToggleJoin2": "Runtime Toggle String Join (2)",
    "StringJoinTools_RuntimeToggleJoin3": "Runtime Toggle String Join (3)",
    "StringJoinTools_RuntimeToggleJoin5": "Runtime Toggle String Join (5)",
    "StringJoinTools_RuntimeToggleJoin10": "Runtime Toggle String Join (10)",
    "StringJoinTools_RuntimeTextInput": "Runtime Text Input",
    "StringJoinTools_StringOutput": "String Output",
}
