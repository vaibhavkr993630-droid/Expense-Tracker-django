import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard,
  Receipt,
  BarChart2,
  Target,
  User,
  LogOut,
  Wallet,
} from 'lucide-react'

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/expenses', icon: Receipt, label: 'Expenses' },
  { to: '/analytics', icon: BarChart2, label: 'Analytics' },
  { to: '/budgets', icon: Target, label: 'Budgets' },
  { to: '/account', icon: User, label: 'Account' },
]

export default function Sidebar() {
  const { username, logout } = useAuth()

  return (
    <aside className="w-56 flex-shrink-0 bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <Wallet className="text-primary" size={22} />
          <span className="font-bold text-white text-base">ExpenseTracker</span>
        </div>
        <p className="text-xs text-muted mt-1 truncate">@{username}</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-white'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-border">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-danger hover:bg-red-900/20 transition-colors"
        >
          <LogOut size={17} />
          Logout
        </button>
      </div>
    </aside>
  )
}
