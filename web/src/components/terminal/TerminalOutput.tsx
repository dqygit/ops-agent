type TerminalOutputProps = {
  output: string
}

export function TerminalOutput({ output }: TerminalOutputProps) {
  return (
    <div className="terminal-view" aria-label="Terminal output">
      <pre>{output}</pre>
    </div>
  )
}
