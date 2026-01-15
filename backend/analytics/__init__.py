import os
from pyramid.config import Configurator
from sqlalchemy import create_engine, engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import configure_mappers
import zope.sqlalchemy

from .models import Base


def get_engine(settings, prefix='sqlalchemy.'):
    # Use DATABASE_URL env var if available (for Docker)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return create_engine(database_url)
    return engine_from_config(settings, prefix)


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


def get_tm_session(session_factory, transaction_manager, request=None):
    dbsession = session_factory()
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    if request is not None:
        def cleanup(request):
            dbsession.close()
        request.add_finished_callback(cleanup)
    return dbsession


def includeme(config):
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    config.include('pyramid_tm')

    session_factory = get_session_factory(get_engine(settings))
    config.registry['dbsession_factory'] = session_factory

    config.add_request_method(
        lambda r: get_tm_session(session_factory, r.tm, request=r),
        'dbsession',
        reify=True
    )


def main(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    with Configurator(settings=settings) as config:
        # Include database
        config.include('.models')
        config.include(includeme)

        # Configure routes
        config.add_route('graphql', '/graphql')
        config.add_route('track', '/api/track')
        config.add_route('health', '/health')

        # Add CORS
        config.add_subscriber(add_cors_headers, 'pyramid.events.NewResponse')

        # Scan for views
        config.scan('.views')

    return config.make_wsgi_app()


def add_cors_headers(event):
    """Add CORS headers to responses."""
    request = event.request
    response = event.response

    settings = request.registry.settings
    origins = settings.get('cors.origins', 'http://localhost:5173')

    response.headers['Access-Control-Allow-Origin'] = origins
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
