import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { TrendingUp, Receipt, DollarSign, Calendar } from 'lucide-react'
import client from '../api/client'

const COLORS = ['#4361ee', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316']

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-muted text-sm">{label}</p>
        <p className="text-white text-xl font-bold">{value}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const now = new Date()
  const [summary, setSummary] = useState(null)
  const [categories, setCategories] = useState([])
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const month = now.getMonth() + 1
    const year = now.getFullYear()

    Promise.all([
      client.get(`/expenses/summary/monthly?month=${month}&year=${year}`),
      client.get(`/expenses/summary/category?month=${month}&year=${year}`),
      client.get('/expenses?limit=5&page=1'),
    ])
      .then(([s, c, r]) => {
        setSummary(s.data)
        setCategories(c.data.categories)
        setRecent(r.data.expenses)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-muted text-center pt-20">Loading dashboard...</div>

  const monthName = now.toLocaleString('default', { month: 'long' })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-muted text-sm mt-1">{monthName} {now.getFullYear()} overview</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total Spent"
          value={`$${summary?.total_expenses?.toFixed(2) ?? '0.00'}`}
          color="bg-primary"
        />
        <StatCard
          icon={Receipt}
          label="Expenses"
          value={summary?.expense_count ?? 0}
          color="bg-green-700"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg per Expense"
          value={`$${summary?.average_expense?.toFixed(2) ?? '0.00'}`}
          color="bg-purple-700"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="card">
          <h2 className="text-white font-semibold mb-4">Spending by Category</h2>
          {categories.length === 0 ? (
            <p className="text-muted text-sm text-center py-10">No data for this month</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={categories}
                  dataKey="total"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ category, percentage }) => `${category} ${percentage}%`}
                  labelLine={false}
                >
                  {categories.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `$${v.toFixed(2)}`} contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a45', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Recent Expenses */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold">Recent Expenses</h2>
            <Calendar size={16} className="text-muted" />
          </div>
          {recent.length === 0 ? (
            <p className="text-muted text-sm text-center py-10">No expenses yet</p>
          ) : (
            <div className="space-y-3">
              {recent.map((exp) => (
                <div key={exp.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="text-white text-sm font-medium">{exp.category}</p>
                    <p className="text-muted text-xs">{exp.description || '—'} · {String(exp.date).slice(0, 10)}</p>
                  </div>
                  <span className="text-white font-semibold text-sm">${parseFloat(exp.amount).toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
