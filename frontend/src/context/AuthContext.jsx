import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import client from '../api/client'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('kubevora_user')
    try {
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('kubevora_token'))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Verify and hydrate current user session on mount
  const checkAuth = useCallback(async () => {
    const storedToken = localStorage.getItem('kubevora_token')
    if (!storedToken) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const response = await client.get('/auth/me')
      setUser(response.data)
      localStorage.setItem('kubevora_user', JSON.stringify(response.data))
    } catch (err) {
      console.warn('Session verification failed:', err?.message)
      localStorage.removeItem('kubevora_token')
      localStorage.removeItem('kubevora_user')
      setUser(null)
      setToken(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (usernameOrEmail, password) => {
    setError(null)
    try {
      const response = await client.post('/auth/login', {
        username_or_email: usernameOrEmail,
        password: password,
      })

      const { access_token, user: loggedUser } = response.data
      localStorage.setItem('kubevora_token', access_token)
      localStorage.setItem('kubevora_user', JSON.stringify(loggedUser))
      setToken(access_token)
      setUser(loggedUser)
      return { success: true, user: loggedUser }
    } catch (err) {
      const message = err.response?.data?.detail || 'Authentication failed. Please verify credentials.'
      setError(message)
      return { success: false, error: message }
    }
  }

  const register = async (userData) => {
    setError(null)
    try {
      const response = await client.post('/auth/register', userData)
      // Automatically log in after registration
      return await login(userData.username, userData.password)
    } catch (err) {
      const message = err.response?.data?.detail || 'Registration failed.'
      setError(message)
      return { success: false, error: message }
    }
  }

  const logout = () => {
    localStorage.removeItem('kubevora_token')
    localStorage.removeItem('kubevora_user')
    setToken(null)
    setUser(null)
    setError(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        error,
        isAuthenticated: !!token && !!user,
        login,
        register,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
