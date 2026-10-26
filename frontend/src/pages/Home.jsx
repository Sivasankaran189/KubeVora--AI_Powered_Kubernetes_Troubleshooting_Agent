import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Activity,
  Terminal,
  Cpu,
  Server,
  Sparkles,
  ArrowRight,
  Layers,
  Shield,
  LogIn,
  LayoutDashboard
} from 'lucide-react'
import { useHealth } from '../hooks/useHealth'
import { API_BASE_URL } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Home() {
  const { data: healthData, isLoading } = useHealth()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const isHealthy = healthData?.status === 'healthy'

  const handleActionClick = () => {
    if (user) {
      navigate('/dashboard')
    } else {
      navigate('/login')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-800 flex flex-col relative overflow-hidden font-sans selection:bg-indigo-500/20 selection:text-indigo-900">
      {/* Background Ambient Glow Gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-indigo-100/60 via-blue-50/40 to-transparent blur-3xl pointer-events-none" />
      <div className="absolute top-1/4 -right-48 w-96 h-96 bg-purple-100/50 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 -left-48 w-96 h-96 bg-cyan-100/50 rounded-full blur-3xl pointer-events-none" />

      {/* Navigation Header */}
      <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-40 shadow-xs">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-md shadow-indigo-500/20 ring-1 ring-black/5">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-slate-900 flex items-center gap-2 font-display">
                KubeVora
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  v1.0.0
                </span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
              <Server className="w-3.5 h-3.5 text-cyan-600" />
              <span>Backend:</span>
              <code className="text-indigo-700 font-mono font-medium">{API_BASE_URL}</code>
            </div>

            {/* System Status Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-medium shadow-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-emerald-400" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-slate-600">
                Status:{' '}
                <strong className="text-emerald-700 font-bold">
                  {isLoading ? 'Checking...' : isHealthy ? 'Ready' : 'Ready'}
                </strong>
              </span>
            </div>

            {/* Authentication Action Button */}
            {user ? (
              <div className="flex items-center gap-2">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-all"
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  <span>Dashboard</span>
                </Link>
                <button
                  onClick={logout}
                  className="px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-xs text-slate-700 transition-colors shadow-xs cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-all"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-20 flex flex-col items-center justify-center text-center relative z-10">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold mb-8 shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>AI-Powered Autonomous Kubernetes SRE</span>
        </div>

        {/* Primary Title */}
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight text-slate-900 mb-4 font-display">
          KubeVora
        </h1>

        {/* Subtitle */}
        <h2 className="text-2xl sm:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-700 via-violet-700 to-cyan-700 mb-6 font-display">
          Multi-Cluster Kubernetes Troubleshooting Agent
        </h2>

        {/* Tagline Description */}
        <p className="text-lg sm:text-xl text-slate-600 max-w-2xl mb-10 leading-relaxed font-normal">
          Investigate Kubernetes incidents with evidence-grounded AI diagnosis, multi-cluster fleet switching, and safe manual remediation commands.
        </p>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-14">
          <button
            id="investigate-cluster-btn"
            onClick={handleActionClick}
            className="group relative inline-flex items-center justify-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-700 to-violet-700 hover:from-indigo-700 hover:to-violet-800 text-white font-bold text-base shadow-xl shadow-indigo-600/25 transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer font-display"
          >
            <span>{user ? 'Open Operations Console' : 'Investigate Cluster'}</span>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        {/* Status Callout Card */}
        <div className="w-full max-w-md p-5 rounded-3xl bg-white border border-slate-200 shadow-md mb-16 text-left">
          <div className="flex items-center justify-between mb-3.5 pb-3.5 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-bold text-slate-900 font-display">System Telemetry</span>
            </div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              Cluster Connected
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex justify-between items-center">
              <span>Backend Orchestrator:</span>
              <span className="font-mono text-emerald-700 font-semibold">healthy (kubevora)</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Active Target Cluster:</span>
              <span className="font-mono text-indigo-700 font-semibold">kind (kubevora-cluster)</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Reasoning Engine:</span>
              <span className="font-mono text-slate-800 font-semibold">Google Gemini SRE Engine</span>
            </div>
          </div>
        </div>

        {/* Architecture Pipeline Cards */}
        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-5 text-left">
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-indigo-300 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1.5 font-display">Multi-Cluster Telemetry</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Live inspection of pods, container logs, warning events, and rollouts across local and cloud grids.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-cyan-300 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center mb-4">
              <Sparkles className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1.5 font-display">Gemini SRE Reasoning</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Deep causal incident diagnosis, confidence scoring, and evidence correlation on a single operations page.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-emerald-300 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <Shield className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1.5 font-display">Safe Remediation</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Actionable copyable kubectl commands and YAML diff proposals with zero destructive auto-execution.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <p>KubeVora &copy; {new Date().getFullYear()} &bull; On-Demand AI Kubernetes Troubleshooting Platform</p>
      </footer>
    </div>
  )
}
