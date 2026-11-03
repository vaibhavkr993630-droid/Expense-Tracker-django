import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'

let toastFn = null

export function showToast(message, type = 'success') {
  if (toastFn) toastFn({ message, type, id: Date.now() })
}

export default function Toast() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    toastFn = (toast) => {
      setToasts((prev) => [...prev, toast])
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id))
      }, 3500)
    }
    return () => { toastFn = null }
  }, [])

  return (
    <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-xl border text-sm font-medium min-w-[240px] animate-in slide-in-from-right ${
            toast.type === 'error'
              ? 'bg-red-900/90 border-red-700 text-red-100'
              : 'bg-green-900/90 border-green-700 text-green-100'
          }`}
        >
          {toast.type === 'error' ? <XCircle size={16} /> : <CheckCircle size={16} />}
          {toast.message}
          <button
            onClick={() => setToasts((p) => p.filter((t) => t.id !== toast.id))}
            className="ml-auto opacity-60 hover:opacity-100"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
