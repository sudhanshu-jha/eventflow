import json
from datetime import datetime

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPOk, HTTPBadRequest, HTTPUnauthorized

from .graphql import schema
from .services.auth import AuthService
from .models.user import User
from .models.event import Event


@view_config(route_name='graphql', request_method='POST', renderer='json')
def graphql_view(request):
    """Handle GraphQL queries and mutations."""
    try:
        body = request.json_body
    except json.JSONDecodeError:
        return HTTPBadRequest(json_body={'error': 'Invalid JSON'})

    query = body.get('query')
    variables = body.get('variables', {})
    operation_name = body.get('operationName')

    if not query:
        return HTTPBadRequest(json_body={'error': 'Query is required'})

    # Build context
    context = {
        'request': request,
        'dbsession': request.dbsession,
        'settings': request.registry.settings,
        'user': None,
    }

    # Try to authenticate user (optional for some queries)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            auth_service = AuthService(request.registry.settings)
            context['user'] = auth_service.get_user_from_request(request)
        except Exception:
            pass  # Auth is optional for some operations

    # Execute GraphQL query
    result = schema.execute(
        query,
        variables=variables,
        operation_name=operation_name,
        context=context,
    )

    response_data = {}
    if result.data:
        response_data['data'] = result.data

    if result.errors:
        response_data['errors'] = [
            {'message': str(error)} for error in result.errors
        ]

    return response_data


@view_config(route_name='graphql', request_method='GET', renderer='json')
def graphql_playground(request):
    """Return GraphQL Playground HTML for GET requests."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset=utf-8/>
        <meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
        <title>GraphQL Playground</title>
        <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <link rel="shortcut icon" href="//cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
        <script src="//cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root">
            <style>
                body { background-color: rgb(23, 42, 58); font-family: Open Sans, sans-serif; height: 90vh; }
            </style>
        </div>
        <script>window.addEventListener('load', function (event) {
            GraphQLPlayground.init(document.getElementById('root'), { endpoint: '/graphql' })
        })</script>
    </body>
    </html>
    """
    return Response(html, content_type='text/html')


@view_config(route_name='graphql', request_method='OPTIONS')
def graphql_options(request):
    """Handle CORS preflight requests."""
    return HTTPOk()


@view_config(route_name='track', request_method='POST', renderer='json')
def track_event(request):
    """REST endpoint for tracking events (for client-side SDKs)."""
    try:
        body = request.json_body
    except json.JSONDecodeError:
        return HTTPBadRequest(json_body={'error': 'Invalid JSON'})

    # Get API key from header or body
    api_key = request.headers.get('X-API-Key') or body.get('api_key')
    if not api_key:
        return HTTPUnauthorized(json_body={'error': 'API key required'})

    # Find user by API key
    user = request.dbsession.query(User).filter(User.api_key == api_key).first()
    if not user:
        return HTTPUnauthorized(json_body={'error': 'Invalid API key'})

    if not user.is_active:
        return HTTPUnauthorized(json_body={'error': 'Account is deactivated'})

    # Validate required fields
    event_type = body.get('event_type', 'custom')
    event_name = body.get('event_name')
    if not event_name:
        return HTTPBadRequest(json_body={'error': 'event_name is required'})

    # Create event
    event = Event(
        user_id=user.id,
        event_type=event_type,
        event_name=event_name,
        properties=body.get('properties', {}),
        session_id=body.get('session_id'),
        url=body.get('url'),
        referrer=body.get('referrer'),
        user_agent=request.user_agent,
        ip_address=request.client_addr,
        timestamp=datetime.utcnow(),
        is_processed='pending',
    )
    request.dbsession.add(event)
    request.dbsession.flush()

    # Trigger async processing
    try:
        from .tasks.event_processing import process_event
        process_event.delay(str(event.id))
    except Exception:
        pass  # Celery may not be running

    return {
        'success': True,
        'event_id': str(event.id),
    }


@view_config(route_name='track', request_method='OPTIONS')
def track_options(request):
    """Handle CORS preflight for track endpoint."""
    return HTTPOk()


@view_config(route_name='health', request_method='GET', renderer='json')
def health_check(request):
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
    }
