from typing import Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class Option(Generic[T]):
    """Generic Option type with Some and None variants"""
    
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
    
    def map(self, f: callable[[T], U]) -> "Option[U]":
        """Apply a function to the value of a Some variant"""
        if self.is_some():
            return Some(f(self.value))
        return self
    
    def and_then(self, f: callable[[T], "Option[U]"]) -> "Option[U]":
        """Pipe the value of a Some variant into a function"""
        if self.is_some():
            return f(self.value)
        return self
    
    def __repr__(self):
        raise NotImplementedError
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Some) and self.is_some():
            return self.value == other.value
        return False
    


class Some(Option[T]):
    def __init__(self, value: T):
        self.value = value

    def __repr__(self):
        return f"Some({self.value})"


class None_(Option[T]):
    def __repr__(self):
        return "None"


def find_user(user_id: int) -> Option[str]:
    users = {1: "Alice", 2: "Bob"}
    return Some(users[user_id]) if user_id in users else None_()


result = find_user(1)
print(result)  # Some(Alice)

result = find_user(42)
print(result)  # None

match find_user(2):
    case Some(value):
        print(f"Utilisateur trouvé: {value}")
    case None_():
        print("Utilisateur non trouvé")
