from typing import Generic, TypeVar, Union, Callable
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
            return self.value
        raise ValueError(f"Called unwrap() on an Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the value of an Ok variant or a default"""
        return self.value if self.is_ok() else default

    def unwrap_err(self) -> E:
        """Return the error of an Err variant or raise an exception"""
        if self.is_err():
            return self.error
        raise ValueError("Called unwrap_err() on an Ok")

    def map(self, f: callable[[T], U]) -> "Result[U, E]":
        """Apply a function to the value of an Ok variant"""
        if self.is_ok():
            return Ok(f(self.value))
        return self

    def map_error(self, f: callable[[E], U]) -> "Result[T, E]":
        """Apply a function to the error of an Err variant"""
        if self.is_err():
            return Err(f(self.error))
        return self

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """Pipe the value of an Ok variant into a function"""
        if self.is_ok():
            try:
                return f(self.value)
            except Exception as e:
                return Err(f"Inner exception: {str(e)}")
        return self

    def or_else(self, f: Callable[[E], "Result[T, U]"]) -> "Result[T, U]":
        """Pipe the error of an Err variant into a function"""
        if self.is_err():
            return f(self.error)
        return self

    def __repr__(self) -> str:
        """Return a string representation of the Result"""
        if self.is_ok():
            return f"Ok({self.value})"
        return f"Err({self.error})"


class Ok(Result[T, E]):
    def __init__(self, value: T):
        self.value = value


class Err(Result[T, E]):
    def __init__(self, error: E):
        self.error = error


class DivisionError(Enum):
    DIVISION_BY_ZERO = "Division by zero"
    NEGATIVE_NUMBER = "Negative number"


class SqrtError(Enum):
    NEGATIVE_NUMBER = "Negative number"


DivisionResult = Result[float, DivisionError]
SqrtResult = Result[float, SqrtError]


def division(a: float, b: float) -> DivisionResult:
    if b == 0:
        return Err(DivisionError.DIVISION_BY_ZERO)
    if a < 0 or b < 0:
        return Err(DivisionError.NEGATIVE_NUMBER)
    return Ok(a / b)


def sqrt_if_positive(x: float) -> SqrtResult:
    return Ok(x ** 0.5) if x >= 0 else Err(SqrtError.NEGATIVE_NUMBER)


def unsafe_function(x: int) -> Result[int, str]:
    return Ok(10 / x)


result = division(10, 2).map(
    lambda x: x * 2).map_error(DivisionError.NEGATIVE_NUMBER)

result = division(10, 2).and_then(sqrt_if_positive)

match result:
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")

fail = Ok(0).and_then(unsafe_function)  # Unhandled exception

Err("Problem").or_else(lambda e: Ok(100))  # fallback to Ok(100)
Err("Problem").or_else(lambda e: Err(f"Error : {e}"))  # transform the error
