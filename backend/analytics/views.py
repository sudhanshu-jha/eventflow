import json
import re
import logging
from datetime import datetime

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPOk, HTTPBadRequest, HTTPUnauthorized

from .graphql import schema
from .services.auth import AuthService
from .models.user import User
from .models.event import Event

logger = logging.getLogger(__name__)

# OpenTelemetry imports (optional - graceful fallback if not available)
try:
    from opentelemetry import trace
    from opentelemetry.trace import StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("OpenTelemetry not available, GraphQL tracing disabled")


def parse_graphql_operation(query):
    """Extract operation type and name from GraphQL query."""
    # Match operation type (query, mutation, subscription) and optional name
    pattern = r'^\s*(query|mutation|subscription)\s*(\w+)?'
    match = re.match(pattern, query.strip(), re.IGNORECASE)
    
    if match:
        op_type = match.group(1).lower()
        op_name = match.group(2)
        return op_type, op_name
    
    # Default to query if no explicit type (shorthand query syntax)
    return 'query', None


def extract_graphql_fields(query):
    """Extract top-level field names from GraphQL query."""
    # Simple regex to find field names after { 
    # This handles cases like: { events { ... } me { ... } }
    fields = re.findall(r'{\s*(\w+)', query)
    # Remove duplicates and common structural keywords
    fields = [f for f in fields if f not in ('query', 'mutation', 'subscription')]
    return list(dict.fromkeys(fields))[:5]  # Return first 5 unique fields


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

    # Parse GraphQL operation details
    op_type, parsed_op_name = parse_graphql_operation(query)
    effective_op_name = operation_name or parsed_op_name or 'anonymous'
    fields = extract_graphql_fields(query)

    # Create OpenTelemetry span for GraphQL operation
    span = None
    if OTEL_AVAILABLE:
        tracer = trace.get_tracer(__name__)
        span = tracer.start_span(
            f"graphql.{op_type}",
            attributes={
                "graphql.operation.type": op_type,
                "graphql.operation.name": effective_op_name,
                "graphql.document": query[:500],  # Truncate long queries
                "graphql.fields": ", ".join(fields),
            }
        )
        # Add variables (sanitized - don't include sensitive data)
        if variables:
            safe_vars = {k: '***' if 'password' in k.lower() or 'token' in k.lower() 
                        else v for k, v in variables.items()}
            span.set_attribute("graphql.variables", json.dumps(safe_vars)[:200])

    try:
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
                if span and context['user']:
                    span.set_attribute("user.id", str(context['user'].id))
                    span.set_attribute("user.email", context['user'].email)
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
            if span:
                span.set_attribute("graphql.response.has_data", True)

        if result.errors:
            response_data['errors'] = [
                {'message': str(error)} for error in result.errors
            ]
            if span:
                span.set_attribute("graphql.response.has_errors", True)
                span.set_attribute("graphql.errors.count", len(result.errors))
                # Record first error message
                span.set_attribute("graphql.errors.first", str(result.errors[0])[:200])
                span.set_status(StatusCode.ERROR, f"GraphQL errors: {len(result.errors)}")
        elif span:
            span.set_status(StatusCode.OK)

        return response_data

    except Exception as e:
        if span:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
        raise
    finally:
        if span:
            span.end()


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
    span = None
    if OTEL_AVAILABLE:
        tracer = trace.get_tracer(__name__)
        span = tracer.start_span("track_event")
    
    try:
        try:
            body = request.json_body
        except json.JSONDecodeError:
            if span:
                span.set_status(StatusCode.ERROR, "Invalid JSON")
            return HTTPBadRequest(json_body={'error': 'Invalid JSON'})

        # Get API key from header or body
        api_key = request.headers.get('X-API-Key') or body.get('api_key')
        if not api_key:
            if span:
                span.set_status(StatusCode.ERROR, "API key required")
            return HTTPUnauthorized(json_body={'error': 'API key required'})

        # Find user by API key
        user = request.dbsession.query(User).filter(User.api_key == api_key).first()
        if not user:
            if span:
                span.set_status(StatusCode.ERROR, "Invalid API key")
            return HTTPUnauthorized(json_body={'error': 'Invalid API key'})

        if not user.is_active:
            if span:
                span.set_status(StatusCode.ERROR, "Account deactivated")
            return HTTPUnauthorized(json_body={'error': 'Account is deactivated'})

        # Validate required fields
        event_type = body.get('event_type', 'custom')
        event_name = body.get('event_name')
        if not event_name:
            if span:
                span.set_status(StatusCode.ERROR, "event_name required")
            return HTTPBadRequest(json_body={'error': 'event_name is required'})

        # Add span attributes
        if span:
            span.set_attribute("event.type", event_type)
            span.set_attribute("event.name", event_name)
            span.set_attribute("event.url", body.get('url', ''))
            span.set_attribute("event.session_id", body.get('session_id', ''))
            span.set_attribute("user.id", str(user.id))

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

        if span:
            span.set_attribute("event.id", str(event.id))

        # Trigger async processing
        try:
            from .tasks.event_processing import process_event
            process_event.delay(str(event.id))
            if span:
                span.set_attribute("event.async_processing", True)
        except Exception:
            if span:
                span.set_attribute("event.async_processing", False)

        if span:
            span.set_status(StatusCode.OK)

        return {
            'success': True,
            'event_id': str(event.id),
        }

    except Exception as e:
        if span:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
        raise
    finally:
        if span:
            span.end()


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
