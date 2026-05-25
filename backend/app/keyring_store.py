import keyring
from typing import Optional

def save_password(connection_id: int, password: str) -> None:
    if password is not None:
        keyring.set_password("querysage", str(connection_id), password)

def get_password(connection_id: int) -> Optional[str]:
    return keyring.get_password("querysage", str(connection_id))

def delete_password(connection_id: int) -> None:
    try:
        keyring.delete_password("querysage", str(connection_id))
    except keyring.errors.PasswordDeleteError:
        pass
