from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

def test_password_hashing():
    raw_pwd = "SecretPassword123!"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_access_token_creation_and_decoding():
    token = create_access_token(subject=42, role="admin")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"

def test_refresh_token_creation():
    token = create_refresh_token(subject=99, role="customer")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "99"
    assert payload["type"] == "refresh"
