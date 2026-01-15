import secrets
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import jwt
from pyramid.httpexceptions import HTTPUnauthorized

from ..models.user import User


class AuthService:
    def __init__(self, settings):
        self.secret = settings.get('jwt.secret', 'default-secret-change-me')
        self.algorithm = settings.get('jwt.algorithm', 'HS256')
        self.expiration = int(settings.get('jwt.expiration', 3600))

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def generate_api_key(self) -> str:
        """Generate a unique API key."""
        return secrets.token_hex(32)

    def create_token(self, user_id: str, email: str) -> dict:
        """Create JWT access and refresh tokens."""
        now = datetime.utcnow()

        # Access token (shorter lived)
        access_payload = {
            'sub': str(user_id),
            'email': email,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(seconds=self.expiration),
        }
        access_token = jwt.encode(access_payload, self.secret, algorithm=self.algorithm)

        # Refresh token (longer lived)
        refresh_payload = {
            'sub': str(user_id),
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7),
        }
        refresh_token = jwt.encode(refresh_payload, self.secret, algorithm=self.algorithm)

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.expiration,
        }

    def decode_token(self, token: str) -> dict:
        """Decode and verify a JWT token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPUnauthorized(json_body={'error': 'Token has expired'})
        except jwt.InvalidTokenError:
            raise HTTPUnauthorized(json_body={'error': 'Invalid token'})

    def get_user_from_request(self, request) -> User:
        """Extract and validate user from request Authorization header."""
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            raise HTTPUnauthorized(json_body={'error': 'Missing or invalid Authorization header'})

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        payload = self.decode_token(token)

        if payload.get('type') != 'access':
            raise HTTPUnauthorized(json_body={'error': 'Invalid token type'})

        user_id = payload.get('sub')
        user = request.dbsession.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPUnauthorized(json_body={'error': 'User not found'})

        if not user.is_active:
            raise HTTPUnauthorized(json_body={'error': 'User is inactive'})

        return user

    def refresh_access_token(self, refresh_token: str, dbsession) -> dict:
        """Generate a new access token using a refresh token."""
        payload = self.decode_token(refresh_token)

        if payload.get('type') != 'refresh':
            raise HTTPUnauthorized(json_body={'error': 'Invalid token type'})

        user_id = payload.get('sub')
        user = dbsession.query(User).filter(User.id == user_id).first()

        if not user or not user.is_active:
            raise HTTPUnauthorized(json_body={'error': 'User not found or inactive'})

        return self.create_token(str(user.id), user.email)


def require_auth(view_callable):
    """Decorator to require authentication for a view."""
    @wraps(view_callable)
    def wrapper(request):
        settings = request.registry.settings
        auth_service = AuthService(settings)
        request.current_user = auth_service.get_user_from_request(request)
        return view_callable(request)
    return wrapper


def get_auth_service(request):
    """Get the auth service from the request registry."""
    settings = request.registry.settings
    return AuthService(settings)
