import React, { useId } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { useDialog } from '../lib/useDialog';

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** `danger` = tombol konfirmasi merah (aksi destruktif). */
  tone?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

/** Pengganti `window.confirm()` yang konsisten dengan tema & aksesibel. */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  message,
  confirmLabel = 'Ya, Lanjutkan',
  cancelLabel = 'Batal',
  tone = 'default',
  onConfirm,
  onCancel,
}) => {
  const ref = useDialog<HTMLDivElement>(open, onCancel);
  const titleId = useId();
  const descId = useId();

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        ref={ref}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        tabIndex={-1}
        className="w-full max-w-sm rounded-2xl bg-slate-900 p-5 shadow-2xl border border-slate-800 text-slate-100 outline-none"
      >
        <div className="flex items-start gap-3">
          <span
            className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border ${
              tone === 'danger'
                ? 'bg-rose-500/15 border-rose-500/30 text-rose-400'
                : 'bg-amber-500/15 border-amber-500/30 text-amber-400'
            }`}
          >
            <ExclamationTriangleIcon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h3 id={titleId} className="text-sm font-bold text-white">
              {title}
            </h3>
            <div id={descId} className="mt-1 text-xs text-slate-400 leading-relaxed">
              {message}
            </div>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            data-autofocus
            onClick={onCancel}
            className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold text-white shadow-sm ${
              tone === 'danger'
                ? 'bg-rose-600 hover:bg-rose-500'
                : 'bg-emerald-600 hover:bg-emerald-500'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
