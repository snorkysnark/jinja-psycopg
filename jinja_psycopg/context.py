from contextvars import ContextVar
from typing import Optional, Any


class ContextDict:
    def __init__(self, name: str) -> None:
        self._context_var = ContextVar[Optional[dict[str, Any]]](name, default=None)

    def write_safe(self, key: str, value: str):
        dictionary = self._context_var.get()
        if dictionary is not None:
            dictionary[key] = value

    def recorder(self):
        return ContextDictRecorder(self._context_var)


class ContextDictRecorder:
    def __init__(self, context_var: ContextVar[Optional[dict[str, Any]]]) -> None:
        self._context_var = context_var
        self._recorded = None

    def __enter__(self):
        self._token = self._context_var.set({})

    def __exit__(self, type, value, traceback):
        self._recorded = self._context_var.get()
        self._context_var.reset(self._token)

    def unwrap(self) -> dict[str, Any]:
        if self._recorded is None:
            raise RuntimeError(
                "Called ContextDictRecorder.unwrap(), but nothing was recorded"
            )

        return self._recorded
