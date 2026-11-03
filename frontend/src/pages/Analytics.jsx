import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import client from '../api/client'

const COLORS = ['#4361ee', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316']
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function Analytics() {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [catData, setCatData] = useState({ grand_total: 0, categories: [] })
  const [monthly, setMonthly] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      client.get(`/expenses/summary/category?month=${month}&year=${year}`),
      client.get(`/expenses/summary/monthly?month=${month}&year=${year}`),
    ])
      .then(([c, m]) => { setCatData(c.data); setMonthly(m.data) })
      .finally(() => setLoading(false))
  }, [month, year])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-muted text-sm mt-1">Spending insights for selected period</p>
        </div>
        <div className="flex gap-2">
          <select className="input-field text-sm w-32" value={month} onChange={(e) => setMonth(+e.target.value)}>
            {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <input
            type="number"
            min="2000"
            max="2100"
            className="input-field text-sm w-24"
            value={year}
            onChange={(e) => setYear(+e.target.value)}
          />
        </div>
      </div>

      {/* Summary Cards */}
      {monthly && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'Total Spent', value: `$${monthly.total_expenses.toFixed(2)}` },
            { label: 'Transactions', value: monthly.expense_count },
            { label: 'Avg per Expense', value: `$${monthly.average_expense.toFixed(2)}` },
          ].map(({ label, value }) => (
            <div key={label} className="card text-center">
              <p className="text-muted text-sm">{label}</p>
              <p className="text-white text-2xl font-bold mt-1">{value}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-muted text-center py-10">Loading...</p>
      ) : catData.categories.length === 0 ? (
        <p className="text-muted text-center py-10">No expenses for this period</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bar Chart */}
          <div className="card">
            <h2 className="text-white font-semibold mb-4">Spending by Category</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={catData.categories} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a45" />
                <XAxis dataKey="category" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip
                  formatter={(v) => [`$${v.toFixed(2)}`, 'Spent']}
                  contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a45', borderRadius: '8px' }}
                />
                <Bar dataKey="total" radius={[4, 4, 0, 0]}>
                  {catData.categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pie Chart */}
          <div className="card">
            <h2 className="text-white font-semibold mb-4">Share of Total (${catData.grand_total.toFixed(2)})</h2>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={catData.categories}
                  dataKey="total"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  innerRadius={45}
                >
                  {catData.categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => `$${v.toFixed(2)}`} contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a45', borderRadius: '8px' }} />
                <Legend wrapperStyle={{ fontSize: '12px', color: '#6b7280' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div className="card lg:col-span-2 p-0 overflow-hidden">
            <h2 className="text-white font-semibold p-5 border-b border-border">Category Breakdown</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted text-xs uppercase border-b border-border">
                  <th className="text-left px-5 py-3">Category</th>
                  <th className="text-right px-5 py-3">Total</th>
                  <th className="text-right px-5 py-3">Count</th>
                  <th className="text-right px-5 py-3">% of Total</th>
                  <th className="px-5 py-3">Share</th>
                </tr>
              </thead>
              <tbody>
                {catData.categories.map((c, i) => (
                  <tr key={c.category} className="border-b border-border/50 hover:bg-white/5">
                    <td className="px-5 py-3 flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-white">{c.category}</span>
                    </td>
                    <td className="px-5 py-3 text-right font-semibold text-white">${c.total.toFixed(2)}</td>
                    <td className="px-5 py-3 text-right text-muted">{c.count}</td>
                    <td className="px-5 py-3 text-right text-muted">{c.percentage}%</td>
                    <td className="px-5 py-3">
                      <div className="w-full bg-border rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full"
                          style={{ width: `${c.percentage}%`, background: COLORS[i % COLORS.length] }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
