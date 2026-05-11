type DeleteConfirmDialogProps = {
  titleId: string
  title: string
  message: string
  saving: boolean
  confirmDisabled?: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function DeleteConfirmDialog({ titleId, title, message, saving, confirmDisabled, onCancel, onConfirm }: DeleteConfirmDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ops-bg/60 backdrop-blur-sm animate-in fade-in duration-300" role="presentation">
      <div className="w-[420px] max-w-[90vw] bg-ops-panel/90 border border-ops-border/40 rounded-2xl p-8 shadow-2xl flex flex-col gap-6 backdrop-blur-xl animate-in zoom-in-95 duration-300" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="flex items-center gap-4 text-ops-danger">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ops-danger/10">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
          </div>
          <h3 id={titleId} className="text-lg font-bold  tracking-wider">{title}</h3>
        </div>
        <p className="text-[13px] leading-relaxed text-ops-text/80">
          Confirming decommission of <span className="font-bold text-ops-cyan">{message}</span>. This procedure is destructive and irreversible.
        </p>
        <div className="flex items-center justify-end gap-3 pt-2">
          <button type="button" className="button px-6" onClick={onCancel} disabled={saving}>Abort</button>
          <button
            type="button"
            className="button button-danger px-8"
            onClick={onConfirm}
            disabled={saving || confirmDisabled}
          >
            {saving ? 'Processing...' : 'Confirm Destruction'}
          </button>
        </div>
      </div>
    </div>
  )
}
