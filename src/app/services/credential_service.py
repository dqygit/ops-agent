import base64
import hashlib
from itertools import cycle


class CredentialService:
    encryption_version = "v1"

    def __init__(self, secret_key: str):
        self._key = hashlib.sha256(secret_key.encode("utf-8")).digest()

    def encrypt_secret(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        encrypted = bytes(value ^ key for value, key in zip(raw, cycle(self._key), strict=False))
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt_secret(self, encrypted_blob: str) -> str:
        raw = base64.b64decode(encrypted_blob.encode("utf-8"))
        decrypted = bytes(value ^ key for value, key in zip(raw, cycle(self._key), strict=False))
        return decrypted.decode("utf-8")
