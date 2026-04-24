import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { jwtDecode } from 'jwt-decode'
import { getUser } from '../api/users'
import type { User } from '../types'

interface AuthCtx {
  user: User | null
  token: string | null
  setToken: (t: string | null) => void
  setUser: (u: User) => void
  loading: boolean
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  setToken: () => {},
  setUser: () => {},
  loading: true,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(localStorage.getItem('token'))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  function setToken(t: string | null) {
    if (t) localStorage.setItem('token', t)
    else localStorage.removeItem('token')
    setTokenState(t)
  }

  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    const decoded = jwtDecode<{ sub: string }>(token)
    const userId = parseInt(decoded.sub)
    getUser(userId)
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <AuthContext.Provider value={{ user, token, setToken, setUser, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
