from typing import Generic, TypeVar, Union

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
        
        
class DivisionByZeroError(Err[str, str]):
    def __init__(self):
        super().__init__("Division by zero")

class NegativeNumberError(Err[str, str]):
    def __init__(self, number: float):
        super().__init__(f"Negative number not allowed: {number}")
        self.number = number
        
def division(a: float, b: float) -> Result[float, Err[str, str]]:
    if b == 0:
        return DivisionByZeroError()
    if a < 0 or b < 0:
        return NegativeNumberError(a if a < 0 else b)
    return Ok(a / b)

result = division(10, 2)
# match result:
#     case Ok(value):
#         print(f"Result: {value}")
#     case Err(error):
#         print(f"Error: {error}")

match result:
    case Ok(value):
        print(f"Résultat: {value}")
    case DivisionByZeroError():
        print("Erreur: Division par zéro détectée")
    case NegativeNumberError(num):
        print(f"Erreur: Nombre négatif détecté ({num})")
    case Err(error):
        print(f"Erreur inconnue: {error}")