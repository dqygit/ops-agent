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
  const lastSentInputRef = useRef<{ value: string; timestamp: number } | null>(null)

  useEffect(() => {
    onInputRef.current = onInput
    onResizeRef.current = onResize
  }, [onInput, onResize])

  const emitInput = (data: string) => {
    if (replayingRef.current || /^\u001b\[(I|O|\?1;2c)$/.test(data)) {
      return
    }

    const now = Date.now()
    const lastInput = lastSentInputRef.current
    if (lastInput !== null && lastInput.value === data && now - lastInput.timestamp < 20) {
      return
    }
    lastSentInputRef.current = { value: data, timestamp: now }
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
      convertEol: true,
      theme: {
        background: '#050807',
        foreground: '#d7e4dd',
        cursor: '#84cc16',
        selectionBackground: 'rgba(132, 204, 22, 0.22)',
      },
    })
    const fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    terminal.open(terminalHostRef.current)
    
    const helperTextarea = terminalHostRef.current.querySelector('textarea') as HTMLTextAreaElement | null
    
    requestAnimationFrame(() => {
      fitAddon.fit()
      onResizeRef.current(terminal.cols, terminal.rows)
    })

    terminal.onData((data) => emitInput(data))

    const handleNativeKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return
      }

      if (event.key === 'Enter') {
        event.preventDefault()
        emitInput('\r')
        return
      }

      if (event.key === 'Backspace') {
        event.preventDefault()
        emitInput('\u007f')
        return
      }

      if (event.key === 'Tab') {
        event.preventDefault()
        emitInput('\t')
        return
      }

      if (event.key.length === 1) {
        event.preventDefault()
        emitInput(event.key)
      }
    }

    helperTextarea?.addEventListener('keydown', handleNativeKeyDown)

    const handleResize = () => {
      fitAddon.fit()
      onResizeRef.current(terminal.cols, terminal.rows)
    }

    window.addEventListener('resize', handleResize)
    terminalRef.current = terminal
    fitAddonRef.current = fitAddon

    return () => {
      helperTextarea?.removeEventListener('keydown', handleNativeKeyDown)
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
      fitAddon.fit()
    }
  }, [sessionKey, output])

  return (
    <div
      ref={containerRef}
      className="relative flex-1 w-full overflow-hidden bg-[#050807] p-2 focus:outline-none"
      aria-label="终端输出"
      onMouseDown={() => {
        terminalRef.current?.focus()
      }}
      tabIndex={0}
    >
      <div ref={terminalHostRef} className="w-full h-full" />
    </div>
  )
}
