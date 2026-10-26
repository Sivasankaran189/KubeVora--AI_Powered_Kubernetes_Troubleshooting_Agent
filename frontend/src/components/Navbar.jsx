import React, { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  Cpu,
  Activity,
  LogOut,
  User,
  History,
  LayoutDashboard,
  Server
} from 'lucide-react'
import client from '../api/client'

export const Navbar = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [clusterInfo, setClusterInfo] = useState({
    name: 'kind-kubevora',
    connected: true,
    latencyMs: 12,
  })

  useEffect(() => {
    let isMounted = true
    const checkCluster = async () => {
      try {
        const t0 = performance.now()
        await client.get('/health')
        const latency = Math.round(performance.now() - t0)
        if (isMounted) {
          setClusterInfo(prev => ({
            ...prev,
            connected: true,
            latencyMs: latency || 10,
          }))
        }
      } catch {
        if (isMounted) {
          setClusterInfo(prev => ({ ...prev, connected: false }))
        }
      }
    }
    checkCluster()
    const interval = setInterval(checkCluster, 30000)
    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isDashboard = location.pathname === '/dashboard' || location.pathname === '/'
  const isHistory = location.pathname === '/history'

  return (
    <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-40 text-slate-800 shadow-xs">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand & Logo */}
        <div className="flex items-center gap-6">
          <Link to="/dashboard" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-md shadow-indigo-500/20 ring-1 ring-black/5">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight text-slate-900 font-display">KubeVora</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  AI SRE
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block font-medium">Kubernetes Troubleshooting Agent</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="flex items-center gap-2 ml-4">
            <Link
              to="/dashboard"
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                isDashboard
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Operations Console</span>
            </Link>
            <Link
              to="/history"
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                isHistory
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Incident History</span>
            </Link>
          </nav>
        </div>

        {/* Right Status & Profile */}
        <div className="flex items-center gap-4">
          {/* Cluster Status Badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
            <span className={`w-2 h-2 rounded-full ${clusterInfo.connected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-slate-500">Live Agent:</span>
            <span className="font-mono font-semibold text-slate-800">{clusterInfo.name}</span>
            <span className="text-[10px] text-slate-400 font-mono">({clusterInfo.latencyMs}ms)</span>
          </div>

          {/* User profile & Logout */}
          <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
            <div className="flex items-center gap-2 text-xs">
              <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 font-semibold">
                <User className="w-3.5 h-3.5" />
              </div>
              <span className="font-semibold text-slate-700 hidden sm:inline">{user?.username || 'admin_sre'}</span>
            </div>

            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Navbar
