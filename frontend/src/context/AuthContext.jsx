import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@apollo/client'
import { LOGIN, REGISTER, REFRESH_TOKEN } from '../graphql/mutations'
import { GET_ME } from '../graphql/queries'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const { data: meData, refetch: refetchMe } = useQuery(GET_ME, {
    skip: !localStorage.getItem('accessToken'),
    onCompleted: (data) => {
      if (data?.me) {
        setUser(data.me)
      }
      setLoading(false)
    },
    onError: () => {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setLoading(false)
    },
  })

  const [loginMutation] = useMutation(LOGIN)
  const [registerMutation] = useMutation(REGISTER)
  const [refreshTokenMutation] = useMutation(REFRESH_TOKEN)

  useEffect(() => {
    if (!localStorage.getItem('accessToken')) {
      setLoading(false)
    }
  }, [])

  const login = async (email, password) => {
    const { data } = await loginMutation({
      variables: { email, password },
    })

    if (data?.login?.success) {
      localStorage.setItem('accessToken', data.login.tokens.accessToken)
      localStorage.setItem('refreshToken', data.login.tokens.refreshToken)
      setUser(data.login.user)
      return { success: true }
    }

    return { success: false, error: data?.login?.error || 'Login failed' }
  }

  const register = async (email, password, name) => {
    const { data } = await registerMutation({
      variables: { email, password, name },
    })

    if (data?.register?.success) {
      localStorage.setItem('accessToken', data.register.tokens.accessToken)
      localStorage.setItem('refreshToken', data.register.tokens.refreshToken)
      setUser(data.register.user)
      return { success: true }
    }

    return { success: false, error: data?.register?.error || 'Registration failed' }
  }

  const logout = () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    setUser(null)
    navigate('/login')
  }

  const refreshToken = async () => {
    const token = localStorage.getItem('refreshToken')
    if (!token) return false

    try {
      const { data } = await refreshTokenMutation({
        variables: { refreshToken: token },
      })

      if (data?.refreshToken?.success) {
        localStorage.setItem('accessToken', data.refreshToken.tokens.accessToken)
        localStorage.setItem('refreshToken', data.refreshToken.tokens.refreshToken)
        return true
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
    }

    logout()
    return false
  }

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
