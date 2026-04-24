import { Link, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function Layout({ children }: { children: ReactNode }) {
  const { user, setToken } = useAuth()
  const navigate = useNavigate()

  function logout() {
    setToken(null)
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="font-semibold text-gray-800">Ritter</Link>
            <Link to="/settle" className="text-sm text-gray-500 hover:text-gray-800">Settle</Link>
            {user?.is_admin && (
              <Link to="/admin" className="text-sm text-gray-500 hover:text-gray-800">Admin</Link>
            )}
          </div>
          <div className="flex items-center gap-4">
            <Link to="/profile" className="text-sm text-gray-500 hover:text-gray-800">
              {user?.name}
            </Link>
            <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">
              Sign out
            </button>
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}
