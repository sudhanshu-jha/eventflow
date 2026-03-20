"""Integration tests for auth GraphQL mutations via schema.execute()."""
import pytest

from analytics.graphql import schema


REGISTER = '''
mutation Register($email: String!, $password: String!, $name: String) {
  register(email: $email, password: $password, name: $name) {
    success
    user { id email name apiKey }
    tokens { accessToken refreshToken tokenType expiresIn }
    error
  }
}
'''

LOGIN = '''
mutation Login($email: String!, $password: String!) {
  login(email: $email, password: $password) {
    success
    user { id email }
    tokens { accessToken refreshToken }
    error
  }
}
'''

REFRESH = '''
mutation RefreshToken($refreshToken: String!) {
  refreshToken(refreshToken: $refreshToken) {
    success
    tokens { accessToken refreshToken }
    error
  }
}
'''

ME = '''
query {
  me { id email name }
}
'''

UPDATE_PROFILE = '''
mutation UpdateProfile($name: String) {
  updateProfile(name: $name) {
    success
    user { id name }
    error
  }
}
'''

CHANGE_PASSWORD = '''
mutation ChangePassword($currentPassword: String!, $newPassword: String!) {
  changePassword(currentPassword: $currentPassword, newPassword: $newPassword) {
    success
    error
  }
}
'''


def execute(query, variables=None, context=None):
    return schema.execute(query, variables=variables or {}, context=context or {})


class TestRegister:
    def test_success(self, gql_context):
        result = execute(REGISTER, {'email': 'new@example.com', 'password': 'TestPass1!', 'name': 'New'}, gql_context)
        assert not result.errors
        data = result.data['register']
        assert data['success'] is True
        assert data['user']['email'] == 'new@example.com'
        assert data['tokens']['accessToken']
        assert data['tokens']['tokenType'] == 'Bearer'

    def test_duplicate_email(self, gql_context, make_user):
        make_user(email='dup@example.com')
        result = execute(REGISTER, {'email': 'dup@example.com', 'password': 'TestPass1!'}, gql_context)
        data = result.data['register']
        assert data['success'] is False
        assert 'already registered' in data['error']

    def test_weak_password_no_uppercase(self, gql_context):
        result = execute(REGISTER, {'email': 'weak@example.com', 'password': 'testpass1!'}, gql_context)
        data = result.data['register']
        assert data['success'] is False
        assert 'uppercase' in data['error']

    def test_weak_password_too_short(self, gql_context):
        result = execute(REGISTER, {'email': 'short@example.com', 'password': 'Ab1!'}, gql_context)
        data = result.data['register']
        assert data['success'] is False
        assert '8 characters' in data['error']

    def test_weak_password_no_digit_or_special(self, gql_context):
        result = execute(REGISTER, {'email': 'nodigit@example.com', 'password': 'TestPasswd'}, gql_context)
        data = result.data['register']
        assert data['success'] is False


class TestLogin:
    def test_success(self, gql_context, make_user):
        make_user(email='login@example.com', password='TestPass1!')
        result = execute(LOGIN, {'email': 'login@example.com', 'password': 'TestPass1!'}, gql_context)
        data = result.data['login']
        assert data['success'] is True
        assert data['tokens']['accessToken']

    def test_wrong_password(self, gql_context, make_user):
        make_user(email='wrongpw@example.com', password='TestPass1!')
        result = execute(LOGIN, {'email': 'wrongpw@example.com', 'password': 'WrongPass1!'}, gql_context)
        data = result.data['login']
        assert data['success'] is False
        assert 'Invalid email or password' in data['error']

    def test_unknown_email(self, gql_context):
        result = execute(LOGIN, {'email': 'nobody@example.com', 'password': 'TestPass1!'}, gql_context)
        data = result.data['login']
        assert data['success'] is False
        assert 'Invalid email or password' in data['error']

    def test_inactive_account(self, gql_context, make_user):
        make_user(email='inactive@example.com', password='TestPass1!', is_active=False)
        result = execute(LOGIN, {'email': 'inactive@example.com', 'password': 'TestPass1!'}, gql_context)
        data = result.data['login']
        assert data['success'] is False
        assert 'deactivated' in data['error']


