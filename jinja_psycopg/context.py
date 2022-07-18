from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class FormatArgs:
    prefix: str
    dictionary: dict[str, Any] = field(default_factory=dict)
    num_values: int = 0

    def save_value(self, value: Any) -> str:
        key = f"{self.prefix}#{self.num_values}"
        self.dictionary[key] = value

        self.num_values += 1
        return key


class FormatArgsContext:
    def __init__(self, name: str) -> None:
        self._context_var = ContextVar[Optional[FormatArgs]](name, default=None)

    def save_value(self, value: Any) -> str:
        context = self._context_var.get()
        if context is None:
            raise RuntimeError(
                "Called ContextWriter.save_value, but no context was found"
            )

        return context.save_value(value)

    def recorder(self, prefix: str):
        return FormatArgsRecorder(self._context_var, prefix)


class FormatArgsRecorder:
    def __init__(
        self, context_var: ContextVar[Optional[FormatArgs]], prefix: str
    ) -> None:
        self._context_var = context_var
        self._prefix = prefix
        self._recorded = None

    def __enter__(self):
        self._token = self._context_var.set(FormatArgs(self._prefix))

    def __exit__(self, type, value, traceback):
        context = self._context_var.get()
        if context is None:
            raise RuntimeError("Finished recording, but ContextVar was empty")

        self._recorded = context.dictionary
        self._context_var.reset(self._token)

    def unwrap(self) -> dict[str, Any]:
        if self._recorded is None:
            raise RuntimeError(
                "Called ContextDictRecorder.unwrap(), but nothing was recorded"
            )

        return self._recorded
