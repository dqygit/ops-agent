import { useState, useEffect } from 'react'
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
  onApprove?: () => void
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
  const [isExpanded, setIsExpanded] = useState(false)

  // Derived state from AgentMessage or Legacy events
  const rawCommand = message?.toolCall?.command || (startEvent as any)?.command || approvalEvent?.command || ''
  
  // Parse command: if it's JSON like {"command":"lshw -short"}, extract the actual command
  const { displayCommand, fullCommand } = (() => {
    if (!rawCommand) return { displayCommand: '', fullCommand: '' }
    
    // Try to parse as JSON
    try {
      const parsed = JSON.parse(rawCommand)
      if (parsed && typeof parsed === 'object' && 'command' in parsed) {
        // It's a JSON object with a command field
        return {
          displayCommand: parsed.command,
          fullCommand: rawCommand
        }
      }
    } catch {
      // Not JSON, use as-is
    }
    
    return { displayCommand: rawCommand, fullCommand: rawCommand }
  })()
  
  const outputText = message?.toolOutput || chunkEvents.map((event) => event.text).join('')
  const exitCode = message ? message.exitCode : ((endEvent as any)?.exitCode ?? (endEvent as any)?.exit_code)
  
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
    <div className={`group/card my-2 rounded-xl border border-ops-border/30 bg-ops-panel/40 shadow-sm transition-all duration-300 ${isExpanded ? 'p-4' : 'p-2 px-3'}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-3 min-w-0">
          <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded border transition-colors ${isRunning ? 'animate-pulse border-ops-cyan/40 bg-ops-cyan/10 text-ops-cyan' : 'border-ops-border/40 bg-ops-deep/40 text-ops-muted'}`}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
          </div>
          
          <div className="flex flex-1 items-center gap-3 min-w-0">
            <span className="shrink-0 text-[10px] font-bold tracking-[0.1em] text-ops-muted uppercase whitespace-nowrap">CMD</span>
            <code className={`flex-1 truncate font-mono text-[12px] ${isRunning ? 'text-ops-cyan' : 'text-ops-text/80'}`}>
              {displayCommand || (message?.toolCall?.name ? `Call: ${message.toolCall.name}` : 'Unknown Command')}
            </code>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(message ? !message.partial : !!endEvent) ? (
            <div className={`flex items-center gap-1.5 rounded border px-2 py-0.5 text-[9px] font-bold tracking-[0.1em] ${exitCode === null || exitCode === 0 ? 'text-ops-emerald border-ops-emerald/30 bg-ops-emerald/5' : 'text-ops-danger border-ops-danger/30 bg-ops-danger/5'}`}>
              <div className={`h-1 w-1 rounded-full ${exitCode === null || exitCode === 0 ? 'bg-ops-emerald' : 'bg-ops-danger'}`} />
              {exitCode === null || exitCode === 0 ? 'Success' : `Error ${exitCode}`}
            </div>
          ) : approvalStatus ? (
            <div className={`flex items-center gap-1.5 rounded border px-2 py-0.5 text-[9px] font-bold tracking-[0.1em] ${approvalStatus === 'approved' ? 'border-ops-emerald/30 bg-ops-emerald/5 text-ops-emerald' : approvalStatus === 'rejected' ? 'border-ops-danger/30 bg-ops-danger/5 text-ops-danger' : 'border-ops-warning/30 bg-ops-warning/5 text-ops-warning'}`}>
              <span className={`h-1 w-1 rounded-full ${approvalStatus === 'approved' ? 'bg-ops-emerald' : approvalStatus === 'rejected' ? 'bg-ops-danger' : 'bg-ops-warning animate-pulse'}`} />
              {approvalStatus === 'approved' ? 'Authorized' : approvalStatus === 'rejected' ? 'Denied' : 'Pending'}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded border border-ops-cyan/30 bg-ops-cyan/5 px-2 py-0.5 text-[9px] font-bold tracking-[0.1em] text-ops-cyan">
              <span className="h-1 w-1 rounded-full bg-ops-cyan animate-ping" />
              Running
            </div>
          )}

          <button 
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex h-6 w-6 items-center justify-center rounded border border-ops-border/40 bg-ops-deep/40 text-ops-muted hover:border-ops-cyan/40 hover:text-ops-cyan transition-colors"
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
            <span className="text-[9px] font-bold tracking-widest text-ops-muted/60 uppercase">Command</span>
            <div className="relative">
              <code className="block rounded-lg border border-ops-border/20 bg-ops-deep px-3 py-2 text-[12px] text-ops-text/90 font-mono shadow-inner border-l-2 border-l-ops-cyan/60 whitespace-pre-wrap break-all">
                {displayCommand || JSON.stringify(message?.toolCall?.args)}
              </code>
            </div>
          </div>

          {showApprovalActions && approvalStatus === 'pending' && (
            <div className="rounded-lg border border-ops-warning/30 bg-ops-warning/5 p-3 border-l-2 border-l-ops-warning/60">
              <div className="mb-2 text-[10px] font-bold tracking-widest text-ops-warning uppercase">Authorization Required</div>
              {(message?.text || approvalEvent?.reason) && <div className="mb-3 text-[12px] text-ops-text/80 italic border-l border-ops-warning/30 pl-3">{message?.text || approvalEvent?.reason}</div>}
              <div className="flex items-center justify-end gap-2">
                <button onClick={onReject} className="button-mini button-mini-danger">Reject</button>
                <button onClick={onApprove} className="button-mini button-mini-primary shadow-glow">Authorize</button>
              </div>
            </div>
          )}

          {outputText && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[9px] font-bold tracking-widest text-ops-muted/60 uppercase">Execution Output</span>
              <OutputBlock text={outputText} label="Trace" />
            </div>
          )}
        </div>
      )}

      {!isExpanded && outputText && (
        <div className="mt-1.5 ml-9 flex items-center gap-2 overflow-hidden border-t border-ops-border/10 pt-1.5">
          <span className="shrink-0 text-[9px] font-bold tracking-[0.05em] text-ops-muted/40 uppercase">Output:</span>
          <span className="truncate font-mono text-[11px] text-ops-muted/60">
            {outputText.split('\n').filter(l => l.trim()).pop() || outputText.slice(-100)}
          </span>
        </div>
      )}
    </div>
  )
}
