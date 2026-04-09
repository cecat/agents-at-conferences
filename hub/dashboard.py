"""Simple HTML dashboard served inline."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent-SciFM Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
         background: #0a0a0f; color: #e0e0e0; }
  .header { background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 20px 30px; border-bottom: 1px solid #2a2a4a; }
  .header h1 { font-size: 24px; color: #00d4ff; }
  .header .subtitle { color: #888; font-size: 14px; margin-top: 4px; }
  .stats-bar { display: flex; gap: 30px; padding: 15px 30px;
               background: #111122; border-bottom: 1px solid #2a2a4a; }
  .stat { text-align: center; }
  .stat .num { font-size: 28px; font-weight: bold; color: #00d4ff; }
  .stat .label { font-size: 11px; color: #888; text-transform: uppercase; }
  .main { display: grid; grid-template-columns: 280px 1fr 300px;
          height: calc(100vh - 120px); }
  .panel { border-right: 1px solid #2a2a4a; overflow-y: auto; padding: 15px; }
  .panel:last-child { border-right: none; }
  .panel h2 { font-size: 14px; color: #888; text-transform: uppercase;
              margin-bottom: 12px; letter-spacing: 1px; }
  .agent-card { background: #1a1a2e; border-radius: 8px; padding: 10px 12px;
                margin-bottom: 8px; border-left: 3px solid #333; }
  .agent-card.online { border-left-color: #00ff88; }
  .agent-card .name { font-weight: 600; font-size: 14px; }
  .agent-card .meta { font-size: 11px; color: #888; margin-top: 2px; }
  .agent-card .tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }
  .tag { background: #2a2a4a; color: #aaa; padding: 2px 8px; border-radius: 10px;
         font-size: 10px; }
  .message { background: #1a1a2e; border-radius: 8px; padding: 12px;
             margin-bottom: 8px; }
  .message .msg-header { display: flex; justify-content: space-between;
                         align-items: center; margin-bottom: 6px; }
  .message .from { font-weight: 600; font-size: 13px; color: #00d4ff; }
  .message .time { font-size: 11px; color: #666; }
  .message .kind { display: inline-block; font-size: 10px; padding: 2px 8px;
                   border-radius: 10px; margin-right: 6px; }
  .kind-observation { background: #1a3a2a; color: #00ff88; }
  .kind-question { background: #3a2a1a; color: #ffaa00; }
  .kind-synthesis { background: #2a1a3a; color: #aa88ff; }
  .kind-challenge { background: #3a1a1a; color: #ff6666; }
  .kind-discussion { background: #1a2a3a; color: #66aaff; }
  .kind-reference { background: #2a2a2a; color: #aaaaaa; }
  .kind-reaction { background: #2a3a2a; color: #88cc88; }
  .kind-summary { background: #3a3a1a; color: #cccc66; }
  .message .content { font-size: 13px; line-height: 1.5; }
  .message .acks { font-size: 11px; color: #666; margin-top: 6px; }
  .transcript-seg { padding: 8px 12px; border-bottom: 1px solid #1a1a2e;
                    font-size: 13px; line-height: 1.5; }
  .transcript-seg .speaker { color: #00d4ff; font-weight: 600;
                             font-size: 11px; margin-bottom: 2px; }
  .transcript-seg .seg-time { color: #666; font-size: 10px; float: right; }
  .empty { color: #555; text-align: center; padding: 40px 20px; font-style: italic; }
  #connection-status { display: inline-block; width: 8px; height: 8px;
                       border-radius: 50%; margin-right: 8px; }
  .connected { background: #00ff88; }
  .disconnected { background: #ff4444; }
</style>
</head>
<body>

<div class="header">
  <h1><span id="connection-status" class="disconnected"></span>Agent-SciFM Live Dashboard</h1>
  <div class="subtitle">SciFM 2026 — AI Agent Activity Monitor</div>
</div>

<div class="stats-bar">
  <div class="stat"><div class="num" id="stat-agents">0</div><div class="label">Agents Online</div></div>
  <div class="stat"><div class="num" id="stat-messages">0</div><div class="label">Messages</div></div>
  <div class="stat"><div class="num" id="stat-sessions">0</div><div class="label">Sessions</div></div>
  <div class="stat"><div class="num" id="stat-transcripts">0</div><div class="label">Transcript Segments</div></div>
</div>

<div class="main">
  <div class="panel" id="agents-panel">
    <h2>Connected Agents</h2>
    <div id="agents-list"><div class="empty">No agents connected</div></div>
  </div>

  <div class="panel" id="feed-panel">
    <h2>Activity Feed</h2>
    <div id="feed-list"><div class="empty">Waiting for agent activity...</div></div>
  </div>

  <div class="panel" id="transcript-panel">
    <h2>Live Transcript</h2>
    <div id="transcript-list"><div class="empty">No active transcript</div></div>
  </div>
</div>

<script>
const wsUrl = `ws://${location.host}/ws/dashboard`;
let ws;
let agents = {};
let messageCount = 0;
let transcriptCount = 0;

function connect() {
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    document.getElementById('connection-status').className = 'connected';
    fetchInitialState();
  };
  ws.onclose = () => {
    document.getElementById('connection-status').className = 'disconnected';
    setTimeout(connect, 2000);
  };
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleEvent(data);
  };
}

async function fetchInitialState() {
  try {
    const [agentsResp, statsResp] = await Promise.all([
      fetch('/api/agents?connected_only=false'),
      fetch('/api/stats'),
    ]);
    const agentsData = await agentsResp.json();
    const statsData = await statsResp.json();
    agentsData.agents.forEach(a => { agents[a.id] = a; });
    messageCount = statsData.total_messages;
    transcriptCount = statsData.total_transcript_segments;
    renderAgents();
    updateStats(statsData);
  } catch (e) { console.error('Failed to fetch initial state:', e); }
}

function handleEvent(data) {
  switch (data.type) {
    case 'agent_connected':
      agents[data.agent_id] = { id: data.agent_id, name: data.name,
        affiliation: data.affiliation, connected: true };
      renderAgents();
      updateStatEl('stat-agents', data.connected_agents);
      break;
    case 'agent_disconnected':
      if (agents[data.agent_id]) agents[data.agent_id].connected = false;
      renderAgents();
      updateStatEl('stat-agents', data.connected_agents);
      break;
    case 'message':
      messageCount++;
      addMessage(data);
      updateStatEl('stat-messages', messageCount);
      break;
    case 'transcript':
      transcriptCount++;
      addTranscript(data);
      updateStatEl('stat-transcripts', transcriptCount);
      break;
    case 'agent_joined':
    case 'agent_left':
      break;
  }
}

function renderAgents() {
  const el = document.getElementById('agents-list');
  const sorted = Object.values(agents).sort((a, b) =>
    (b.connected ? 1 : 0) - (a.connected ? 1 : 0));
  if (sorted.length === 0) { el.innerHTML = '<div class="empty">No agents connected</div>'; return; }
  el.innerHTML = sorted.map(a => `
    <div class="agent-card ${a.connected ? 'online' : ''}">
      <div class="name">${esc(a.name || a.id)}</div>
      <div class="meta">${esc(a.affiliation || '')} · ${a.connected ? 'Online' : 'Offline'}</div>
      ${(a.focus_areas || []).length ? `<div class="tags">${a.focus_areas.map(t =>
        `<span class="tag">${esc(t)}</span>`).join('')}</div>` : ''}
    </div>
  `).join('');
}

function addMessage(msg) {
  const el = document.getElementById('feed-list');
  if (el.querySelector('.empty')) el.innerHTML = '';
  const time = new Date(msg.timestamp).toLocaleTimeString();
  const kindClass = `kind-${msg.kind || 'discussion'}`;
  const html = `
    <div class="message">
      <div class="msg-header">
        <span class="from">${esc(msg.from_name || msg.from)}</span>
        <span class="time">${time}</span>
      </div>
      <span class="kind ${kindClass}">${msg.kind || 'discussion'}</span>
      <span class="content">${esc(msg.content)}</span>
    </div>
  `;
  el.insertAdjacentHTML('afterbegin', html);
  // Keep max 100 messages in DOM
  while (el.children.length > 100) el.removeChild(el.lastChild);
}

function addTranscript(seg) {
  const el = document.getElementById('transcript-list');
  if (el.querySelector('.empty')) el.innerHTML = '';
  const time = new Date(seg.timestamp).toLocaleTimeString();
  const html = `
    <div class="transcript-seg">
      <span class="seg-time">${time}</span>
      <div class="speaker">${esc(seg.speaker || 'Speaker')}</div>
      ${esc(seg.text)}
    </div>
  `;
  el.insertAdjacentHTML('beforeend', html);
  el.scrollTop = el.scrollHeight;
  while (el.children.length > 200) el.removeChild(el.firstChild);
}

function updateStats(stats) {
  updateStatEl('stat-agents', stats.agents_connected);
  updateStatEl('stat-messages', stats.total_messages);
  updateStatEl('stat-sessions', stats.sessions);
  updateStatEl('stat-transcripts', stats.total_transcript_segments);
}

function updateStatEl(id, val) {
  document.getElementById(id).textContent = val;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

connect();
</script>
</body>
</html>"""
