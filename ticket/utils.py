from hashlib import sha1


def hash_password(password: str) -> str:
    """
    Retorna o hash da senha em sha1, em formato hexadecimal.
    """
    return sha1(password.encode("UTF-8")).hexdigest()
