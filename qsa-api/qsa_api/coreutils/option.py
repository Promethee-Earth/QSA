from typing import Generic, TypeVar

T = TypeVar("T")


class Option(Generic[T]):
    pass


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
