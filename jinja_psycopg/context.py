from __future__ import annotations
from contextvars import ContextVar
from typing import Optional, Any


class FormatArgs:
    def __init__(self, prefix: str) -> None:
        """Data structure for recording values in jinja blocks to be formatted by psycopg

        Args:
            prefix: Prefix used in dictionary keys
        """

        self._prefix = prefix
        self._dictionary = {}
        self._num_values = 0

    def save_value(self, value: Any) -> str:
        """
        Args:
            value: value to save

        Returns:
            generated key in the format of `prefix#number`
        """
        key = f"{self._prefix}#{self._num_values}"
        self._dictionary[key] = value

        self._num_values += 1
        return key

    @property
    def dictionary(self) -> dict:
        """
        Returns:
            saved values
        """
        return self._dictionary


class FormatArgsContext:
    def __init__(self, name: str) -> None:
        """Wrapper for [contextvars.ContextVar][] used for saving format args from within
            [`psycopg`][jinja_psycopg.renderer.psycopg_filter] filter and for creating argument recorders

        Args:
            name: name used by the ContextVar
        """
        self._context_var = ContextVar[Optional[FormatArgs]](name, default=None)

    def save_value(self, value: Any) -> str:
        """
        Args:
            value: value to save

        Returns:
            generated key in the format of `prefix#number`

        Raises:
            RuntimeError: if ContextVar was empty
        """

        context = self._context_var.get()
        if context is None:
            raise RuntimeError(
                "Called ContextWriter.save_value, but no context was found"
            )

        return context.save_value(value)

    def recorder(self, prefix: str) -> FormatArgsRecorder:
        """
        Args:
            prefix: Prefix for the keys in the resulting dictionary

        Returns:
            new recorder with the given prefix
        """
        return FormatArgsRecorder(self._context_var, prefix)


class FormatArgsRecorder:
    def __init__(
        self, context_var: ContextVar[Optional[FormatArgs]], prefix: str
    ) -> None:
        """[contextvars.ContextVar][] wrapper that works as a context manager
        and records arguments saved within its scope into a dictionary

        Args:
            context_var: Inner ContextVar
            prefix: Prefix used in dictionary keys
        """

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
        """
        Returns:
            the recorded arguments

        Raises:
            RuntimeError: if nothing was recorded
        """
        if self._recorded is None:
            raise RuntimeError(
                "Called ContextDictRecorder.unwrap(), but nothing was recorded"
            )

        return self._recorded
