import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { Wallet } from 'lucide-react'

export default function Auth() {
  const [tab, setTab] = useState('login')
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const body = new URLSearchParams({ username: form.username, password: form.password })
      const res = await axios.post('/login', body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      login(res.data.access_token, form.username)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await axios.post('/signup', form)
      setTab('login')
      setForm((f) => ({ ...f, email: '', password: '', confirm_password: '' }))
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <div className="p-3 bg-primary/20 rounded-2xl">
              <Wallet size={32} className="text-primary" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white">Expense Tracker</h1>
          <p className="text-muted text-sm mt-1">Track your spending smarter</p>
        </div>

        <div className="card">
          {/* Tabs */}
          <div className="flex bg-bg rounded-lg p-1 mb-6">
            {['login', 'signup'].map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setError('') }}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors capitalize ${
                  tab === t ? 'bg-primary text-white' : 'text-muted hover:text-white'
                }`}
              >
                {t === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-800 text-red-300 text-sm rounded-lg px-4 py-3 mb-4">
              {error}
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm text-muted mb-1">Username</label>
                <input
                  required
                  className="input-field"
                  value={form.username}
                  onChange={(e) => set('username', e.target.value)}
                  placeholder="your_username"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Password</label>
                <input
                  type="password"
                  required
                  className="input-field"
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="space-y-4">
              <div>
                <label className="block text-sm text-muted mb-1">Username</label>
                <input
                  required
                  className="input-field"
                  value={form.username}
                  onChange={(e) => set('username', e.target.value)}
                  placeholder="your_username"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Email</label>
                <input
                  type="email"
                  required
                  className="input-field"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  className="input-field"
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Confirm Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  className="input-field"
                  value={form.confirm_password}
                  onChange={(e) => set('confirm_password', e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
