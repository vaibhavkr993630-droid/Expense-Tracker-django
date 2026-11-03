import { useEffect, useState, useCallback } from 'react'
import { Plus, Trash2, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import client from '../api/client'
import { showToast } from '../components/Toast'
import BudgetModal from '../components/BudgetModal'
import ConfirmDialog from '../components/ConfirmDialog'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function StatusIcon({ status }) {
  if (status === 'exceeded') return <XCircle size={16} className="text-danger" />
  if (status === 'warning') return <AlertTriangle size={16} className="text-warning" />
  return <CheckCircle size={16} className="text-success" />
}

function BadgeStatus({ status }) {
  const cls = status === 'exceeded' ? 'badge-exceeded' : status === 'warning' ? 'badge-warning' : 'badge-ok'
  const label = status === 'exceeded' ? 'Exceeded' : status === 'warning' ? 'Warning' : 'On Track'
  return <span className={cls}>{label}</span>
}

export default function Budgets() {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [budgets, setBudgets] = useState([])
  const [alerts, setAlerts] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const [b, a] = await Promise.all([
        client.get(`/budgets?month=${month}&year=${year}`),
        client.get(`/budgets/alerts?month=${month}&year=${year}`),
      ])
      setBudgets(b.data)
      setAlerts(a.data.alerts)
    } finally {
      setLoading(false)
    }
  }, [month, year])

  useEffect(() => { fetch() }, [fetch])

  const handleDelete = async () => {
    try {
      await client.delete(`/budgets/${deleteTarget.id}`)
      showToast('Budget deleted')
      fetch()
    } catch {
      showToast('Failed to delete', 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const alertMap = Object.fromEntries(alerts.map((a) => [a.category, a]))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Budgets</h1>
          <p className="text-muted text-sm mt-1">Set limits and track spending</p>
        </div>
        <div className="flex gap-2 items-center">
          <select className="input-field text-sm w-28" value={month} onChange={(e) => setMonth(+e.target.value)}>
            {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <input type="number" min="2000" max="2100" className="input-field text-sm w-20" value={year} onChange={(e) => setYear(+e.target.value)} />
          <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Set Budget
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-muted text-center py-10">Loading...</p>
      ) : budgets.length === 0 ? (
        <div className="card text-center py-16">
          <p className="text-muted">No budgets set for {MONTHS[month - 1]} {year}</p>
          <button onClick={() => setShowModal(true)} className="btn-primary mt-4 inline-flex items-center gap-2">
            <Plus size={16} /> Set your first budget
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {budgets.map((b) => {
            const alert = alertMap[b.category]
            const pct = alert?.percentage_used ?? 0
            const barColor = alert?.status === 'exceeded' ? '#ef4444' : alert?.status === 'warning' ? '#f59e0b' : '#22c55e'

            return (
              <div key={b.id} className="card space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <StatusIcon status={alert?.status ?? 'ok'} />
                    <span className="text-white font-semibold">{b.category}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BadgeStatus status={alert?.status ?? 'ok'} />
                    <button
                      onClick={() => setDeleteTarget(b)}
                      className="p-1.5 rounded text-muted hover:text-danger hover:bg-red-900/20 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1">
                  <div className="w-full bg-border rounded-full h-2">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(pct, 100)}%`, background: barColor }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted">
                    <span>Spent: <span className="text-white font-medium">${(alert?.spent ?? 0).toFixed(2)}</span></span>
                    <span>Limit: <span className="text-white font-medium">${parseFloat(b.amount).toFixed(2)}</span></span>
                  </div>
                </div>

                {/* Stats row */}
                <div className="flex gap-4 text-sm">
                  <div>
                    <p className="text-muted text-xs">Used</p>
                    <p className="text-white font-semibold">{pct.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Remaining</p>
                    <p className={`font-semibold ${(alert?.remaining ?? 0) < 0 ? 'text-danger' : 'text-success'}`}>
                      ${(alert?.remaining ?? parseFloat(b.amount)).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showModal && <BudgetModal onClose={() => setShowModal(false)} onSaved={fetch} />}
      {deleteTarget && (
        <ConfirmDialog
          message={`Delete budget for "${deleteTarget.category}"?`}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}
