import { useState, useEffect } from 'react'
import { useAppearance } from '../../../hooks/useAppearance'
import type { AgentMessage } from '../../../types/ops'
import type { Approval, CommandStart, CommandChunk, CommandEnd } from './types'
import { OutputBlock } from './OutputBlock'

type CommandExecutionCardProps = {
  message?: AgentMessage
  approvalEvent?: Approval
  startEvent?: CommandStart
  chunkEvents?: CommandChunk[]
  endEvent?: CommandEnd
  pendingApprovalRuntimeId: string | null
  onApprove?: (allowPrefix?: string) => void
  onReject?: () => void
}

export function CommandExecutionCard({
  message,
  approvalEvent,
  startEvent,
  chunkEvents = [],
  endEvent,
  pendingApprovalRuntimeId,
  onApprove,
  onReject
}: CommandExecutionCardProps) {
  const { t } = useAppearance()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showWhitelistOptions, setShowWhitelistOptions] = useState(false)
  const [allowPrefix, setAllowPrefix] = useState('')

  // Derived state from AgentMessage or Legacy events
  const toolCall = message?.toolCall
  const rawCommand = toolCall?.command || (startEvent as any)?.command || approvalEvent?.command || ''
  const isCommandTool = Boolean(rawCommand)
  const toolName = toolCall?.name || toolCall?.originalName || ''
  const toolDisplayText = toolCall?.displayText || ''
  const toolDescription = toolCall?.description || ''
  const argsJson = toolCall?.args ? JSON.stringify(toolCall.args, null, 2) : '{}'
  const args = toolCall?.args ?? {}
  const targetAssetName = typeof args.asset_name === 'string' ? args.asset_name : undefined
  const targetTerminalId = typeof args.terminal_id === 'string' ? args.terminal_id : ((startEvent as any)?.terminalId ?? (startEvent as any)?.terminal_id)
  const targetLabel = [targetAssetName, targetTerminalId ? `terminal ${String(targetTerminalId).slice(0, 8)}` : undefined]
    .filter(Boolean)
    .join(' · ')

  // Parse command: if it's JSON like {"command":"lshw -short"}, extract the actual command
  const displayCommand = (() => {
    if (!rawCommand) return ''

    // Try to parse as JSON
    try {
      const parsed = JSON.parse(rawCommand)
      if (parsed && typeof parsed === 'object' && 'command' in parsed) {
        // It's a JSON object with a command field
        return parsed.command
      }
    } catch {
      // Not JSON, use as-is
    }

    return rawCommand
  })()
  const toolSummary = isCommandTool
    ? displayCommand
    : (toolDisplayText || toolDescription || toolName ? [toolDisplayText || toolName, toolDescription].filter(Boolean).join(' — ') : '')

  const outputText = message?.toolOutput ?? chunkEvents.map((event) => event.text).join('')
  const exitCode = message ? message.exitCode : ((endEvent as any)?.exitCode ?? (endEvent as any)?.exit_code)
  const hasExecutionResult = message ? message.type === 'say' && message.say === 'tool_use' && !message.partial : !!endEvent
  const commandTokens = displayCommand.trim().split(/\s+/).filter(Boolean)
  const allowPrefixOptions = Array.from(new Set([displayCommand.trim(), commandTokens[0]].filter(Boolean)))
  
  const isMessageAsk = message?.type === 'ask'
  const approvalStatus = isMessageAsk ? 'pending' : (message?.type === 'say' && message?.say === 'tool_use' && !message.partial ? 'approved' : (approvalEvent?.status ?? (approvalEvent ? 'pending' : undefined)))
  
  // For ask-type messages: show buttons when pendingApprovalRuntimeId is set (stream guarantees correctness)
  // For legacy approval events: match on runtimeId
  const showApprovalActions = pendingApprovalRuntimeId !== null && (
    isMessageAsk || 
    (approvalStatus === 'pending' && approvalEvent?.runtimeId === pendingApprovalRuntimeId)
  )

  const isRunning = message ? message.partial : (!endEvent && !approvalStatus)

  // Auto-expand if it's an ask message or if command is running/has output
  useEffect(() => {
    if (isMessageAsk) {
      setIsExpanded(true)
    }
  }, [isMessageAsk])

  // Auto-expand when command starts running or has output
  useEffect(() => {
    if (isRunning || outputText) {
      setIsExpanded(true)
    }
  }, [isRunning, outputText])

  return (
    <div className={`group/card my-2 overflow-hidden rounded-[22px] border border-ops-border/25 bg-ops-panel/28 shadow-[0_14px_38px_rgb(var(--ops-bg)/0.14)] transition-all duration-300 ${isExpanded ? 'p-4' : 'px-3 py-2.5'}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-xl border transition-colors ${isRunning ? 'animate-pulse border-ops-cyan/35 bg-ops-cyan/10 text-ops-cyan' : approvalStatus === 'pending' ? 'border-ops-warning/35 bg-ops-warning/10 text-ops-warning' : 'border-ops-border/35 bg-ops-deep/45 text-ops-muted'}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-[9px] font-black uppercase tracking-[0.16em] text-ops-muted/45">{isCommandTool ? t('conversation.command') : t('conversation.toolCall')}</span>
            <code className={`truncate font-mono text-[12px] ${isRunning ? 'text-ops-cyan' : 'text-ops-text/82'}`}>
              {toolSummary || (isCommandTool ? t('conversation.unknownCommand') : t('conversation.unknownTool'))}
            </code>
            {targetLabel ? <span className="truncate text-[10px] font-semibold text-ops-muted/60">Target: {targetLabel}</span> : null}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(message ? !message.partial : !!endEvent) ? (
            <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.12em] ${exitCode === null || exitCode === 0 ? 'border-ops-green/25 bg-ops-green/8 text-ops-green' : 'border-ops-danger/30 bg-ops-danger/8 text-ops-danger'}`}>
              <div className={`h-1.5 w-1.5 rounded-full ${exitCode === null || exitCode === 0 ? 'bg-ops-green' : 'bg-ops-danger'}`} />
              {exitCode === null || exitCode === 0 ? t('conversation.success') : t('conversation.errorCode', { code: String(exitCode) })}
            </div>
          ) : approvalStatus ? (
            <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.12em] ${approvalStatus === 'approved' ? 'border-ops-green/25 bg-ops-green/8 text-ops-green' : approvalStatus === 'rejected' ? 'border-ops-danger/30 bg-ops-danger/8 text-ops-danger' : 'border-ops-warning/35 bg-ops-warning/10 text-ops-warning'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${approvalStatus === 'approved' ? 'bg-ops-green' : approvalStatus === 'rejected' ? 'bg-ops-danger' : 'animate-pulse bg-ops-warning'}`} />
              {approvalStatus === 'approved' ? t('conversation.authorized') : approvalStatus === 'rejected' ? t('conversation.denied') : t('conversation.needsApproval')}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-full border border-ops-cyan/30 bg-ops-cyan/8 px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.12em] text-ops-cyan">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-ops-cyan" />
              {t('conversation.running')}
            </div>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex h-7 w-7 items-center justify-center rounded-xl border border-ops-border/35 bg-ops-deep/45 text-ops-muted transition-colors hover:border-ops-cyan/35 hover:text-ops-cyan"
          >
            <svg 
              width="12" 
              height="12" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              className={`transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            >
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 flex flex-col gap-4 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex flex-col gap-1.5">
            <span className="text-[9px] font-black uppercase tracking-[0.16em] text-ops-muted/48">{isCommandTool ? t('conversation.commandPayload') : t('conversation.toolArgs')}</span>
            {!isCommandTool && (toolName || toolDisplayText || toolDescription) ? (
              <div className="rounded-2xl border border-ops-border/20 bg-ops-deep/45 px-4 py-3 text-[12px] leading-relaxed text-ops-text/82">
                {toolName ? <div><span className="font-bold text-ops-muted/70">{t('conversation.name')}:</span> {toolName}</div> : null}
                {toolDisplayText ? <div><span className="font-bold text-ops-muted/70">{t('conversation.display')}:</span> {toolDisplayText}</div> : null}
                {toolDescription ? <div><span className="font-bold text-ops-muted/70">{t('conversation.description')}:</span> {toolDescription}</div> : null}
              </div>
            ) : null}
            <code className="block whitespace-pre-wrap break-all rounded-2xl border border-ops-border/20 bg-ops-deep/80 px-4 py-3 font-mono text-[12px] leading-relaxed text-ops-text/90 shadow-[inset_0_1px_0_rgb(var(--ops-text)/0.04)]">
              {isCommandTool ? displayCommand : argsJson}
            </code>
          </div>

          {showApprovalActions && approvalStatus === 'pending' && (
            <section className="relative overflow-hidden rounded-[20px] border border-ops-warning/30 bg-[linear-gradient(135deg,rgb(var(--ops-warning)/0.13),rgb(var(--ops-panel)/0.74)_48%,rgb(var(--ops-deep)/0.86))] p-4 shadow-[0_18px_46px_rgb(var(--ops-bg)/0.16)]">
              <div className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-ops-warning/65 to-transparent" />
              <div className="mb-4 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-ops-warning/30 bg-ops-warning/12 text-ops-warning shadow-[0_0_24px_rgb(var(--ops-warning)/0.12)]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3 3.5 19h17L12 3Z" /><path d="M12 8v5" /><path d="M12 17h.01" /></svg>
                  </div>
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-warning">{t('conversation.riskCheckpoint')}</div>
                    <div className="mt-1 text-sm font-semibold text-ops-text">{t('conversation.needsOperatorApproval', { kind: isCommandTool ? t('conversation.commandKind') : t('conversation.toolCallKind') })}</div>
                  </div>
                </div>
                <span className="rounded-full border border-ops-warning/25 bg-ops-deep/45 px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.14em] text-ops-warning/80">{t('conversation.needsApproval')}</span>
              </div>

              {(message?.text || approvalEvent?.reason) && <div className="mb-4 rounded-2xl border border-ops-warning/15 bg-ops-deep/38 px-3 py-2 text-[12px] leading-relaxed text-ops-text/78">{message?.text || approvalEvent?.reason}</div>}

              {isCommandTool && showWhitelistOptions ? (
                <div className="mb-4 rounded-2xl border border-ops-border/20 bg-ops-deep/45 p-3">
                  <div className="mb-2 text-[10px] font-black uppercase tracking-[0.14em] text-ops-muted/68">{t('conversation.whitelistPrefix')}</div>
                  <div className="mb-3 flex flex-wrap gap-2">
                    {allowPrefixOptions.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={`rounded-full border px-3 py-1 font-mono text-[11px] transition-colors ${allowPrefix === option ? 'border-ops-cyan/45 bg-ops-cyan/12 text-ops-cyan' : 'border-ops-border/30 bg-ops-panel/30 text-ops-muted hover:text-ops-text'}`}
                        onClick={() => setAllowPrefix(option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                  <input
                    className="field-control h-9 w-full font-mono text-[12px]"
                    value={allowPrefix}
                    onChange={(event) => setAllowPrefix(event.target.value)}
                    placeholder={t('conversation.whitelistPrefixPlaceholder')}
                  />
                </div>
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-3">
                {isCommandTool ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (!showWhitelistOptions) {
                        setAllowPrefix(allowPrefixOptions[0] ?? '')
                        setShowWhitelistOptions(true)
                        return
                      }
                      onApprove?.(allowPrefix)
                    }}
                    className="rounded-full border border-ops-cyan/25 bg-ops-cyan/8 px-3.5 py-2 text-[11px] font-black uppercase tracking-[0.12em] text-ops-cyan transition-colors hover:border-ops-cyan/45 hover:bg-ops-cyan/14 disabled:cursor-not-allowed disabled:opacity-45"
                    disabled={showWhitelistOptions && !allowPrefix.trim()}
                  >
                    {showWhitelistOptions ? t('conversation.approveTrustPrefix') : t('conversation.trustCommandPrefix')}
                  </button>
                ) : <span />}
                <div className="flex items-center gap-2">
                  <button type="button" onClick={onReject} className="rounded-full border border-ops-danger/25 bg-ops-danger/8 px-4 py-2 text-[11px] font-black uppercase tracking-[0.12em] text-ops-danger transition-colors hover:border-ops-danger/45 hover:bg-ops-danger/12">{t('conversation.reject')}</button>
                  <button type="button" onClick={() => onApprove?.()} className="rounded-full border border-ops-warning/35 bg-ops-warning px-4 py-2 text-[11px] font-black uppercase tracking-[0.12em] text-ops-deep shadow-[0_0_28px_rgb(var(--ops-warning)/0.22)] transition-colors hover:bg-ops-warning/85">{t('conversation.approveOnce')}</button>
                </div>
              </div>
            </section>
          )}

          {hasExecutionResult && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[9px] font-bold tracking-widest text-ops-muted/60 uppercase">{t('conversation.executionOutput')}</span>
              <OutputBlock text={outputText || t('conversation.noOutput')} label={t('conversation.trace')} />
            </div>
          )}
        </div>
      )}

      {!isExpanded && hasExecutionResult && (
        <div className="mt-1.5 ml-9 flex items-center gap-2 overflow-hidden border-t border-ops-border/10 pt-1.5">
          <span className="shrink-0 text-[9px] font-bold tracking-[0.05em] text-ops-muted/40 uppercase">{t('conversation.output')}</span>
          <span className="truncate font-mono text-[11px] text-ops-muted/60">
            {outputText.split('\n').filter(l => l.trim()).pop() || outputText.slice(-100) || t('conversation.noOutput')}
          </span>
        </div>
      )}
    </div>
  )
}
