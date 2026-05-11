import { useEffect, useRef } from 'react'
import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'

type TerminalOutputProps = {
  sessionKey: string
  output: string
  onInput: (data: string) => void
  onResize: (cols: number, rows: number) => void
}

function stripReplayControlSequences(value: string) {
  return value
    .replace(/\u001b\[c/g, '')
    .replace(/\u001b\[\?1004h/g, '')
    .replace(/\u001b\[\?1004l/g, '')
    .replace(/\u001b\[\?9001h/g, '')
    .replace(/\u001b\[\?9001l/g, '')
}

export function TerminalOutput({ sessionKey, output, onInput, onResize }: TerminalOutputProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const terminalHostRef = useRef<HTMLDivElement | null>(null)
  const terminalRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const writtenLengthRef = useRef(0)
  const currentSessionKeyRef = useRef(sessionKey)
  const replayingRef = useRef(false)
  const onInputRef = useRef(onInput)
  const onResizeRef = useRef(onResize)
  const outputRef = useRef(output)
  const sessionKeyRef = useRef(sessionKey)
  const lastSentInputRef = useRef<{ value: string; timestamp: number } | null>(null)

  useEffect(() => {
    onInputRef.current = onInput
    onResizeRef.current = onResize
    outputRef.current = output
    sessionKeyRef.current = sessionKey
  }, [onInput, onResize, output, sessionKey])

  const emitInput = (data: string) => {
    if (replayingRef.current || /^\u001b\[(I|O|\?1;2c)$/.test(data)) {
      return
    }

    onInputRef.current(data)
  }

  // Initialize terminal
  useEffect(() => {
    if (terminalHostRef.current === null) {
      return
    }

    const terminal = new Terminal({
      cursorBlink: true,
      fontFamily: 'Cascadia Code, JetBrains Mono, Consolas, monospace',
      fontSize: 13,
      theme: {
        background: '#0B0F19',
        foreground: '#F1F5F9',
        cursor: '#06B6D4',
        selectionBackground: 'rgba(6, 182, 212, 0.3)',
        black: '#1E293B',
        red: '#EF4444',
        green: '#10B981',
        yellow: '#F59E0B',
        blue: '#3B82F6',
        magenta: '#8B5CF6',
        cyan: '#06B6D4',
        white: '#F1F5F9',
        brightBlack: '#475569',
        brightRed: '#F87171',
        brightGreen: '#34D399',
        brightYellow: '#FBBF24',
        brightBlue: '#60A5FA',
        brightMagenta: '#A78BFA',
        brightCyan: '#22D3EE',
        brightWhite: '#FFFFFF',
      },
    })
    const fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    terminal.open(terminalHostRef.current)
    
    const helperTextarea = terminalHostRef.current.querySelector('textarea') as HTMLTextAreaElement | null
    
    requestAnimationFrame(() => {
      fitAddon.fit()
      onResizeRef.current(terminal.cols, terminal.rows)

      if (outputRef.current.length > 0) {
        replayingRef.current = true
        terminal.write(stripReplayControlSequences(outputRef.current))
        writtenLengthRef.current = outputRef.current.length
        queueMicrotask(() => {
          replayingRef.current = false
        })
      }
    })

    terminal.onData((data) => emitInput(data))

    const handleResize = () => {
      fitAddon.fit()
      onResizeRef.current(terminal.cols, terminal.rows)
    }

    window.addEventListener('resize', handleResize)
    terminalRef.current = terminal
    fitAddonRef.current = fitAddon

    return () => {
      window.removeEventListener('resize', handleResize)
      terminal.dispose()
      terminalRef.current = null
      fitAddonRef.current = null
      writtenLengthRef.current = 0
    }
  }, [])

  // Handle session change and output updates
  useEffect(() => {
    const terminal = terminalRef.current
    const fitAddon = fitAddonRef.current
    if (terminal === null || fitAddon === null) {
      return
    }

    // If session has changed, clear and reset
    if (currentSessionKeyRef.current !== sessionKey) {
      terminal.clear()
      terminal.reset()
      writtenLengthRef.current = 0
      currentSessionKeyRef.current = sessionKey
      
      if (output.length > 0) {
        replayingRef.current = true
        terminal.write(stripReplayControlSequences(output))
        writtenLengthRef.current = output.length
        queueMicrotask(() => {
          replayingRef.current = false
        })
      }
      
      requestAnimationFrame(() => {
        fitAddon.fit()
        onResizeRef.current(terminal.cols, terminal.rows)
      })
      return
    }

    // If output is shorter than what we've written, the buffer was probably reset on the server
    if (output.length < writtenLengthRef.current) {
      terminal.clear()
      writtenLengthRef.current = 0
    }

    // Incremental write
    const nextChunk = output.slice(writtenLengthRef.current)
    if (nextChunk.length > 0) {
      terminal.write(nextChunk)
      writtenLengthRef.current = output.length
    }
  }, [sessionKey, output])

  return (
    <div
      ref={containerRef}
      className="relative flex-1 w-full overflow-hidden bg-ops-bg p-3 focus:outline-none"
      aria-label="Terminal Session"
      onMouseDown={() => {
        terminalRef.current?.focus()
      }}
      tabIndex={0}
    >
      <div ref={terminalHostRef} className="w-full h-full" />
    </div>
  )
}
