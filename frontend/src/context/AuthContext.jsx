import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@apollo/client'
import { LOGIN, REGISTER, REFRESH_TOKEN } from '../graphql/mutations'
import { GET_ME } from '../graphql/queries'
import { setAccessToken, clearAccessToken } from '../graphql/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // Tracks whether we currently hold an in-memory access token.
  // Controls the skip flag on GET_ME so we only query once we're authenticated.
  const [hasToken, setHasToken] = useState(false)
  const navigate = useNavigate()

  const [loginMutation] = useMutation(LOGIN)
  const [registerMutation] = useMutation(REGISTER)
  const [refreshTokenMutation] = useMutation(REFRESH_TOKEN)

  const storeTokens = useCallback((tokens) => {
    // Access token lives only in memory — never in localStorage.
    setAccessToken(tokens.accessToken)
    setHasToken(true)
    localStorage.setItem('refreshToken', tokens.refreshToken)
    localStorage.setItem('tokenExpiresAt', String(Date.now() + tokens.expiresIn * 1000))
  }, [])

  const clearTokens = useCallback(() => {
    clearAccessToken()
    setHasToken(false)
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('tokenExpiresAt')
  }, [])

  // On mount: if a refresh token is persisted from a previous session, exchange it
  // for a new access token so the user stays logged in across page reloads.
  useEffect(() => {
    const storedRefresh = localStorage.getItem('refreshToken')
    if (!storedRefresh) {
      setLoading(false)
      return
    }
    refreshTokenMutation({ variables: { refreshToken: storedRefresh } })
      .then(({ data }) => {
        if (data?.refreshToken?.success) {
          storeTokens(data.refreshToken.tokens)
          // loading=false is set by GET_ME's onCompleted / onError below
        } else {
          clearTokens()
          setLoading(false)
        }
      })
      .catch(() => {
        clearTokens()
        setLoading(false)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps — intentional mount-only

  // Fetch the current user profile once we have a valid access token.
  const { refetch: refetchMe } = useQuery(GET_ME, {
    skip: !hasToken,
    onCompleted: (data) => {
      if (data?.me) setUser(data.me)
      setLoading(false)
    },
    onError: () => {
      clearTokens()
      setUser(null)
      setLoading(false)
    },
  })

  const refreshToken = useCallback(async () => {
    const token = localStorage.getItem('refreshToken')
    if (!token) return false

    try {
      const { data } = await refreshTokenMutation({ variables: { refreshToken: token } })
      if (data?.refreshToken?.success) {
        storeTokens(data.refreshToken.tokens)
        return true
      }
    } catch (_err) {
      // Refresh failure is expected when the refresh token is expired; log server-side.
    }

    clearTokens()
    setUser(null)
    navigate('/login')
    return false
  }, [refreshTokenMutation, storeTokens, clearTokens, navigate])

  // Schedule a proactive token refresh 5 minutes before the access token expires.
  useEffect(() => {
    const expiresAt = parseInt(localStorage.getItem('tokenExpiresAt') || '0', 10)
    if (!expiresAt) return

    const msUntilRefresh = expiresAt - Date.now() - 5 * 60 * 1000
    if (msUntilRefresh <= 0) return

    const timer = setTimeout(refreshToken, msUntilRefresh)
    return () => clearTimeout(timer)
  }, [user, refreshToken])

  const login = async (email, password) => {
    const { data } = await loginMutation({ variables: { email, password } })
    if (data?.login?.success) {
      storeTokens(data.login.tokens)
      setUser(data.login.user)
      return { success: true }
    }
    return { success: false, error: data?.login?.error || 'Login failed' }
  }

  const register = async (email, password, name) => {
    const { data } = await registerMutation({ variables: { email, password, name } })
    if (data?.register?.success) {
      storeTokens(data.register.tokens)
      setUser(data.register.user)
      return { success: true }
    }
    return { success: false, error: data?.register?.error || 'Registration failed' }
  }

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    navigate('/login')
  }, [clearTokens, navigate])

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    refreshToken,
    refetchMe,
    isAuthenticated: !!user,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
