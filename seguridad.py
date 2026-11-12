"""Funciones criptográficas proporcionadas para COMP 2700."""
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def crear_hash(clave):
    """Crea un hash Argon2 con salt aleatorio administrado por la biblioteca."""
    return _hasher.hash(clave)


def verificar_clave(hash_guardado, clave):
    """Verifica una clave sin comparar hashes recién generados."""
    try:
        return _hasher.verify(hash_guardado, clave)
    except (VerificationError, InvalidHashError, TypeError):
        return False
