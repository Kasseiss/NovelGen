import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

let listeners: ((toasts: ToastItem[]) => void)[] = [];
let toastList: ToastItem[] = [];
let nextId = 0;

export function showToast(message: string, type: ToastType = 'info') {
  const id = nextId++;
  toastList = [...toastList, { id, type, message }];
  listeners.forEach((l) => l(toastList));

  setTimeout(() => {
    toastList = toastList.filter((t) => t.id !== id);
    listeners.forEach((l) => l(toastList));
  }, 3000);
}

const icons = {
  success: <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />,
  error: <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />,
  info: <Info className="w-4 h-4 text-gold-400 shrink-0" />,
};

const bgColors = {
  success: 'bg-emerald-500/10 border-emerald-500/20',
  error: 'bg-red-500/10 border-red-500/20',
  info: 'bg-gold-500/10 border-gold-500/20',
};

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    listeners.push(setToasts);
    return () => {
      listeners = listeners.filter((l) => l !== setToasts);
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-16 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-2 px-4 py-3 rounded-lg border backdrop-blur-sm animate-fade-in ${bgColors[toast.type]}`}
        >
          {icons[toast.type]}
          <span className="text-sm text-ink-100">{toast.message}</span>
          <button
            onClick={() => {
              toastList = toastList.filter((t) => t.id !== toast.id);
              listeners.forEach((l) => l(toastList));
            }}
            className="ml-2 p-0.5 text-ink-500 hover:text-ink-300"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
