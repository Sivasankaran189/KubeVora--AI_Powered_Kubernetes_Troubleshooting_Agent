import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import History from './pages/History'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Default Homepage: Clean KubeVora Landing & Status */}
          <Route path="/" element={<Home />} />

          {/* Public Authentication Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* SRE Console Dashboard */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
                  <Navbar />
                  <main className="flex-1">
                    <Dashboard />
                  </main>
                </div>
              </ProtectedRoute>
            }
          />

          {/* SRE Incident History */}
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
