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
    <div className="settings-confirm" role="alertdialog" aria-modal="true" aria-labelledby={titleId}>
      <h4 id={titleId}>{title}</h4>
      <p>{message}</p>
      <div className="modal-actions">
        <button type="button" className="button" onClick={onCancel}>取消</button>
        <button type="button" className="button button-danger" onClick={onConfirm} disabled={saving || confirmDisabled}>删除</button>
      </div>
    </div>
  )
}
