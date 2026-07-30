from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from time import time
from typing import Optional


VALID_MODES = {"single", "multiple"}
MAX_RUNTIME_TEXT_BYTES = 512 * 1024


@dataclass(frozen=True)
class RuntimeJoinState:
    state_key: str
    mode: str
    enabled_mask: int
    selected_index: int
    input_count: int
    revision: int
    updated_at: float

    def to_dict(self) -> dict:
        return asdict(self)


class RuntimeStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._states: dict[str, RuntimeJoinState] = {}

    @staticmethod
    def _normalise(
        *,
        mode: str,
        enabled_mask: int,
        selected_index: int,
        input_count: int,
    ) -> tuple[str, int, int, int]:
        count = max(1, int(input_count))
        mode_value = mode if mode in VALID_MODES else "multiple"
        max_mask = (1 << count) - 1
        mask = int(enabled_mask) & max_mask
        selected = int(selected_index)

        if not 0 <= selected < count:
            selected = -1

        if mode_value == "single":
            if mask == 0:
                selected = -1
            else:
                if selected < 0 or not (mask & (1 << selected)):
                    selected = (mask & -mask).bit_length() - 1
                mask = 1 << selected

        return mode_value, mask, selected, count

    def update(
        self,
        *,
        state_key: str,
        mode: str,
        enabled_mask: int,
        selected_index: int,
        input_count: int,
    ) -> RuntimeJoinState:
        key = str(state_key).strip()
        if not key:
            raise ValueError("state_key must not be empty")

        mode_value, mask, selected, count = self._normalise(
            mode=mode,
            enabled_mask=enabled_mask,
            selected_index=selected_index,
            input_count=input_count,
        )

        with self._lock:
            previous = self._states.get(key)
            changed = (
                previous is None
                or previous.mode != mode_value
                or previous.enabled_mask != mask
                or previous.selected_index != selected
                or previous.input_count != count
            )
            revision = 1 if previous is None else previous.revision + int(changed)
            state = RuntimeJoinState(
                state_key=key,
                mode=mode_value,
                enabled_mask=mask,
                selected_index=selected,
                input_count=count,
                revision=revision,
                updated_at=time(),
            )
            self._states[key] = state
            return state

    def get(self, state_key: str) -> Optional[RuntimeJoinState]:
        key = str(state_key).strip()
        if not key:
            return None
        with self._lock:
            return self._states.get(key)

    def clear(self, state_key: str) -> bool:
        key = str(state_key).strip()
        if not key:
            return False
        with self._lock:
            return self._states.pop(key, None) is not None


RUNTIME_STATE_STORE = RuntimeStateStore()


class StaleRuntimeTextUpdate(ValueError):
    """Raised when one browser session sends an older text update."""


@dataclass(frozen=True)
class RuntimeTextState:
    state_key: str
    text: str
    revision: int
    client_id: str
    client_sequence: int
    updated_at: float

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("client_id", None)
        data.pop("client_sequence", None)
        return data


class RuntimeTextStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._states: dict[str, RuntimeTextState] = {}
        self._client_updates: dict[tuple[str, str], tuple[int, str]] = {}

    @staticmethod
    def _validate(
        *,
        state_key: str,
        text: str,
        client_id: str,
        client_sequence: int,
    ) -> tuple[str, str, str, int]:
        if not isinstance(state_key, str):
            raise TypeError("state_key must be a string")
        key = state_key.strip()
        if not key:
            raise ValueError("state_key must not be empty")
        if len(key) > 256:
            raise ValueError("state_key must be at most 256 characters")

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if len(text.encode("utf-8")) > MAX_RUNTIME_TEXT_BYTES:
            raise ValueError(
                f"text must be at most {MAX_RUNTIME_TEXT_BYTES} UTF-8 bytes"
            )

        if not isinstance(client_id, str):
            raise TypeError("client_id must be a string")
        session = client_id.strip()
        if not session:
            raise ValueError("client_id must not be empty")
        if len(session) > 128:
            raise ValueError("client_id must be at most 128 characters")

        if isinstance(client_sequence, bool) or not isinstance(client_sequence, int):
            raise TypeError("client_sequence must be an integer")
        if client_sequence < 0:
            raise ValueError("client_sequence must not be negative")

        return key, text, session, client_sequence

    def update(
        self,
        *,
        state_key: str,
        text: str,
        client_id: str,
        client_sequence: int,
    ) -> RuntimeTextState:
        key, value, session, sequence = self._validate(
            state_key=state_key,
            text=text,
            client_id=client_id,
            client_sequence=client_sequence,
        )

        with self._lock:
            previous = self._states.get(key)
            previous_client_update = self._client_updates.get((key, session))
            if previous_client_update is not None:
                previous_sequence, previous_text = previous_client_update
                if sequence < previous_sequence:
                    raise StaleRuntimeTextUpdate(
                        "client_sequence is older than the accepted update"
                    )
                if sequence == previous_sequence:
                    if value != previous_text:
                        raise StaleRuntimeTextUpdate(
                            "client_sequence was already used for different text"
                        )
                    if (
                        previous is not None
                        and previous.client_id == session
                        and previous.text == value
                    ):
                        return previous
                    raise StaleRuntimeTextUpdate(
                        "update was already superseded by another client"
                    )

            changed = previous is None or previous.text != value
            revision = 1 if previous is None else previous.revision + int(changed)
            state = RuntimeTextState(
                state_key=key,
                text=value,
                revision=revision,
                client_id=session,
                client_sequence=sequence,
                updated_at=time(),
            )
            self._states[key] = state
            self._client_updates[(key, session)] = (sequence, value)
            return state

    def get(self, state_key: str) -> Optional[RuntimeTextState]:
        if not isinstance(state_key, str):
            return None
        key = state_key.strip()
        if not key:
            return None
        with self._lock:
            return self._states.get(key)

    def clear(self, state_key: str) -> bool:
        if not isinstance(state_key, str):
            return False
        key = state_key.strip()
        if not key:
            return False
        with self._lock:
            removed = self._states.pop(key, None) is not None
            for client_key in [
                client_key
                for client_key in self._client_updates
                if client_key[0] == key
            ]:
                self._client_updates.pop(client_key, None)
            return removed


RUNTIME_TEXT_STATE_STORE = RuntimeTextStateStore()
