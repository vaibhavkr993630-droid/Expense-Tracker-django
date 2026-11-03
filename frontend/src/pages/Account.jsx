import { useEffect, useState } from 'react'
import { User, Mail, KeyRound, Trash2 } from 'lucide-react'
import client from '../api/client'
import { showToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../context/AuthContext'

export default function Account() {
  const { username, logout } = useAuth()
  const [profile, setProfile] = useState(null)
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwLoading, setPwLoading] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  useEffect(() => {
    client.get('/users/me').then((r) => setProfile(r.data)).catch(() => {})
  }, [])

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm) {
      showToast('Passwords do not match', 'error')
      return
    }
    setPwLoading(true)
    try {
      await client.patch('/users/change-password', {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      })
      showToast('Password updated')
      setPwForm({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to update password', 'error')
    } finally {
      setPwLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    try {
      await client.delete('/users/me')
      showToast('Account deleted')
      logout()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to delete account', 'error')
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h1 className="text-2xl font-bold text-white">Account</h1>
        <p className="text-muted text-sm mt-1">Manage your profile and security</p>
      </div>

      {/* Profile Card */}
      <div className="card space-y-4">
        <h2 className="text-white font-semibold border-b border-border pb-3">Profile</h2>
        <div className="flex items-center gap-3 py-2">
          <User size={16} className="text-muted flex-shrink-0" />
          <div>
            <p className="text-xs text-muted">Username</p>
            <p className="text-white font-medium">{profile?.username ?? username}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 py-2">
          <Mail size={16} className="text-muted flex-shrink-0" />
          <div>
            <p className="text-xs text-muted">Email</p>
            <p className="text-white font-medium">{profile?.email ?? '—'}</p>
          </div>
        </div>
      </div>

      {/* Change Password */}
      <div className="card space-y-4">
        <h2 className="text-white font-semibold border-b border-border pb-3 flex items-center gap-2">
          <KeyRound size={16} /> Change Password
        </h2>
        <form onSubmit={handlePasswordChange} className="space-y-3">
          {[
            { key: 'current_password', label: 'Current Password' },
            { key: 'new_password', label: 'New Password' },
            { key: 'confirm', label: 'Confirm New Password' },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="block text-sm text-muted mb-1">{label}</label>
              <input
                type="password"
                required
                minLength={key !== 'current_password' ? 6 : 1}
                className="input-field"
                value={pwForm[key]}
                onChange={(e) => setPwForm((f) => ({ ...f, [key]: e.target.value }))}
                placeholder="••••••••"
              />
            </div>
          ))}
          <button type="submit" disabled={pwLoading} className="btn-primary w-full mt-2">
            {pwLoading ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      </div>

      {/* Danger Zone */}
      <div className="card border-danger/40 space-y-3">
        <h2 className="text-danger font-semibold border-b border-danger/20 pb-3 flex items-center gap-2">
          <Trash2 size={16} /> Danger Zone
        </h2>
        <p className="text-muted text-sm">Permanently delete your account and all associated data. This action cannot be undone.</p>
        <button onClick={() => setShowDelete(true)} className="btn-danger text-sm">
          Delete Account
        </button>
      </div>

      {showDelete && (
        <ConfirmDialog
          message="This will permanently delete your account and all expenses. Are you sure?"
          onConfirm={handleDeleteAccount}
          onCancel={() => setShowDelete(false)}
        />
      )}
    </div>
  )
}
