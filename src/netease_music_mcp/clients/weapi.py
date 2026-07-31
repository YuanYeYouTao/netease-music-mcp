import base64
import json
import secrets
from collections.abc import Mapping
from typing import cast

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

_IV = b"0102030405060708"
_PRESET_KEY = b"0CoJUm6Qyw8W8jud"
_BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDgtQn2JZ34ZC28NWYpAUd98iZ37BUrX/aKzmFbt7clFSs6sXqHauqKWqdtLkF2KexO40H1YTX8z2lSgBBOAxLsvaklV8k4cBFK9snQXE9/DDaFt6Rr7iVZMldczhC0JNgTz+SHXT6CBHuX3e9SdB1Ua44oncaTWz7OBGLbCiK45wIDAQAB
-----END PUBLIC KEY-----"""


def _aes_cbc(value: bytes, key: bytes) -> str:
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(value) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(_IV)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).decode("ascii")


def encrypt_weapi(
    payload: Mapping[str, object], *, secret_key: str | None = None
) -> dict[str, str]:
    """Encrypt the legacy WeAPI form used by NetEase's web client."""
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    secret = secret_key or "".join(secrets.choice(_BASE62) for _ in range(16))
    params = _aes_cbc(_aes_cbc(text, _PRESET_KEY).encode("utf-8"), secret.encode("ascii"))
    public_key = cast(RSAPublicKey, load_pem_public_key(_PUBLIC_KEY))
    # NetEase's legacy WeAPI uses raw RSA here (the upstream Node client passes
    # the "NONE" scheme), not a modern RSA encryption padding mode.
    secret_number = int.from_bytes(secret[::-1].encode("ascii"), "big")
    numbers = public_key.public_numbers()
    encrypted_secret = pow(secret_number, numbers.e, numbers.n).to_bytes(
        (numbers.n.bit_length() + 7) // 8, "big"
    )
    return {"params": params, "encSecKey": encrypted_secret.hex()}
