import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  Boxes,
  Terminal,
  User,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  Lock,
  Cpu,
  Layers,
  Zap
} from 'lucide-react'

export const Login = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [usernameOrEmail, setUsernameOrEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError(null)
    if (!usernameOrEmail.trim() || !password) {
      setFormError('Please enter your username/email and password.')
      return
    }

    setSubmitting(true)
    const result = await login(usernameOrEmail.trim(), password)
    setSubmitting(false)

    if (result.success) {
      const target = location.state?.from?.pathname || '/dashboard'
      navigate(target, { replace: true })
    } else {
      setFormError(result.error)
    }
  }

  // Convenience helper for 1-click evaluation
  const handleQuickDemoLogin = async () => {
    setUsernameOrEmail('admin_sre')
    setPassword('adminpassword123')
    setSubmitting(true)
    setFormError(null)
    const result = await login('admin_sre', 'adminpassword123')
    setSubmitting(false)
    if (result.success) {
      navigate('/dashboard', { replace: true })
    } else {
      setFormError(result.error)
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-800 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      {/* Background ambient lighting and fine pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(#e0e7ff_1px,transparent_1px)] [background-size:28px_28px] opacity-60 pointer-events-none"></div>
      <div className="absolute top-1/6 -left-32 w-96 h-96 bg-indigo-100/70 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/6 -right-32 w-96 h-96 bg-purple-100/70 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-10 items-center relative z-10">
        
        {/* Left Column: Brand Overview & Core Pillars */}
        <div className="lg:col-span-6 space-y-7">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-violet-50 border border-violet-200/90 text-violet-700 text-xs font-semibold shadow-xs">
            <span className="w-2 h-2 rounded-full bg-violet-600 animate-pulse"></span>
            Unified System Clarity
          </div>

          <div>
            <div className="flex items-center gap-3.5 mb-2">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 p-0.5 shadow-md shadow-violet-500/20">
                <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center">
                  <Boxes className="w-6 h-6 text-violet-600" />
                </div>
              </div>
              <h1 className="text-4xl sm:text-5xl font-black font-display tracking-tight text-indigo-950">
                Kube<span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 bg-clip-text text-transparent">Vora</span>
              </h1>
            </div>
            <p className="text-lg font-bold text-indigo-900 mt-2">
              Autonomous System Equilibrium & Causal Clarity
            </p>
            <p className="text-sm text-slate-500 mt-1.5 font-medium leading-relaxed max-w-md">
              Transform noisy operational signals into verified root causes and safe, automated remediations in real time.
            </p>
          </div>

          {/* Core Pillars: Clean White Cards with Violet/Blue Accents */}
          <div className="space-y-3 pt-1">
            <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/80 border border-slate-200/90 shadow-xs hover:border-violet-300 hover:shadow-md hover:shadow-violet-500/5 transition-all">
              <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
                <Zap className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">Evidence-Linked Diagnosis</h2>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">Correlates millions of live operational signals into an isolated, proven causal trajectory.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/80 border border-slate-200/90 shadow-xs hover:border-violet-300 hover:shadow-md hover:shadow-violet-500/5 transition-all">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 shrink-0 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">Safe Resolution Guardrails</h2>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">Deterministic remediations validated in real-time with instant automated rollback envelopes.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/80 border border-slate-200/90 shadow-xs hover:border-violet-300 hover:shadow-md hover:shadow-violet-500/5 transition-all">
              <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shrink-0 mt-0.5">
                <Layers className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">Incident Pattern Memory</h2>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">Intelligent signatures eliminate repetitive investigation of identical operational bottlenecks.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Clean White Authentication Card */}
        <div className="lg:col-span-6">
          <div className="bg-white/95 border border-violet-100 rounded-3xl shadow-xl shadow-violet-500/10 p-7 sm:p-9 relative overflow-hidden backdrop-blur-xl">
            {/* Window Header */}
            <div className="flex items-center justify-between pb-4 mb-6 border-b border-slate-100 text-xs font-medium text-slate-400">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-400/80"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80"></span>
                </div>
                <span className="text-slate-400 font-semibold ml-1">Secure Operations Console</span>
              </div>
              <span className="text-violet-600 font-semibold bg-violet-50 px-2 py-0.5 rounded-md border border-violet-200/70">
                Verified Access
              </span>
            </div>

            <h2 className="text-2xl font-bold font-display text-indigo-950 mb-1">Sign In</h2>
            <p className="text-xs text-slate-500 mb-6 font-medium">
              Enter your credentials to access live operational insights.
            </p>

            {formError && (
              <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-indigo-950 mb-1.5">
                  Username or Work Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    placeholder="admin_sre or team@company.com"
                    className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold text-indigo-950">
                    Password
                  </label>
                  <span className="text-[11px] text-slate-400 font-medium">Minimum 6 characters</span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-violet-500/25 disabled:opacity-50 transition-all duration-200 mt-2"
              >
                {submitting ? (
                  <>
                    <Cpu className="w-4 h-4 animate-spin" />
                    <span>Verifying Session...</span>
                  </>
                ) : (
                  <>
                    <span>Enter Console</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Login Preset Button */}
            <div className="mt-5 pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={handleQuickDemoLogin}
                disabled={submitting}
                className="w-full py-2.5 px-3 rounded-xl bg-violet-50/60 hover:bg-violet-100/70 border border-violet-200/80 text-violet-700 hover:text-violet-900 text-xs font-semibold flex items-center justify-center gap-2 transition-all duration-200"
              >
                <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                <span>1-Click Evaluation Access (admin_sre)</span>
              </button>
            </div>

            {/* Register Link */}
            <div className="mt-5 text-center text-xs text-slate-500 font-medium">
              Need team access?{' '}
              <Link to="/register" className="text-violet-600 hover:text-violet-800 underline font-semibold">
                Request Account Access
              </Link>
            </div>

          </div>
        </div>

      </div>
    </div>
  )
}

export default Login
