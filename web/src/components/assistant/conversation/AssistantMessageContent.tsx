import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PROSE_CLASS } from './types'
import { stripJsonBlocks } from './utils'

type AssistantMessageContentProps = {
  content: string
  isStreaming?: boolean
}

export function AssistantMessageContent({ content, isStreaming }: AssistantMessageContentProps) {
  const processedContent = useMemo(() => stripJsonBlocks(content), [content])

  // Simple parser for <think>...</think>
  const parsed = useMemo(() => {
    const thinkStart = processedContent.indexOf('<think>')
    const thinkEnd = processedContent.indexOf('</think>')

    if (thinkStart !== -1) {
      if (thinkEnd !== -1) {
        // Full block found
        const thinking = processedContent.slice(thinkStart + 7, thinkEnd).trim()
        const output = processedContent.slice(thinkEnd + 8).trim()
        return { thinking, output, isThinkingOnly: false, isStillThinking: false }
      } else {
        // Open block found
        const thinking = processedContent.slice(thinkStart + 7).trim()
        return { thinking, output: '', isThinkingOnly: true, isStillThinking: true }
      }
    }

    return { thinking: '', output: processedContent, isThinkingOnly: false, isStillThinking: false }
  }, [processedContent])

  const [isThinkExpanded, setIsThinkExpanded] = useState(true)

  if (!parsed.thinking && !parsed.output) return null

  return (
    <div className="flex flex-col gap-3 w-full">
      {parsed.thinking && (
        <div className="flex flex-col gap-2">
          <button
            onClick={() => setIsThinkExpanded(!isThinkExpanded)}
            className="flex items-center gap-2 text-[10px] font-bold tracking-[0.1em] text-ops-cyan/60 hover:text-ops-cyan transition-colors uppercase w-fit"
          >
            <div className={`flex h-4 w-4 items-center justify-center rounded border border-ops-cyan/30 bg-ops-cyan/5 transition-transform duration-200 ${isThinkExpanded ? 'rotate-180' : ''}`}>
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m6 9 6 6 6-6"/></svg>
            </div>
            <span>{parsed.isStillThinking ? 'Thinking in progress...' : 'Thought Process'}</span>
            {parsed.isStillThinking && isStreaming && <span className="h-1 w-1 rounded-full bg-ops-cyan animate-pulse" />}
          </button>
          
          {isThinkExpanded && (
            <div className="relative overflow-hidden rounded-xl border border-ops-border/20 bg-ops-panel/40 px-4 py-3 text-[13px] leading-relaxed text-ops-muted italic animate-in fade-in slide-in-from-top-1 duration-200">
              <div className="absolute top-0 left-0 h-full w-0.5 bg-ops-cyan/30" />
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.thinking}</ReactMarkdown>
              {parsed.isStillThinking && isStreaming && (
                <span className="ml-1 inline-block h-3.5 w-1.5 animate-pulse align-[-2px] rounded-sm bg-ops-cyan/85" />
              )}
            </div>
          )}
        </div>
      )}

      {parsed.output && (
        <div className={PROSE_CLASS}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.output}</ReactMarkdown>
          {isStreaming && !parsed.isStillThinking && (
            <span className="ml-1 inline-block h-3.5 w-1.5 animate-pulse align-[-2px] rounded-sm bg-ops-cyan/85" />
          )}
        </div>
      )}
    </div>
  )
}
