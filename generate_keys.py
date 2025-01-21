
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def generate_keys():
    # Генерация ключей
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Сохранение приватного ключа
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open("vapid_private_key.pem", "wb") as f:
        f.write(private_key_pem)

    # Сохранение публичного ключа
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open("vapid_public_key.pem", "wb") as f:
        f.write(public_key_pem)

    print("VAPID keys generated and saved!")
