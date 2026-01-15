import graphene
from ...models.user import User
from ...services.auth import AuthService


class AuthPayload(graphene.ObjectType):
    access_token = graphene.String()
    refresh_token = graphene.String()
    token_type = graphene.String()
    expires_in = graphene.Int()


class UserType(graphene.ObjectType):
    id = graphene.ID()
    email = graphene.String()
    name = graphene.String()
    api_key = graphene.String()
    created_at = graphene.DateTime()
    is_active = graphene.Boolean()


class Register(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        name = graphene.String()

    success = graphene.Boolean()
    user = graphene.Field(UserType)
    tokens = graphene.Field(AuthPayload)
    error = graphene.String()

    def mutate(self, info, email, password, name=None):
        dbsession = info.context.get('dbsession')
        settings = info.context.get('settings')

        # Check if user exists
        existing = dbsession.query(User).filter(User.email == email).first()
        if existing:
            return Register(success=False, error='Email already registered')

        # Validate password
        if len(password) < 8:
            return Register(success=False, error='Password must be at least 8 characters')

        auth_service = AuthService(settings)

        # Create user
        user = User(
            email=email,
            password_hash=auth_service.hash_password(password),
            api_key=auth_service.generate_api_key(),
            name=name,
        )
        dbsession.add(user)
        dbsession.flush()

        # Generate tokens
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
    user = graphene.Field(UserType)
    tokens = graphene.Field(AuthPayload)
    error = graphene.String()

    def mutate(self, info, email, password):
        dbsession = info.context.get('dbsession')
        settings = info.context.get('settings')

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
        except Exception as e:
            return RefreshToken(success=False, error=str(e))
