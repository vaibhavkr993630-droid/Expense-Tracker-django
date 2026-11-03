import { useState } from 'react'
import { X } from 'lucide-react'
import client from '../api/client'
import { showToast } from './Toast'

const CATEGORIES = ['Groceries', 'Leisure', 'Electronics', 'Utilities', 'Clothing', 'Health', 'Others']

const today = () => new Date().toISOString().split('T')[0]

export default function ExpenseModal({ expense, onClose, onSaved }) {
  const isEdit = !!expense
  const [form, setForm] = useState({
    amount: expense?.amount ?? '',
    category: expense?.category ?? '',
    description: expense?.description ?? '',
    date: expense?.date ? expense.date.split('T')[0] : today(),
  })
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await client.put(`/expenses/${expense.id}`, form)
        showToast('Expense updated')
      } else {
        await client.post('/expenses', form)
        showToast('Expense added')
      }
      onSaved()
      onClose()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Something went wrong', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold text-lg">{isEdit ? 'Edit Expense' : 'Add Expense'}</h2>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">Amount ($)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              className="input-field"
              value={form.amount}
              onChange={(e) => set('amount', e.target.value)}
              placeholder="0.00"
            />
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">Category</label>
            <select
              required
              className="input-field"
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
            >
              <option value="">Select category</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">Description</label>
            <input
              type="text"
              maxLength={200}
              className="input-field"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              placeholder="Optional note"
            />
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">Date</label>
            <input
              type="date"
              required
              className="input-field"
              value={form.date}
              onChange={(e) => set('date', e.target.value)}
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Saving...' : isEdit ? 'Update' : 'Add Expense'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
