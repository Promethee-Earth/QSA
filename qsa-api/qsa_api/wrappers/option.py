from typing import Generic, TypeVar, cast, Callable

T = TypeVar("T")
U = TypeVar("U")


class Option(Generic[T]):
    """Generic Option type with Some and None variants"""

    value: T  # abstract attribute

    def __init__(self):
        super().__init__()

    def is_some(self) -> bool:
        """Check if the Option is a Some variant"""
        return isinstance(self, Some)

    def is_none(self) -> bool:
        """Check if the Option is a None variant"""
        return isinstance(self, None_)

    def unwrap(self) -> T:
        """Return the value of a Some variant or raise an exception"""
        if self.is_some():
            return self.value
        raise ValueError("Called unwrap() on a None")

    def unwrap_or(self, default: T) -> T:
        """Return the value of a Some variant or a default"""
        return self.value if self.is_some() else default

    def expect(self, msg: str) -> T:
        """Expect a Some variant or raise an exception with a custom message"""
        if self.is_some():
            return self.value
        raise ValueError(msg)

    def map(self, f: Callable[[T], U]) -> "Option[U]":
        """Apply a function to the value of a Some variant"""
        if self.is_some():
            return Some(f(self.value))
        return None_()

    def filter(self, f: Callable[[T], bool]) -> "Option[T]":
        """Filter the value of a Some variant"""
        if self.is_some() and f(self.value):
            return self
        return None_()

    def map_or(self, default: U, f: Callable[[T], U]) -> U:
        """Apply a function to the value of a Some variant or return a default"""
        return f(self.value) if self.is_some() else default

    def and_then(self, f: Callable[[T], "Option[U]"]) -> "Option[U]":
        """Pipe the value of a Some variant into a function"""
        if self.is_some():
            return f(self.value)
        return None_()

    def __eq__(self, other) -> bool:
        """Compare two Option instances"""
        if isinstance(other, Some) and self.is_some():
            return self.value == other.value
        return False


class Some(Option[T]):
    __match_args__ = ("value",)

    def __init__(self, value: T):
        self.value = value

    def __repr__(self):
        return f"Some({self.value})"


class None_(Option[T]):
    _instance = None  # 🔹 Singleton

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(None_, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.value = cast(T, None)

    def __repr__(self):
        return "None"

    def __eq__(self, other) -> bool:
        """Compare a None_ instance with another instance"""
        return isinstance(other, None_)
