import { ApolloClient, InMemoryCache, createHttpLink, from, Observable } from '@apollo/client'
import { setContext } from '@apollo/client/link/context'
import { onError } from '@apollo/client/link/error'

const httpLink = createHttpLink({
  uri: '/graphql',
})

// In-memory access token storage — never written to localStorage.
// Access tokens stored in localStorage are readable by any JavaScript on the page
// (XSS, extensions, third-party scripts). Keeping them in memory means they are
// lost on page reload, but the refresh token in localStorage will restore the
// session transparently via AuthContext's mount effect.
let _accessToken = null

export function setAccessToken(token) {
  _accessToken = token
}

export function clearAccessToken() {
  _accessToken = null
}

const authLink = setContext((_, { headers }) => {
  return {
    headers: {
      ...headers,
      authorization: _accessToken ? `Bearer ${_accessToken}` : '',
    },
  }
})

// Serializes concurrent 401-triggered refreshes into a single in-flight request.
let isRefreshing = false
let pendingQueue = []

function drainQueue(token) {
  pendingQueue.forEach(({ resolve }) => resolve(token))
  pendingQueue = []
}

function rejectQueue(error) {
  pendingQueue.forEach(({ reject }) => reject(error))
  pendingQueue = []
}

function silentRefresh() {
  const refreshToken = localStorage.getItem('refreshToken')
  if (!refreshToken) return Promise.reject(new Error('No refresh token'))

  return fetch('/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `mutation RefreshToken($refreshToken: String!) {
        refreshToken(refreshToken: $refreshToken) {
          success tokens { accessToken refreshToken expiresIn } error
        }
      }`,
      variables: { refreshToken },
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      const result = data?.data?.refreshToken
      if (result?.success) {
        _accessToken = result.tokens.accessToken
        localStorage.setItem('refreshToken', result.tokens.refreshToken)
        if (result.tokens.expiresIn) {
          localStorage.setItem('tokenExpiresAt', String(Date.now() + result.tokens.expiresIn * 1000))
        }
        return result.tokens.accessToken
      }
      throw new Error(result?.error || 'Token refresh failed')
    })
}

const errorLink = onError(({ networkError, operation, forward }) => {
  if (networkError?.statusCode === 401) {
    return new Observable((observer) => {
      if (isRefreshing) {
        pendingQueue.push({
          resolve: (token) => {
            operation.setContext(({ headers = {} }) => ({
              headers: { ...headers, authorization: `Bearer ${token}` },
            }))
            forward(operation).subscribe(observer)
          },
          reject: (err) => observer.error(err),
        })
        return
      }

      isRefreshing = true
      silentRefresh()
        .then((token) => {
          isRefreshing = false
          drainQueue(token)
          operation.setContext(({ headers = {} }) => ({
            headers: { ...headers, authorization: `Bearer ${token}` },
          }))
          forward(operation).subscribe(observer)
        })
        .catch((err) => {
          isRefreshing = false
          rejectQueue(err)
          _accessToken = null
          localStorage.removeItem('refreshToken')
          localStorage.removeItem('tokenExpiresAt')
          window.location.href = '/login'
          observer.error(err)
        })
    })
  }
})

export const client = new ApolloClient({
  link: from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
    },
  },
})
