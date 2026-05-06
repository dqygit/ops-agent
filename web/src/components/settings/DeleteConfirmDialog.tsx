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
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="alertdialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="w-[400px] bg-ops-panel border border-ops-border/50 rounded-xl p-5 shadow-2xl flex flex-col gap-3">
        <h4 id={titleId} className="text-base font-medium text-ops-text">{title}</h4>
        <p className="text-sm text-ops-muted">{message}</p>
        <div className="flex items-center justify-end gap-3 mt-4 pt-4 border-t border-ops-border/20">
          <button type="button" className="px-4 py-2 text-sm rounded-md hover:bg-ops-border/20 text-ops-muted transition-colors" onClick={onCancel}>取消</button>
          <button type="button" className="px-4 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50" onClick={onConfirm} disabled={saving || confirmDisabled}>删除</button>
        </div>
      </div>
    </div>
  )
}
