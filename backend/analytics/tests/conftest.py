import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Disable rate limiting in tests by pointing to an unreachable Redis host.
# _check_rate_limit() catches connection errors and returns True (allow all).
os.environ['REDIS_URL'] = 'redis://localhost:1/99'

from analytics.models import Base

# Allow PostgreSQL-specific types (JSONB, UUID, ARRAY) to work with SQLite (tests only).
import uuid as uuid_module
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.dialects.postgresql import UUID as PGUUID

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: 'TEXT'
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: 'CHAR(36)'
SQLiteTypeCompiler.visit_ARRAY = lambda self, type_, **kw: 'TEXT'

# Override PGUUID bind/result processors so strings are stored/retrieved as-is in SQLite.
# NOTE: This patches the global PGUUID class for the entire pytest session. It is guarded
# by a dialect-name check so it only activates for SQLite connections, leaving any
# future PostgreSQL integration tests unaffected.
_orig_bind = PGUUID.bind_processor
_orig_result = PGUUID.result_processor


def _sqlite_uuid_bind(self, dialect):
    if dialect.name == 'sqlite':
        def process(value):
            if value is None:
                return None
            return str(value)
        return process
    return _orig_bind(self, dialect)


def _sqlite_uuid_result(self, dialect, coltype):
    if dialect.name == 'sqlite':
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid_module.UUID):
                return value
            return uuid_module.UUID(value)
        return process
    return _orig_result(self, dialect, coltype)


PGUUID.bind_processor = _sqlite_uuid_bind
PGUUID.result_processor = _sqlite_uuid_result

TEST_SETTINGS = {
    'jwt.secret': 'test-jwt-secret-key-minimum-32-bytes',
    'jwt.algorithm': 'HS256',
    'jwt.expiration': '3600',
    'sqlalchemy.url': 'sqlite:///:memory:',
    'tm.manager_hook': 'pyramid_tm.explicit_manager',
    'cors.origins': 'http://localhost:5173',
}


@pytest.fixture(scope='session')
def engine():
    """SQLite in-memory engine shared across the test session."""
    eng = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def dbsession(engine):
    """Per-test transactional session — rolled back after each test."""
    connection = engine.connect()
    trans = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def test_settings():
    return TEST_SETTINGS.copy()


@pytest.fixture
def auth_service(test_settings):
    from analytics.services.auth import AuthService
    return AuthService(test_settings)


@pytest.fixture
def make_user(dbsession, auth_service):
    """Factory fixture to create User instances in the test DB."""
    from analytics.models.user import User

    def _factory(email='test@example.com', password='TestPass1!', name='Test User', is_active=True):
        user = User(
            email=email,
            password_hash=auth_service.hash_password(password),
            api_key=auth_service.generate_api_key(),
            name=name,
            is_active=is_active,
        )
        dbsession.add(user)
        dbsession.flush()
        return user

    return _factory


@pytest.fixture
def gql_context(dbsession, test_settings):
    """Minimal GraphQL context dict for schema.execute() calls."""
    return {
        'dbsession': dbsession,
        'settings': test_settings,
        'request': None,
        'user': None,
    }


@pytest.fixture(scope='session')
def webtest_app(engine):
    """WebTest app backed by the same SQLite session-engine."""
    orig_db_url = os.environ.pop('DATABASE_URL', None)

    from webtest import TestApp
    from pyramid.config import Configurator
    import analytics

    # Wire Pyramid to use our test engine
    def custom_includeme(config):
        settings = config.get_settings()
        settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'
        config.include('pyramid_tm')
        from sqlalchemy.orm import sessionmaker
        import zope.sqlalchemy
        session_factory = sessionmaker()
        session_factory.configure(bind=engine)
        config.registry['dbsession_factory'] = session_factory
        config.add_request_method(
            lambda r: analytics.get_tm_session(session_factory, r.tm, request=r),
            'dbsession',
            reify=True,
        )

    with Configurator(settings=TEST_SETTINGS) as config:
        config.include('analytics.models')
        config.include(custom_includeme)
        config.add_route('graphql', '/graphql')
        config.add_route('track', '/api/track')
        config.add_route('health', '/health')
        config.add_subscriber(analytics.add_cors_headers, 'pyramid.events.NewResponse')
        config.scan('analytics.views')
        app = config.make_wsgi_app()

    if orig_db_url:
        os.environ['DATABASE_URL'] = orig_db_url

    return TestApp(app)
