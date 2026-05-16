import type { MCPServer, MCPTool } from '../../types/ops'
import type { MCPSectionProps } from './settingsTypes'

function statusClass(status: string) {
  if (status === 'ok') {
    return 'text-ops-emerald bg-ops-emerald/10 border-ops-emerald/20'
  }
  if (status === 'failed') {
    return 'text-red-400 bg-red-500/10 border-red-500/20'
  }
  return 'text-ops-muted bg-ops-border/10 border-ops-border/20'
}

function transportLabel(server: MCPServer) {
  return server.transport === 'httpSse' ? 'HTTP/SSE' : 'stdio'
}

function summarizeSchema(tool: MCPTool) {
  const properties = tool.inputSchema.properties
  if (properties && typeof properties === 'object' && !Array.isArray(properties)) {
    const keys = Object.keys(properties)
    return keys.length ? `schema: ${keys.slice(0, 6).join(', ')}${keys.length > 6 ? '…' : ''}` : 'schema: no properties'
  }
  return Object.keys(tool.inputSchema).length ? 'schema available' : 'schema: empty'
}

function ServerCard({ server, selected, saving, onSelect, onEdit, onDelete, onTest, onRefresh, onSetEnabled }: {
  server: MCPServer
  selected: boolean
  saving: boolean
  onSelect: (serverId: string) => void
  onEdit: (server: MCPServer) => void
  onDelete: (server: MCPServer) => void
  onTest: (server: MCPServer) => void
  onRefresh: (server: MCPServer) => void
  onSetEnabled: (server: MCPServer, enabled: boolean) => void
}) {
  const enableBlocked = !server.enabled && !server.lastRefreshSucceeded

  return (
    <article className={`rounded-2xl border p-5 shadow-sm transition-all duration-300 ${selected ? 'bg-ops-cyan/5 border-ops-cyan/30' : 'bg-ops-panel/40 border-ops-border/20 hover:border-ops-cyan/30 hover:bg-ops-panel/60'}`}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onSelect(server.id)}>
            <div className="flex flex-wrap items-center gap-3">
              <strong className="text-[13px] font-bold text-ops-text tracking-tight break-all">{server.name}</strong>
              <span className="px-2 py-0.5 text-[9px] font-bold tracking-widest rounded-md text-ops-cyan bg-ops-cyan/10 border border-ops-cyan/20">{transportLabel(server)}</span>
              <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest rounded-md border ${server.enabled ? 'text-ops-emerald bg-ops-emerald/10 border-ops-emerald/20' : 'text-ops-muted bg-ops-border/10 border-ops-border/20'}`}>{server.enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-medium tracking-wider text-ops-muted">
              <span className={`px-2 py-0.5 rounded-md border ${statusClass(server.connectionStatus)}`}>Connection: {server.connectionStatus}</span>
              <span className={`px-2 py-0.5 rounded-md border ${statusClass(server.discoveryStatus)}`}>Discovery: {server.discoveryStatus}</span>
              <span className="px-2 py-0.5 rounded-md border border-ops-border/20 bg-ops-deep/30">Tools: {server.tools.length}</span>
            </div>
          </button>
          <div className="flex flex-col items-end gap-2">
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button type="button" className="button h-8 px-3 text-[10px]" onClick={() => onSetEnabled(server, !server.enabled)} disabled={saving || enableBlocked} title={enableBlocked ? 'Test or refresh successfully before enabling.' : undefined}>{server.enabled ? 'Disable' : 'Enable'}</button>
              <button type="button" className="button h-8 px-3 text-[10px]" onClick={() => onTest(server)} disabled={saving}>Test</button>
              <button type="button" className="button h-8 px-3 text-[10px]" onClick={() => onRefresh(server)} disabled={saving}>Refresh</button>
              <button type="button" className="button h-8 px-3 text-[10px]" onClick={() => onEdit(server)}>Edit</button>
              <button type="button" className="button button-danger h-8 px-3 text-[10px]" onClick={() => onDelete(server)} disabled={saving}>Delete</button>
            </div>
            {enableBlocked ? <div className="max-w-[220px] text-right text-[10px] leading-4 text-ops-muted">Test or refresh successfully before enabling.</div> : null}
          </div>
        </div>
        {server.lastError ? (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-[11px] text-red-200 break-words">{server.lastError}</div>
        ) : null}
      </div>
    </article>
  )
}

export function McpSection({
  servers,
  serverForm,
  showServerForm,
  editingServer,
  selectedServerId,
  loading,
  error,
  saving,
  testResult,
  onRetry,
  onStartCreate,
  onStartEdit,
  onStartDelete,
  onSelectServer,
  onFormChange,
  onCancelForm,
  onSave,
  onTest,
  onRefresh,
  onSetEnabled,
  onUpdateTool,
}: MCPSectionProps) {
  const selectedServer = servers.find((server) => server.id === selectedServerId) ?? servers[0] ?? null

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
        <div>
          <h4 className="text-[14px] font-bold tracking-[0.15em] text-ops-text">MCP Servers</h4>
          <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">Manage tool servers, discovery, and per-tool approval policies.</p>
        </div>
        <button type="button" className="button button-primary" onClick={onStartCreate}>Add MCP Server</button>
      </div>

      {loading ? <div className="flex items-center justify-center h-40 text-ops-muted text-sm">Loading MCP servers...</div> : null}

      {!loading && error ? (
        <div className="p-4 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between gap-4">
          <span>{error}</span>
          <button type="button" className="px-3 py-1.5 rounded-md bg-ops-border/20 hover:bg-ops-border/30 transition-colors text-ops-text text-sm" onClick={onRetry}>Retry</button>
        </div>
      ) : null}

      {!loading && !error && showServerForm ? (
        <form className="bg-ops-deep/40 p-6 rounded-2xl border border-ops-border/20 grid grid-cols-2 gap-5 mt-2 animate-in slide-in-from-top-4 duration-300" onSubmit={onSave}>
          <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70">
            Server Name
            <input className="field-control" value={serverForm.name} onChange={(event) => onFormChange({ ...serverForm, name: event.target.value })} placeholder="e.g. filesystem" required />
          </label>
          <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70">
            Transport
            <select className="field-control" value={serverForm.transport} onChange={(event) => onFormChange({ ...serverForm, transport: event.target.value === 'httpSse' ? 'httpSse' : 'stdio' })}>
              <option value="stdio">stdio</option>
              <option value="httpSse">HTTP/SSE</option>
            </select>
          </label>

          {serverForm.transport === 'stdio' ? (
            <>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70 col-span-2">
                Command
                <input className="field-control font-mono" value={serverForm.command} onChange={(event) => onFormChange({ ...serverForm, command: event.target.value })} placeholder="npx" required />
              </label>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70 col-span-2">
                Args (one per line)
                <textarea className="field-control min-h-[84px] font-mono" value={serverForm.args} onChange={(event) => onFormChange({ ...serverForm, args: event.target.value })} placeholder="-y&#10;@modelcontextprotocol/server-filesystem" rows={4} />
              </label>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70 col-span-2">
                Env JSON
                <textarea className="field-control min-h-[84px] font-mono" value={serverForm.env} onChange={(event) => onFormChange({ ...serverForm, env: event.target.value })} placeholder={'{\n  "TOKEN": "redacted"\n}'} rows={4} />
              </label>
            </>
          ) : (
            <>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70 col-span-2">
                URL
                <input className="field-control font-mono" value={serverForm.url} onChange={(event) => onFormChange({ ...serverForm, url: event.target.value })} placeholder="https://example.com/sse" required />
              </label>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70 col-span-2">
                Headers JSON
                <textarea className="field-control min-h-[84px] font-mono" value={serverForm.headers} onChange={(event) => onFormChange({ ...serverForm, headers: event.target.value })} placeholder={'{\n  "Authorization": "Bearer redacted"\n}'} rows={4} />
              </label>
              <label className="flex flex-col gap-2 text-[11px] font-bold tracking-widest text-ops-muted/70">
                Timeout (s)
                <input className="field-control font-mono" type="number" min="1" value={serverForm.timeoutSeconds} onChange={(event) => onFormChange({ ...serverForm, timeoutSeconds: event.target.value })} required />
              </label>
            </>
          )}

          {testResult ? <div className="col-span-2 p-4 text-[11px] font-mono text-ops-cyan bg-ops-cyan/10 border border-ops-cyan/20 rounded-xl break-all animate-in fade-in duration-300">{testResult}</div> : null}
          <div className="flex items-center justify-end gap-3 mt-4 pt-6 border-t border-ops-border/20 col-span-2">
            <button type="button" className="button px-6" onClick={onCancelForm}>Cancel</button>
            <button type="submit" className="button button-primary px-8" disabled={saving}>{saving ? 'Processing...' : editingServer ? 'Save Server' : 'Create Server'}</button>
          </div>
        </form>
      ) : null}

      {!loading && !error && servers.length === 0 ? (
        <div className="text-center py-10 text-ops-muted text-sm bg-ops-panel/20 rounded-lg border border-ops-border/10 border-dashed">No MCP servers configured.</div>
      ) : !loading && !error ? (
        <div className="flex flex-col gap-3">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              selected={selectedServer?.id === server.id}
              saving={saving}
              onSelect={onSelectServer}
              onEdit={onStartEdit}
              onDelete={onStartDelete}
              onTest={onTest}
              onRefresh={onRefresh}
              onSetEnabled={onSetEnabled}
            />
          ))}
        </div>
      ) : null}

      {!loading && !error && selectedServer ? (
        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between pb-3 border-b border-ops-border/20">
            <div>
              <h5 className="text-[12px] font-bold tracking-[0.14em] text-ops-text">Tools: {selectedServer.name}</h5>
              <p className="text-[10px] text-ops-muted mt-1">Original and exposed names are shown for collision-safe tool routing.</p>
            </div>
          </div>
          {selectedServer.tools.length === 0 ? (
            <div className="text-center py-6 text-ops-muted text-sm bg-ops-panel/20 rounded-lg border border-ops-border/10 border-dashed">No tools discovered for this server.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {selectedServer.tools.map((tool) => (
                <article key={tool.id} className="rounded-2xl border border-ops-border/20 bg-ops-panel/40 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <strong className="text-[12px] text-ops-text break-all">{tool.exposedName}</strong>
                        <span className="text-[10px] text-ops-muted font-mono break-all">original: {tool.originalName}</span>
                        <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest rounded-md border ${tool.enabled ? 'text-ops-emerald bg-ops-emerald/10 border-ops-emerald/20' : 'text-ops-muted bg-ops-border/10 border-ops-border/20'}`}>{tool.enabled ? 'Enabled' : 'Disabled'}</span>
                      </div>
                      <p className="mt-2 text-[11px] leading-5 text-ops-muted">{tool.description || 'No description provided.'}</p>
                      <p className="mt-1 text-[10px] font-mono text-ops-muted/80">{summarizeSchema(tool)}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="flex items-center gap-2 text-[10px] font-bold tracking-widest text-ops-muted/70">
                        <input type="checkbox" className="accent-ops-cyan w-4 h-4 rounded-md" checked={tool.enabled} onChange={(event) => onUpdateTool(tool, { enabled: event.target.checked })} disabled={saving} />
                        Enabled
                      </label>
                      <select className="field-control h-8 py-0 text-[10px]" value={tool.approvalPolicy} onChange={(event) => onUpdateTool(tool, { approvalPolicy: event.target.value === 'allow' ? 'allow' : event.target.value === 'deny' ? 'deny' : 'ask' })} disabled={saving}>
                        <option value="ask">Ask approval</option>
                        <option value="allow">Allow</option>
                        <option value="deny">Deny</option>
                      </select>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  )
}
