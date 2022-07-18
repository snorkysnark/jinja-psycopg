from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class FormatArgs:
    """Data structure for recording values in jinja blocks to be formatted by psycopg
    Args:
        - prefix (str): Prefix used in dictionary keys"""

    prefix: str
    dictionary: dict[str, Any] = field(default_factory=dict)
    num_values: int = 0

    def save_value(self, value: Any) -> str:
        """Saves the value to dictionary, returning its key
        in the format of `prefix#number`"""
        key = f"{self.prefix}#{self.num_values}"
        self.dictionary[key] = value

        self.num_values += 1
        return key


class FormatArgsContext:
    """Wrapper for ContextVar used for saving format args from within `psycopg` filter
    and for creating argument recorders"""

    def __init__(self, name: str) -> None:
        """Args:
        - name (str): name used by the ContextVar"""
        self._context_var = ContextVar[Optional[FormatArgs]](name, default=None)

    def save_value(self, value: Any) -> str:
        """Saves the value to dictionary, returning its key
        in the format of `prefix#number`.

        Errors if ContextVar is empty"""
        context = self._context_var.get()
        if context is None:
            raise RuntimeError(
                "Called ContextWriter.save_value, but no context was found"
            )

        return context.save_value(value)

    def recorder(self, prefix: str):
        """Args:
        - prefix (str): Prefix for the keys in the resulting dictionary"""
        return FormatArgsRecorder(self._context_var, prefix)


class FormatArgsRecorder:
    """ContextVar wrapper that works as a context manager
    and records arguments saved within its scope into a dictionary"""

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
        """Returs the recorded arguments, errors if nothing was recorder"""
        if self._recorded is None:
            raise RuntimeError(
                "Called ContextDictRecorder.unwrap(), but nothing was recorded"
            )

        return self._recorded
