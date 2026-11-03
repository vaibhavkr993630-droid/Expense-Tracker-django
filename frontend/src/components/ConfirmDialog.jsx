import { AlertTriangle } from 'lucide-react'

export default function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl p-6 max-w-sm w-full shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="text-warning flex-shrink-0" size={22} />
          <p className="text-white font-medium">{message}</p>
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="btn-ghost text-sm">Cancel</button>
          <button onClick={onConfirm} className="btn-danger text-sm">Delete</button>
        </div>
      </div>
    </div>
  )
}
