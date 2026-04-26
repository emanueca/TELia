import os
from cryptography.fernet import Fernet

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("RU_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("RU_ENCRYPTION_KEY não definida no .env")
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()
