"""HTTP-level tests for /graphql, /api/track, and /health via WebTest."""
import json
import pytest

from analytics.services.auth import AuthService

SETTINGS = {
    'jwt.secret': 'test-jwt-secret-key-minimum-32-bytes',
    'jwt.algorithm': 'HS256',
    'jwt.expiration': '3600',
}


def gql(app, query, variables=None, token=None):
    """Helper to POST a GraphQL operation."""
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps({'query': query, 'variables': variables or {}})
    return app.post('/graphql', body, headers=headers)


class TestHealthEndpoint:
    def test_returns_healthy(self, webtest_app):
        resp = webtest_app.get('/health')
        assert resp.status_int == 200
        assert resp.json['status'] == 'healthy'


class TestGraphQLRegister:
    REGISTER_MUTATION = '''
    mutation Register($email: String!, $password: String!, $name: String) {
      register(email: $email, password: $password, name: $name) {
        success tokens { accessToken refreshToken } error
      }
    }
    '''

    def test_register_success(self, webtest_app):
        resp = gql(webtest_app, self.REGISTER_MUTATION, {
            'email': 'httptest@example.com',
            'password': 'TestPass1!',
            'name': 'HTTP Test',
        })
        assert resp.status_int == 200
        data = resp.json['data']['register']
        assert data['success'] is True
        assert data['tokens']['accessToken']

    def test_register_weak_password(self, webtest_app):
        resp = gql(webtest_app, self.REGISTER_MUTATION, {
            'email': 'weakhttp@example.com',
            'password': 'weakpass',
        })
        data = resp.json['data']['register']
        assert data['success'] is False


class TestGraphQLLogin:
    REGISTER = '''
    mutation Register($email: String!, $password: String!) {
      register(email: $email, password: $password) { success }
    }
    '''
    LOGIN = '''
    mutation Login($email: String!, $password: String!) {
      login(email: $email, password: $password) {
        success tokens { accessToken refreshToken } error
      }
    }
    '''

    def test_login_success(self, webtest_app):
        gql(webtest_app, self.REGISTER, {'email': 'loginhttp@example.com', 'password': 'TestPass1!'})
        resp = gql(webtest_app, self.LOGIN, {'email': 'loginhttp@example.com', 'password': 'TestPass1!'})
        data = resp.json['data']['login']
        assert data['success'] is True
        assert data['tokens']['accessToken']

    def test_login_wrong_password(self, webtest_app):
        gql(webtest_app, self.REGISTER, {'email': 'wrongpw@example.com', 'password': 'TestPass1!'})
        resp = gql(webtest_app, self.LOGIN, {'email': 'wrongpw@example.com', 'password': 'WrongPass9!'})
        data = resp.json['data']['login']
        assert data['success'] is False


class TestTrackEndpoint:
    REGISTER = '''
    mutation Register($email: String!, $password: String!) {
      register(email: $email, password: $password) { success error }
    }
    '''
    ME = '{ me { apiKey } }'
    LOGIN = '''
    mutation Login($email: String!, $password: String!) {
      login(email: $email, password: $password) {
        success tokens { accessToken } error
      }
    }
    '''

    def _get_api_key(self, webtest_app, email):
        gql(webtest_app, self.REGISTER, {'email': email, 'password': 'TestPass1!'})
        login_resp = gql(webtest_app, self.LOGIN, {'email': email, 'password': 'TestPass1!'})
        token = login_resp.json['data']['login']['tokens']['accessToken']
        me_resp = gql(webtest_app, self.ME, token=token)
        return me_resp.json['data']['me']['apiKey']

    def test_track_with_valid_key(self, webtest_app):
        api_key = self._get_api_key(webtest_app, 'trackuser@example.com')
        resp = webtest_app.post_json('/api/track', {
            'event_type': 'page_view',
            'event_name': 'home_page',
        }, headers={'X-API-Key': api_key})
        assert resp.status_int == 200
        assert resp.json['success'] is True

    def test_track_missing_key(self, webtest_app):
        resp = webtest_app.post_json('/api/track', {
            'event_type': 'page_view',
            'event_name': 'home',
        }, expect_errors=True)
        assert resp.status_int == 401

    def test_track_invalid_key(self, webtest_app):
        resp = webtest_app.post_json('/api/track', {
            'event_name': 'home',
        }, headers={'X-API-Key': 'invalidkey'}, expect_errors=True)
        assert resp.status_int == 401

    def test_track_missing_event_name(self, webtest_app):
        api_key = self._get_api_key(webtest_app, 'tracknoname@example.com')
        resp = webtest_app.post_json('/api/track', {
            'event_type': 'page_view',
        }, headers={'X-API-Key': api_key}, expect_errors=True)
        assert resp.status_int == 400
