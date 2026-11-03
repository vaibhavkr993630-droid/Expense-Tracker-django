import { useState } from 'react'
import { X } from 'lucide-react'
import client from '../api/client'
import { showToast } from './Toast'

const CATEGORIES = ['Groceries', 'Leisure', 'Electronics', 'Utilities', 'Clothing', 'Health', 'Others']

export default function BudgetModal({ onClose, onSaved }) {
  const now = new Date()
  const [form, setForm] = useState({
    category: '',
    amount: '',
    month: now.getMonth() + 1,
    year: now.getFullYear(),
  })
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await client.post('/budgets', {
        ...form,
        amount: parseFloat(form.amount),
        month: parseInt(form.month),
        year: parseInt(form.year),
      })
      showToast('Budget saved')
      onSaved()
      onClose()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to save budget', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold text-lg">Set Budget</h2>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">Category</label>
            <select required className="input-field" value={form.category} onChange={(e) => set('category', e.target.value)}>
              <option value="">Select category</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">Budget Limit ($)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              className="input-field"
              value={form.amount}
              onChange={(e) => set('amount', e.target.value)}
              placeholder="500.00"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-muted mb-1">Month</label>
              <select className="input-field" value={form.month} onChange={(e) => set('month', e.target.value)}>
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(0, i).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">Year</label>
              <input
                type="number"
                min="2000"
                max="2100"
                className="input-field"
                value={form.year}
                onChange={(e) => set('year', e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Saving...' : 'Set Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
