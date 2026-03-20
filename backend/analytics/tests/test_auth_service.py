"""Unit tests for AuthService — no database required."""
import pytest
import jwt
from pyramid.httpexceptions import HTTPUnauthorized

from analytics.services.auth import AuthService

SETTINGS = {
    'jwt.secret': 'test-jwt-secret-key-for-unit-tests',
    'jwt.algorithm': 'HS256',
    'jwt.expiration': '3600',
}


@pytest.fixture
def svc():
    return AuthService(SETTINGS)


class TestHashPassword:
    def test_returns_bcrypt_hash(self, svc):
        hashed = svc.hash_password('mypassword')
        assert hashed.startswith('$2b$')

    def test_verify_correct_password(self, svc):
        hashed = svc.hash_password('correct')
        assert svc.verify_password('correct', hashed) is True

    def test_reject_wrong_password(self, svc):
        hashed = svc.hash_password('correct')
        assert svc.verify_password('wrong', hashed) is False


class TestGenerateApiKey:
    def test_returns_64_char_hex(self, svc):
        key = svc.generate_api_key()
        assert len(key) == 64
        int(key, 16)  # raises ValueError if not hex

    def test_unique_keys(self, svc):
        assert svc.generate_api_key() != svc.generate_api_key()


class TestValidatePasswordStrength:
    def test_too_short(self, svc):
        assert svc.validate_password_strength('Ab1!') is not None

    def test_no_uppercase(self, svc):
        assert svc.validate_password_strength('testpass1!') is not None

    def test_no_digit_or_special(self, svc):
        assert svc.validate_password_strength('TestPasswd') is not None

    def test_valid_with_digit(self, svc):
        assert svc.validate_password_strength('TestPass1') is None

    def test_valid_with_special(self, svc):
        assert svc.validate_password_strength('TestPass!') is None

    def test_valid_full(self, svc):
        assert svc.validate_password_strength('TestPass1!') is None


class TestCreateToken:
    def test_returns_all_fields(self, svc):
        result = svc.create_token('user-id', 'user@example.com')
        assert set(result.keys()) == {'access_token', 'refresh_token', 'token_type', 'expires_in'}

    def test_token_type_is_bearer(self, svc):
        result = svc.create_token('user-id', 'user@example.com')
        assert result['token_type'] == 'Bearer'

    def test_expires_in_matches_setting(self, svc):
        result = svc.create_token('user-id', 'user@example.com')
        assert result['expires_in'] == 3600

    def test_access_token_type_claim(self, svc):
        result = svc.create_token('user-id', 'user@example.com')
        payload = svc.decode_token(result['access_token'])
        assert payload['type'] == 'access'

    def test_refresh_token_type_claim(self, svc):
        result = svc.create_token('user-id', 'user@example.com')
        payload = svc.decode_token(result['refresh_token'])
        assert payload['type'] == 'refresh'


class TestDecodeToken:
    def test_valid_token_returns_payload(self, svc):
        tokens = svc.create_token('uid', 'e@e.com')
        payload = svc.decode_token(tokens['access_token'])
        assert payload['sub'] == 'uid'

    def test_expired_token_raises_unauthorized(self, svc):
        from datetime import datetime, timedelta
        expired = jwt.encode(
            {'sub': 'uid', 'type': 'access', 'exp': datetime.utcnow() - timedelta(seconds=1)},
            SETTINGS['jwt.secret'], algorithm='HS256'
        )
        with pytest.raises(HTTPUnauthorized):
            svc.decode_token(expired)

    def test_invalid_token_raises_unauthorized(self, svc):
        with pytest.raises(HTTPUnauthorized):
            svc.decode_token('not.a.token')


class TestRefreshAccessToken:
    def test_valid_refresh_returns_new_tokens(self, svc, dbsession, make_user):
        user = make_user(email='refresh@example.com')
        tokens = svc.create_token(str(user.id), user.email)
        result = svc.refresh_access_token(tokens['refresh_token'], dbsession)
        assert 'access_token' in result

    def test_access_token_as_refresh_raises(self, svc, dbsession, make_user):
        user = make_user(email='badrefresh@example.com')
        tokens = svc.create_token(str(user.id), user.email)
        with pytest.raises(HTTPUnauthorized):
            svc.refresh_access_token(tokens['access_token'], dbsession)

    def test_inactive_user_raises(self, svc, dbsession, make_user):
        user = make_user(email='inactive@example.com', is_active=False)
        tokens = svc.create_token(str(user.id), user.email)
        with pytest.raises(HTTPUnauthorized):
            svc.refresh_access_token(tokens['refresh_token'], dbsession)
