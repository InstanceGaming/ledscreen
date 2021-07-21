from cryptography.fernet import Fernet
import base64


def generate_key():
    return base64.b64encode(Fernet.generate_key())


def decrypt(key: str, ciphertext: str):
    f = Fernet(base64.b64decode(key))
    return f.decrypt(base64.b64decode(ciphertext))


def encrypt(key: str, contents: str, encoding='UTF-8'):
    f = Fernet(base64.b64decode(key))
    return base64.b64encode(f.encrypt(contents.encode(encoding)))
