"""Field-level encryption for personal data stored in the database.

Use EncryptedString as a column type. The database only ever holds the
encrypted text; your Python code reads and writes the normal value:

    phone = db.Column(EncryptedString, default="")
    account.phone = "+65 91234567"   # saved encrypted
    print(account.phone)             # "+65 91234567"

Encryption uses Fernet (AES-128 in CBC mode + HMAC-SHA256) from the
`cryptography` package. The key comes from the ENCRYPTION_KEY config
value (see app/__init__.py). Lose the key and the data cannot be read.

Encrypted columns cannot be searched with filter_by(), because the same
value encrypts differently every time. Only encrypt fields you never
search on.
"""
import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy.types import Text, TypeDecorator


@lru_cache(maxsize=4)
def _fernet(key):
    return Fernet(key)


def _cipher():
    return _fernet(current_app.config["ENCRYPTION_KEY"])


def encrypt(value):
    return _cipher().encrypt(value.encode()).decode()


def decrypt(token):
    try:
        return _cipher().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError(
            "Could not decrypt a stored value. The database was probably made "
            "with a different ENCRYPTION_KEY or before encryption was added. "
            "Delete instance/eeveelution.db and run: python seed.py"
        ) from None


def phone_digest(value):
    """Searchable fingerprint of a phone number, so 'is this number taken?' can be answered.

    Encrypted columns cannot be searched, so each phone also stores this keyed hash
    (HMAC-SHA256 with the ENCRYPTION_KEY). Without the key the digests cannot be turned
    back into phone numbers, even though phone numbers have few possible values.
    """
    if not value:
        return None
    key = current_app.config["ENCRYPTION_KEY"].encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


class EncryptedString(TypeDecorator):
    """A text column that is encrypted in the database and plain in Python."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # Python -> database
        return None if value is None else encrypt(value)

    def process_result_value(self, value, dialect):  # database -> Python
        return None if value is None else decrypt(value)
