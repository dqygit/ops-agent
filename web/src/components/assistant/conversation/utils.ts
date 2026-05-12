import type { Group } from './types'

export function stripAnsi(text: string) {
  return text.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
}

export function stripJsonBlocks(text: string) {
  let result = text

  const markerIndex = result.indexOf('<FINAL_JSON>')
  if (markerIndex >= 0) {
    result = result.slice(0, markerIndex)
  }

  // Only strip blocks that are fully closed to avoid flickering during stream
  result = result.replace(/```json\s*[\s\S]*?```/gi, '')
  
  // More targeted JSON block stripping for common agent patterns
  const jsonPatterns = [
    /\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*?\}/g,
    /\[\s*\{\s*"(?:title|command|reason)"[\s\S]*?\}\s*\]/g
  ]

  for (const pattern of jsonPatterns) {
    result = result.replace(pattern, '')
  }

  // Handle trailing partial JSON blocks only if they look very likely to be the end-of-turn data
  // and we have some content before them.
  const jsonTailPatterns = [
    /\n\s*\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*$/,
    /\n\s*\[\s*\{[\s\S]*$/,
  ]

  for (const pattern of jsonTailPatterns) {
    // Only strip if there is content before the newline to avoid stripping the whole message
    if (result.includes('\n')) {
      result = result.replace(pattern, '')
    }
  }

  result = result
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim()
      if (!trimmed) return true
      // Don't strip lines that might be part of a markdown list or code block
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('1. ')) return true
      if (/^[\[{].*[\]}]$/.test(trimmed)) return false
      if (/^"(?:title|reason|risk_level|expected_output|command|decision|summary)"\s*:/.test(trimmed)) return false
      if (/^[\]}],?$/.test(trimmed)) return false
      return true
    })
    .join('\n')

  result = result
    .replace(/[，,、。；;:：\-\s]+$/g, '')
    .replace(/([，,、]){2,}/g, '$1')
    .replace(/\n{4,}/g, '\n\n\n')
    .replace(/\n{3,}/g, '\n\n')

  return result.trim()
}

export function sortAssistantGroups(groups: Group[]): Group[] {
  // Maintain the original order of events to ensure thinking, commands, and results
  // appear in the sequence they actually occurred.
  return groups
}

