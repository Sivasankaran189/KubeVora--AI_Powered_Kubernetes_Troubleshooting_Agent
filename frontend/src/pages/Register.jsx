import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  Boxes,
  User,
  Mail,
  Lock,
  ArrowRight,
  ShieldAlert,
  Cpu,
  BadgeCheck
} from 'lucide-react'

export const Register = () => {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'Site Reliability Engineer',
  })
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError(null)

    if (!formData.username.trim() || !formData.email.trim() || !formData.password) {
      setFormError('Please fill in all required fields.')
      return
    }

    if (formData.password.length < 6) {
      setFormError('Password must be at least 6 characters.')
      return
    }

    setSubmitting(true)
    const result = await register({
      username: formData.username.trim(),
      email: formData.email.trim().toLowerCase(),
      password: formData.password,
      full_name: formData.full_name.trim() || formData.username.trim(),
      role: formData.role,
    })
    setSubmitting(false)

    if (result.success) {
      navigate('/dashboard', { replace: true })
    } else {
      setFormError(result.error)
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-800 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 bg-[radial-gradient(#e0e7ff_1px,transparent_1px)] [background-size:28px_28px] opacity-60 pointer-events-none"></div>
      <div className="absolute top-1/4 -right-36 w-96 h-96 bg-purple-100/70 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 -left-36 w-96 h-96 bg-indigo-100/70 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-lg relative z-10">
        <div className="bg-white/95 border border-violet-100 rounded-3xl shadow-xl shadow-violet-500/10 p-7 sm:p-9 relative overflow-hidden backdrop-blur-xl">
          
          {/* Header */}
          <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 text-xs font-medium text-slate-400">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-400/80"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80"></span>
              </div>
              <span className="text-slate-400 font-semibold ml-1">Team Provisioning</span>
            </div>
            <span className="text-violet-600 font-semibold bg-violet-50 px-2 py-0.5 rounded-md border border-violet-200/70">
              Role Access
            </span>
          </div>

          <div className="flex items-center gap-3.5 mb-2">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 p-0.5 shadow-md shadow-violet-500/20">
              <div className="w-full h-full bg-white rounded-[13px] flex items-center justify-center">
                <Boxes className="w-5 h-5 text-violet-600" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-display text-indigo-950">
                Create Account
              </h1>
              <p className="text-xs text-slate-500 font-medium">
                Initialize your workspace access with enterprise governance controls.
              </p>
            </div>
          </div>

          {formError && (
            <div className="mt-4 mb-2 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 mt-5">
            <div>
              <label className="block text-xs font-bold text-indigo-950 mb-1">
                Username <span className="text-violet-600">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="operations_lead"
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-indigo-950 mb-1">
                Email Address <span className="text-violet-600">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-indigo-950 mb-1">
                Full Display Name
              </label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                placeholder="Alex Morgan"
                className="w-full px-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-indigo-950 mb-1">
                Operational Role
              </label>
              <select
                name="role"
                value={formData.role}
                onChange={handleChange}
                className="w-full px-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
              >
                <option value="Site Reliability Engineer">Site Reliability Engineer (SRE)</option>
                <option value="Platform Operations Lead">Platform Operations Lead</option>
                <option value="Infrastructure Architect">Infrastructure Architect</option>
                <option value="Systems Operations Engineer">Systems Operations Engineer</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-indigo-950 mb-1">
                Password <span className="text-violet-600">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Minimum 6 characters"
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 transition-all"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-violet-500/25 disabled:opacity-50 transition-all duration-200 mt-5"
            >
              {submitting ? (
                <>
                  <Cpu className="w-4 h-4 animate-spin" />
                  <span>Provisioning Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account & Enter Console</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-5 text-center text-xs text-slate-500 font-medium">
            Already have an account?{' '}
            <Link to="/login" className="text-violet-600 hover:text-violet-800 underline font-semibold">
              Back to Sign In
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}

export default Register
