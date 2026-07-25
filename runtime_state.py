from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from time import time
from typing import Optional


VALID_MODES = {"single", "multiple"}


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