class TestRefreshToken:
    def test_success(self, gql_context, make_user, auth_service):
        user = make_user(email='rtoken@example.com')
        tokens = auth_service.create_token(str(user.id), user.email)
        result = execute(REFRESH, {'refreshToken': tokens['refresh_token']}, gql_context)
        data = result.data['refreshToken']
        assert data['success'] is True
        assert data['tokens']['accessToken']

    def test_access_token_rejected(self, gql_context, make_user, auth_service):
        user = make_user(email='badtoken@example.com')
        tokens = auth_service.create_token(str(user.id), user.email)
        result = execute(REFRESH, {'refreshToken': tokens['access_token']}, gql_context)
        data = result.data['refreshToken']
        assert data['success'] is False

    def test_invalid_token_rejected(self, gql_context):
        result = execute(REFRESH, {'refreshToken': 'not.a.token'}, gql_context)
        data = result.data['refreshToken']
        assert data['success'] is False


class TestMeQuery:
    def test_authenticated_returns_user(self, gql_context, make_user):
        user = make_user(email='me@example.com')
        gql_context['user'] = user
        result = execute(ME, context=gql_context)
        assert result.data['me']['email'] == 'me@example.com'

    def test_unauthenticated_returns_none(self, gql_context):
        result = execute(ME, context=gql_context)
        assert result.data['me'] is None


class TestUpdateProfile:
    def test_success(self, gql_context, make_user):
        user = make_user(email='profile@example.com', name='Old Name')
        gql_context['user'] = user
        result = execute(UPDATE_PROFILE, {'name': 'New Name'}, gql_context)
        data = result.data['updateProfile']
        assert data['success'] is True
        assert data['user']['name'] == 'New Name'

    def test_unauthenticated(self, gql_context):
        result = execute(UPDATE_PROFILE, {'name': 'X'}, gql_context)
        data = result.data['updateProfile']
        assert data['success'] is False
        assert 'Authentication required' in data['error']


class TestChangePassword:
    def test_success(self, gql_context, make_user, auth_service):
        user = make_user(email='changepw@example.com', password='OldPass1!')
        gql_context['user'] = user
        result = execute(
            CHANGE_PASSWORD,
            {'currentPassword': 'OldPass1!', 'newPassword': 'NewPass2@'},
            gql_context,
        )
        data = result.data['changePassword']
        assert data['success'] is True
        assert auth_service.verify_password('NewPass2@', user.password_hash)

    def test_wrong_current_password(self, gql_context, make_user):
        user = make_user(email='wrongcurrent@example.com', password='OldPass1!')
        gql_context['user'] = user
        result = execute(
            CHANGE_PASSWORD,
            {'currentPassword': 'WrongPass1!', 'newPassword': 'NewPass2@'},
            gql_context,
        )
        data = result.data['changePassword']
        assert data['success'] is False
        assert 'incorrect' in data['error']

    def test_weak_new_password(self, gql_context, make_user):
        user = make_user(email='weaknew@example.com', password='OldPass1!')
        gql_context['user'] = user
        result = execute(
            CHANGE_PASSWORD,
            {'currentPassword': 'OldPass1!', 'newPassword': 'weakpassword'},
            gql_context,
        )
        data = result.data['changePassword']
        assert data['success'] is False

    def test_unauthenticated(self, gql_context):
        result = execute(
            CHANGE_PASSWORD,
            {'currentPassword': 'any', 'newPassword': 'NewPass1!'},
            gql_context,
        )
        data = result.data['changePassword']
        assert data['success'] is False
        assert 'Authentication required' in data['error']
