import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Terminal, Cpu } from 'lucide-react'

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-300 p-4">
        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-xl bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center animate-pulse">
            <Cpu className="w-8 h-8 text-cyan-400 animate-spin" style={{ animationDuration: '6s' }} />
          </div>
          <div className="absolute -inset-1 rounded-xl bg-cyan-500/20 blur-md -z-10 animate-pulse"></div>
        </div>
        <div className="flex items-center gap-2 text-cyan-400 font-mono text-sm tracking-wider uppercase">
          <Terminal className="w-4 h-4 animate-bounce" />
          <span>Authenticating SRE Session...</span>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-mono">Syncing cluster security context & RBAC tokens</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}

export default ProtectedRoute
