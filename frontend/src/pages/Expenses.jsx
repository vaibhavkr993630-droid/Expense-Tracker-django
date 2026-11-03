import { useEffect, useState, useCallback } from 'react'
import { Plus, Pencil, Trash2, Download, FileText, ChevronLeft, ChevronRight, Filter } from 'lucide-react'
import client from '../api/client'
import { showToast } from '../components/Toast'
import ExpenseModal from '../components/ExpenseModal'
import ConfirmDialog from '../components/ConfirmDialog'

const PERIODS = ['', 'week', 'month', '3months']
const PERIOD_LABELS = { '': 'All time', week: 'Last 7 days', month: 'Last 30 days', '3months': 'Last 3 months' }

export default function Expenses() {
  const [data, setData] = useState({ expenses: [], total: 0, page: 1, limit: 10 })
  const [filters, setFilters] = useState({ from_date: '', to_date: '', period: '', page: 1, limit: 10 })
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const fetchExpenses = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v) })
    try {
      const res = await client.get(`/expenses?${params}`)
      setData(res.data)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { fetchExpenses() }, [fetchExpenses])

  const handleDelete = async () => {
    try {
      await client.delete(`/expenses/${deleteTarget.id}`)
      showToast('Expense deleted')
      fetchExpenses()
    } catch {
      showToast('Failed to delete', 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const exportFile = async (type) => {
    const params = new URLSearchParams()
    if (filters.from_date) params.append('from_date', filters.from_date)
    if (filters.to_date) params.append('to_date', filters.to_date)
    if (filters.period) params.append('period', filters.period)
    const token = localStorage.getItem('token')
    const res = await fetch(`/expenses/export/${type}?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) { showToast('Export failed', 'error'); return }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `expenses.${type}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const totalPages = Math.ceil(data.total / filters.limit) || 1
  const setPage = (p) => setFilters((f) => ({ ...f, page: p }))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Expenses</h1>
          <p className="text-muted text-sm mt-1">{data.total} total record(s)</p>
        </div>
        <button onClick={() => { setEditTarget(null); setShowModal(true) }} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Expense
        </button>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-end">
        <Filter size={16} className="text-muted self-center" />
        <div>
          <label className="block text-xs text-muted mb-1">Period</label>
          <select
            className="input-field text-sm w-36"
            value={filters.period}
            onChange={(e) => setFilters((f) => ({ ...f, period: e.target.value, from_date: '', to_date: '', page: 1 }))}
          >
            {PERIODS.map((p) => <option key={p} value={p}>{PERIOD_LABELS[p]}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">From</label>
          <input type="date" className="input-field text-sm" value={filters.from_date}
            onChange={(e) => setFilters((f) => ({ ...f, from_date: e.target.value, period: '', page: 1 }))} />
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">To</label>
          <input type="date" className="input-field text-sm" value={filters.to_date}
            onChange={(e) => setFilters((f) => ({ ...f, to_date: e.target.value, period: '', page: 1 }))} />
        </div>
        <button onClick={() => setFilters({ from_date: '', to_date: '', period: '', page: 1, limit: 10 })} className="btn-ghost text-sm">
          Reset
        </button>
        <div className="ml-auto flex gap-2">
          <button onClick={() => exportFile('csv')} className="flex items-center gap-1 text-sm text-muted hover:text-white transition-colors">
            <Download size={15} /> CSV
          </button>
          <button onClick={() => exportFile('pdf')} className="flex items-center gap-1 text-sm text-muted hover:text-white transition-colors">
            <FileText size={15} /> PDF
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted text-xs uppercase">
                <th className="text-left px-5 py-3">Date</th>
                <th className="text-left px-5 py-3">Category</th>
                <th className="text-left px-5 py-3">Description</th>
                <th className="text-right px-5 py-3">Amount</th>
                <th className="text-right px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center text-muted py-10">Loading...</td></tr>
              ) : data.expenses.length === 0 ? (
                <tr><td colSpan={5} className="text-center text-muted py-10">No expenses found</td></tr>
              ) : (
                data.expenses.map((exp) => (
                  <tr key={exp.id} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                    <td className="px-5 py-3 text-muted">{String(exp.date).slice(0, 10)}</td>
                    <td className="px-5 py-3">
                      <span className="bg-primary/20 text-primary text-xs font-medium px-2 py-0.5 rounded-full">
                        {exp.category}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-300 max-w-xs truncate">{exp.description || '—'}</td>
                    <td className="px-5 py-3 text-right font-semibold text-white">${parseFloat(exp.amount).toFixed(2)}</td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => { setEditTarget(exp); setShowModal(true) }}
                          className="p-1.5 rounded text-muted hover:text-primary hover:bg-primary/10 transition-colors"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(exp)}
                          className="p-1.5 rounded text-muted hover:text-danger hover:bg-red-900/20 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-border text-sm text-muted">
            <span>Page {filters.page} of {totalPages}</span>
            <div className="flex gap-2">
              <button disabled={filters.page <= 1} onClick={() => setPage(filters.page - 1)}
                className="p-1.5 rounded hover:bg-white/10 disabled:opacity-40 transition-colors">
                <ChevronLeft size={16} />
              </button>
              <button disabled={filters.page >= totalPages} onClick={() => setPage(filters.page + 1)}
                className="p-1.5 rounded hover:bg-white/10 disabled:opacity-40 transition-colors">
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {showModal && (
        <ExpenseModal
          expense={editTarget}
          onClose={() => { setShowModal(false); setEditTarget(null) }}
          onSaved={fetchExpenses}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          message={`Delete "$${parseFloat(deleteTarget.amount).toFixed(2)} – ${deleteTarget.category}"?`}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}
