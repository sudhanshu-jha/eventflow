import os
import threading
import graphene
from pyramid.httpexceptions import HTTPUnauthorized

from ...models.user import User
from ...services.auth import AuthService


class AuthPayload(graphene.ObjectType):
    access_token = graphene.String()
    refresh_token = graphene.String()
    token_type = graphene.String()
    expires_in = graphene.Int()


# Module-level cached Redis client — reuses the connection pool across requests.
_redis_client = None
_redis_lock = threading.Lock()


def _get_redis():
    global _redis_client
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                import redis as redis_lib
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6380/0')
                _redis_client = redis_lib.from_url(redis_url, socket_connect_timeout=1)
    return _redis_client


def _check_rate_limit(key: str) -> bool:
    """Returns True if request is allowed. Degrades gracefully if Redis unavailable."""
    try:
        from ...services.auth import RateLimiter
        return RateLimiter(_get_redis()).is_allowed(key)
    except Exception:
        return True


class Register(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        name = graphene.String()

    success = graphene.Boolean()
    user = graphene.Field('analytics.graphql.queries.UserType')
    tokens = graphene.Field(AuthPayload)
    error = graphene.String()

    def mutate(self, info, email, password, name=None):
        from ..queries import UserType

        dbsession = info.context.get('dbsession')
        settings = info.context.get('settings')
        request = info.context.get('request')

        if request:
            ip = getattr(request, 'remote_addr', None) or 'unknown'
            if not _check_rate_limit(f'rate_limit:register:{ip}'):
                return Register(success=False, error='Too many registration attempts, please try again later')

        existing = dbsession.query(User).filter(User.email == email).first()
        if existing:
            return Register(success=False, error='Email already registered')

        auth_service = AuthService(settings)

        pw_error = auth_service.validate_password_strength(password)
        if pw_error:
            return Register(success=False, error=pw_error)

        user = User(
            email=email,
            password_hash=auth_service.hash_password(password),
            api_key=auth_service.generate_api_key(),
            name=name,
        )
        dbsession.add(user)
        dbsession.flush()

        tokens = auth_service.create_token(str(user.id), user.email)

        return Register(
            success=True,
            user=UserType(
                id=str(user.id),
                email=user.email,
                name=user.name,
                api_key=user.api_key,
                created_at=user.created_at,
                is_active=user.is_active,
            ),
            tokens=AuthPayload(
                access_token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                token_type=tokens['token_type'],
                expires_in=tokens['expires_in'],
            )
        )


class Login(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    success = graphene.Boolean()
    user = graphene.Field('analytics.graphql.queries.UserType')
    tokens = graphene.Field(AuthPayload)
    error = graphene.String()

    def mutate(self, info, email, password):
        from ..queries import UserType

        dbsession = info.context.get('dbsession')
        settings = info.context.get('settings')
        request = info.context.get('request')

        if request:
            ip = getattr(request, 'remote_addr', None) or 'unknown'
            if not _check_rate_limit(f'rate_limit:login:{ip}:{email}'):
                return Login(success=False, error='Too many login attempts, please try again later')

        user = dbsession.query(User).filter(User.email == email).first()
        if not user:
            return Login(success=False, error='Invalid email or password')

        auth_service = AuthService(settings)

        if not auth_service.verify_password(password, user.password_hash):
            return Login(success=False, error='Invalid email or password')

        if not user.is_active:
            return Login(success=False, error='Account is deactivated')

        tokens = auth_service.create_token(str(user.id), user.email)

        return Login(
            success=True,
            user=UserType(
                id=str(user.id),
                email=user.email,
                name=user.name,
                api_key=user.api_key,
                created_at=user.created_at,
                is_active=user.is_active,
            ),
            tokens=AuthPayload(
                access_token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                token_type=tokens['token_type'],
                expires_in=tokens['expires_in'],
            )
        )


class RefreshToken(graphene.Mutation):
    class Arguments:
        refresh_token = graphene.String(required=True)

    success = graphene.Boolean()
    tokens = graphene.Field(AuthPayload)
    error = graphene.String()

    def mutate(self, info, refresh_token):
        dbsession = info.context.get('dbsession')
        settings = info.context.get('settings')

        auth_service = AuthService(settings)

        try:
            tokens = auth_service.refresh_access_token(refresh_token, dbsession)
            return RefreshToken(
                success=True,
                tokens=AuthPayload(
                    access_token=tokens['access_token'],
                    refresh_token=tokens['refresh_token'],
                    token_type=tokens['token_type'],
                    expires_in=tokens['expires_in'],
                )
            )
        except HTTPUnauthorized as e:
            body = getattr(e, 'json_body', {}) or {}
            return RefreshToken(success=False, error=body.get('error', 'Invalid or expired refresh token'))
        except Exception:
            return RefreshToken(success=False, error='Token refresh failed')


class UpdateProfile(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    success = graphene.Boolean()
    user = graphene.Field('analytics.graphql.queries.UserType')
    error = graphene.String()

    def mutate(self, info, name=None):
        from ..queries import UserType

        user = info.context.get('user')
        if not user:
            return UpdateProfile(success=False, error='Authentication required')

        if name is not None:
            if not name.strip():
                return UpdateProfile(success=False, error='Name cannot be empty')
            user.name = name

        dbsession = info.context.get('dbsession')
        dbsession.flush()

        return UpdateProfile(
            success=True,
            user=UserType(
                id=str(user.id),
                email=user.email,
                name=user.name,
                api_key=user.api_key,
                created_at=user.created_at,
                is_active=user.is_active,
            )
        )


class ChangePassword(graphene.Mutation):
    class Arguments:
        current_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    success = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, current_password, new_password):
        user = info.context.get('user')
        if not user:
            return ChangePassword(success=False, error='Authentication required')

        settings = info.context.get('settings')
        auth_service = AuthService(settings)

        if not auth_service.verify_password(current_password, user.password_hash):
            return ChangePassword(success=False, error='Current password is incorrect')

        pw_error = auth_service.validate_password_strength(new_password)
        if pw_error:
            return ChangePassword(success=False, error=pw_error)

        user.password_hash = auth_service.hash_password(new_password)
        dbsession = info.context.get('dbsession')
        dbsession.flush()

        return ChangePassword(success=True)
