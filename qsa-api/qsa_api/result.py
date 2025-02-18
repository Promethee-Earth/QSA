from typing import Generic, TypeVar, Union
from enum import Enum

T = TypeVar("T")
E = TypeVar("E")


class Result(Generic[T, E]):
    def __init__(self, value: Union[T, None] = None, error: Union[E, None] = None):
        self.value = value
        self.error = error

    def is_ok(self) -> bool:
        return self.error is None

    def is_err(self) -> bool:
        return self.error is not None

    def unwrap(self) -> T:
        if self.is_ok():
            return self.value
        raise ValueError(f"Called unwrap() on an Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return self.value if self.is_ok() else default

    def unwrap_err(self) -> E:
        if self.is_err():
            return self.error
        raise ValueError("Called unwrap_err() on an Ok")

    def map(self, f: callable[[T], T]) -> "Result[T, E]":
        if self.is_ok():
            return Result.Ok(f(self.value))
        return self

    def map_error(self, f: callable[[E], E]) -> "Result[T, E]":
        if self.is_err():
            return Result.Err(f(self.error))
        return self

    @staticmethod
    def Ok(value: T) -> "Result[T, E]":
        return Result(value=value)

    @staticmethod
    def Err(error: E) -> "Result[T, E]":
        return Result(error=error)


class Ok(Result[T, E]):
    def __init__(self, value: T):
        self.value = value


class Err(Result[T, E]):
    def __init__(self, error: E):
        self.error = error

class DivisionError(Enum):
    DIVISION_BY_ZERO = "Division par zéro"
    NEGATIVE_NUMBER = "Nombre négatif non autorisé"

Result = Union[float, DivisionError]

def division(a: float, b: float) -> Result:
    if b == 0:
        return Result.Err(DivisionError.DIVISION_BY_ZERO)
    if a < 0 or b < 0:
        return Result.Err(DivisionError.NEGATIVE_NUMBER)
    return Ok(a / b)


result = division(10, 2).map(
    lambda x: x * 2).map_error(DivisionError.NEGATIVE_NUMBER)

match result:
    case Ok(value):
        print(f"Résultat: {value}")
    case Err(error):
        print(f"Erreur: {error}")
