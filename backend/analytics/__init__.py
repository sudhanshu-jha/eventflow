import os
import logging
import atexit
from pyramid.config import Configurator
from sqlalchemy import create_engine, engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import configure_mappers
import zope.sqlalchemy

from .models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global engine reference for telemetry
_engine = None


def get_engine(settings, prefix='sqlalchemy.'):
    global _engine
    # Use DATABASE_URL env var if available (for Docker)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        _engine = create_engine(database_url)
    else:
        _engine = engine_from_config(settings, prefix)
    return _engine


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


def init_opentelemetry(engine=None):
    """Initialize OpenTelemetry for the application."""
    try:
        from .telemetry import init_telemetry, shutdown_telemetry
        
        # Initialize telemetry with SQLAlchemy engine
        init_telemetry(engine=engine, enable_celery=False)
        
        # Register shutdown handler
        atexit.register(shutdown_telemetry)
        
        logger.info("OpenTelemetry initialized successfully")
        return True
    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        return False


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

    # Create the WSGI app
    app = config.make_wsgi_app()
    
    # Initialize OpenTelemetry
    otel_enabled = init_opentelemetry(engine=_engine)
    
    # Wrap with OpenTelemetry middleware if enabled
    if otel_enabled:
        try:
            from .telemetry import get_wsgi_middleware
            app = get_wsgi_middleware(app)
            logger.info("WSGI app wrapped with OpenTelemetry middleware")
        except Exception as e:
            logger.warning(f"Failed to wrap app with OTEL middleware: {e}")
    
    return app


def add_cors_headers(event):
    """Add CORS headers to responses."""
    request = event.request
    response = event.response

    settings = request.registry.settings
    allowed_origins = settings.get('cors.origins', 'http://localhost:5173')
    
    # Parse comma-separated origins into a list
    allowed_origins_list = [origin.strip() for origin in allowed_origins.split(',')]
    
    # Get the request origin
    request_origin = request.headers.get('Origin', '')
    
    # Only set the origin if it's in our allowed list
    if request_origin in allowed_origins_list:
        response.headers['Access-Control-Allow-Origin'] = request_origin
    elif allowed_origins_list:
        # Default to first allowed origin for non-browser requests
        response.headers['Access-Control-Allow-Origin'] = allowed_origins_list[0]

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, traceparent, tracestate'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    # Expose trace headers for frontend correlation
    response.headers['Access-Control-Expose-Headers'] = 'traceparent, tracestate'
