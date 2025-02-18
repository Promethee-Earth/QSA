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
        
        
def division(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("Division by zero")
    return Ok(a / b)

result = division(10, 2)
match result:
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")