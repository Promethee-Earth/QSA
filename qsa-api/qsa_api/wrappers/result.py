from typing import Generic, TypeVar, Union, Callable, cast
from enum import Enum

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class Result(Generic[T, E]):
    """Generic Result type with Ok and Err variants"""

    def __init__(self, value: Union[T, None] = None, error: Union[E, None] = None):
        self.value = value
        self.error = error

    def is_ok(self) -> bool:
        """Check if the Result is an Ok variant"""
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        """Check if the Result is an Err variant"""
        return isinstance(self, Err)

    def unwrap(self) -> T:
        """Return the value of an Ok variant or raise an exception"""
        if self.is_ok():
            return cast(T, self.value)
        raise ValueError(f"Called unwrap() on an Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the value of an Ok variant or a default"""
        return cast(T, self.value) if self.is_ok() else default

    def unwrap_err(self) -> E:
        """Return the error of an Err variant or raise an exception"""
        if self.is_err():
            return cast(E, self.error)
        raise ValueError("Called unwrap_err() on an Ok")

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        """Apply a function to the value of an Ok variant"""
        if self.is_ok():
            return Ok(f(cast(T, self.value)))
        return cast("Result[U, E]", self)

    def map_error(self, f: Callable[[E], U]) -> "Result[T, U]":
        """Apply a function to the error of an Err variant"""
        if self.is_err():
            return Err(f(self.error))
        return cast("Result[T, U]", self)

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """Pipe the value of an Ok variant into a function"""
        if self.is_ok():
            return f(cast(T, self.value))
        return cast(Result[U, E], self)

    def or_else(self, f: Callable[[E], "Result[T, U]"]) -> "Result[T, U]":
        """Pipe the error of an Err variant into a function"""
        if self.is_err():
            return f(cast(E, self.error))
        return cast(Result[T, U], self)

    def __repr__(self) -> str:
        """Return a string representation of the Result"""
        if self.is_ok():
            return f"Ok({self.value})"
        return f"Err({self.error})"

    def __eq__(self, other) -> bool:
        """Compare two Result instances"""
        if isinstance(other, Result):
            if self.is_ok() and other.is_ok():
                return self.value == other.value
            if self.is_err() and other.is_err():
                return self.error == other.error
        return False


class Ok(Result[T, E]):
    __match_args__ = ("value",)

    def __init__(self, value: T):
        self.value = value


class Err(Result[T, E]):
    __match_args__ = ("error",)

    def __init__(self, error: E):
        self.error = error
