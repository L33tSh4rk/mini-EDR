// logica do dashboard: conexao websocket, render do dom e envio de ordens

// estado local dos agentes conhecidos (agent_id -> dados)
const agents = new Map();
// grupos de alertas: agente+pid no mesmo card (groupKey -> grupo)
const alertGroups = new Map();
// indice auxiliar: alert_id -> groupKey (para remocao quando resolvido)
const alertIndex = new Map();
// socket atual
let ws = null;

// referencias do dom
const el = {
  agentList: document.getElementById("agent-list"),
  alertList: document.getElementById("alert-list"),
  onlineCount: document.getElementById("online-count"),
  alertCount: document.getElementById("alert-count"),
  agentTotal: document.getElementById("agent-total"),
  conn: document.getElementById("conn"),
  connText: document.getElementById("conn-text"),
};

// abre o canal de tempo real com a api
function connect_websocket() {
  const url = `ws://${location.host}/ws`;
  ws = new WebSocket(url);

  ws.onopen = () => setConnection(true);
  ws.onclose = () => {
    // marca offline e reagenda reconexao
    setConnection(false);
    setTimeout(connect_websocket, 2000);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (event) => {
    // despacha o frame conforme o tipo
    let frame;
    try { frame = JSON.parse(event.data); } catch { return; }
    routeFrame(frame);
  };
}

// roteia frames de entrada por frame_type
function routeFrame(frame) {
  switch (frame.frame_type) {
    case "agent_list": frame.data.forEach(upsertAgent); renderAgents(); break;
    case "agent_status": on_agent_status_change(frame.data); break;
    case "new_alert": on_alert_received(frame.data); break;
    case "alert_list": on_alert_snapshot(frame.data); break;
    case "alert_resolved": on_alert_resolved(frame.data); break;
    case "command_ack": on_command_ack(frame.data); break;
  }
}

// atualiza indicador de status da conexao
function setConnection(online) {
  el.conn.className = online ? "conn conn-on" : "conn conn-off";
  el.connText.textContent = online ? "conectado" : "reconectando…";
}

// insere / atualiza agente no estado local
function upsertAgent(a) {
  agents.set(a.agent_id, a);
}

// atualiza lista de maquinas quando status muda
function on_agent_status_change(a) {
  upsertAgent(a);
  renderAgents();
}

// renderiza a lista de endpoints
function renderAgents() {
  const list = [...agents.values()];
  const online = list.filter((a) => a.status === "online").length;
  el.onlineCount.textContent = online;
  el.agentTotal.textContent = list.length;

  if (list.length === 0) {
    el.agentList.innerHTML = '<div class="empty">sem endpoints registrados</div>';
    return;
  }
  // online primeiro, depois por id
  list.sort((a, b) => (a.status === b.status ? a.agent_id.localeCompare(b.agent_id) : a.status === "online" ? -1 : 1));
  el.agentList.innerHTML = list.map(agentRow).join("");
}

// monta o card de um endpoint
function agentRow(a) {
  const host = a.hostname || "(sem hostname)";
  const ip = a.ip_address || "—";
  const isolated = !!a.isolated;
  const online = a.status === "online";
  // um botao que alterna isolar/liberar; offline nao tem acao
  let toggle = "";
  if (online) {
    toggle = isolated
      ? `<button class="btn lift" data-action="LIFT" data-agent="${esc(a.agent_id)}">liberar host</button>`
      : `<button class="btn danger" data-action="ISOLATE" data-agent="${esc(a.agent_id)}">isolar host</button>`;
  } else {
    toggle = `<span class="agent-offline-hint">offline — sem ações</span>`;
  }
  const badge = isolated ? `<span class="iso-badge">isolado</span>` : "";
  return `
    <div class="agent${isolated ? " isolated" : ""}">
      <div class="agent-head">
        <span class="dot ${a.status}"></span>
        <span class="agent-host">${esc(host)}</span>
        ${badge}
        <span class="agent-state ${a.status}">${a.status}</span>
      </div>
      <div class="agent-id">${esc(a.agent_id)}</div>
      <div class="agent-ip">${esc(ip)}</div>
      <div class="agent-actions">${toggle}</div>
    </div>`;
}

// ordem de severidade para escolher a cor do grupo
const SEV_RANK = { MEDIUM: 1, HIGH: 2, CRITICAL: 3 };

// chave do grupo: agente+pid quando ha pid; senao o proprio alert_id (singleton)
function groupKey(d) {
  const pid = d.culprit_pid;
  if (pid !== null && pid !== undefined) return `p:${d.agent_id}:${pid}`;
  return `a:${d.alert_id}`;
}

// adiciona um alerta ao seu grupo (cria o card se for grupo novo)
function on_alert_received(d) {
  const id = d.alert_id;
  if (id && alertIndex.has(id)) return;       // ja exibido (evita duplicar no replay)
  const empty = el.alertList.querySelector(".empty");
  if (empty) empty.remove();

  const key = groupKey(d);
  let g = alertGroups.get(key);
  if (!g) {
    g = { key, agentId: d.agent_id, pid: (d.culprit_pid ?? null), alerts: new Map(), el: null };
    alertGroups.set(key, g);
    g.el = document.createElement("div");
    el.alertList.prepend(g.el);              // grupo novo no topo
  }
  g.alerts.set(id, {
    rule: d.rule_triggered || "alerta",
    description: d.description || "",
    severity: (d.severity || "CRITICAL"),
  });
  if (id) alertIndex.set(id, key);
  renderGroup(g);
  updateAlertCount();
}

// snapshot dos alertas ativos no connect/refresh (mais antigo -> mais novo)
function on_alert_snapshot(list) {
  alertGroups.clear();
  alertIndex.clear();
  el.alertList.innerHTML = "";
  list.forEach(on_alert_received);
  if (alertGroups.size === 0) showAlertsEmpty();
  updateAlertCount();
}

// um alerta foi resolvido (servidor): tira do grupo; remove o card se esvaziar
function on_alert_resolved(d) {
  const key = alertIndex.get(d.alert_id);
  alertIndex.delete(d.alert_id);
  const g = key && alertGroups.get(key);
  if (g) {
    g.alerts.delete(d.alert_id);
    if (g.alerts.size === 0) {
      if (g.el) g.el.remove();
      alertGroups.delete(key);
    } else {
      renderGroup(g);
    }
  }
  if (alertGroups.size === 0) showAlertsEmpty();
  updateAlertCount();
}

// contador = total de deteccoes ativas (somando todos os grupos)
function updateAlertCount() {
  let n = 0;
  for (const g of alertGroups.values()) n += g.alerts.size;
  el.alertCount.textContent = n;
}

function showAlertsEmpty() {
  if (!el.alertList.querySelector(".empty")) {
    el.alertList.innerHTML = '<div class="empty">nenhum alerta ativo</div>';
  }
}

// severidade do grupo = a maior entre seus alertas
function groupSeverity(g) {
  let best = "MEDIUM";
  for (const a of g.alerts.values()) {
    if ((SEV_RANK[a.severity] || 0) > (SEV_RANK[best] || 0)) best = a.severity;
  }
  return best;
}

// mapeia severidade para classe css de cor
function sevClass(severity) {
  const s = String(severity || "").toUpperCase();
  if (s === "HIGH") return "sev-high";
  if (s === "MEDIUM") return "sev-medium";
  return "sev-critical";
}

// desenha o card de um grupo de alertas
function renderGroup(g) {
  const sev = groupSeverity(g);
  const list = [...g.alerts.values()];
  const title = list.length === 1 ? list[0].rule : `${list.length} detecções`;
  const rows = list.map((a) =>
    `<li><b>${esc(a.rule)}</b>${a.description ? ` — ${esc(a.description)}` : ""}</li>`
  ).join("");
  const hasPid = g.pid !== null && g.pid !== undefined;
  // um "encerrar pid" resolve todos os alertas do grupo
  const killBtn = hasPid
    ? `<button class="btn danger" data-action="KILL" data-agent="${esc(g.agentId)}" data-pid="${g.pid}" data-group="${esc(g.key)}">encerrar pid ${g.pid}</button>`
    : `<button class="btn danger" disabled title="alerta de arquivo: sem processo associado">encerrar pid —</button>`;
  const dismissBtn = `<button class="btn" data-group-resolve="${esc(g.key)}">dispensar</button>`;
  g.el.className = `alert-card ${sevClass(sev)}`;
  g.el.innerHTML = `
    <div class="sev-stripe"></div>
    <div class="alert-main">
      <div class="alert-top">
        <span class="alert-rule">${esc(title)}</span>
        <span class="badge">${esc(sev)}</span>
        <span class="alert-time">${nowTime()}</span>
      </div>
      <ul class="alert-rules">${rows}</ul>
      <div class="alert-meta">
        <span>agente: <b>${esc(g.agentId)}</b></span>
        ${hasPid ? `<span>pid: <b>${g.pid}</b></span>` : ""}
      </div>
      <div class="alert-actions">
        ${killBtn}
        ${dismissBtn}
      </div>
    </div>`;
}

// envia ordem de mitigacao de volta pela api via websocket
function trigger_order(command, agentId, pid) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  const order = {
    frame_type: "trigger_order",
    data: {
      target_agent: agentId,
      command: command,
      parameters: pid !== undefined && pid !== null ? { pid: Number(pid) } : {},
    },
  };
  ws.send(JSON.stringify(order));
}

// envia ordem de resolucao de um alerta (acionado/dispensado)
function resolve_alert(alertId) {
  if (!ws || ws.readyState !== WebSocket.OPEN || !alertId) return;
  ws.send(JSON.stringify({ frame_type: "resolve_alert", data: { alert_id: alertId } }));
}

// resolve todos os alertas de um grupo (um resolve_alert por alert_id)
function resolveGroup(key) {
  const g = alertGroups.get(key);
  if (!g) return;
  for (const id of g.alerts.keys()) resolve_alert(id);
}

// delega cliques dos botoes de acao (mitigacao) e de dispensar
document.addEventListener("click", (e) => {
  const actBtn = e.target.closest("button[data-action]");
  const resBtn = e.target.closest("button[data-group-resolve], button[data-resolve]");
  const btn = actBtn || resBtn;
  if (!btn) return;
  // feedback imediato no botao (flash) ate o ack chegar
  btn.classList.add("clicked");
  setTimeout(() => btn.classList.remove("clicked"), 400);
  if (actBtn) {
    trigger_order(actBtn.dataset.action, actBtn.dataset.agent, actBtn.dataset.pid);
    // KILL no card agrupado resolve o grupo inteiro
    if (actBtn.dataset.group) resolveGroup(actBtn.dataset.group);
    else if (actBtn.dataset.alert) resolve_alert(actBtn.dataset.alert);
  } else if (resBtn) {
    if (resBtn.dataset.groupResolve) resolveGroup(resBtn.dataset.groupResolve);
    else resolve_alert(resBtn.dataset.resolve);
  }
});

// ack do servidor: confirma que o comando foi recebido/publicado
function on_command_ack(d) {
  const label = { KILL: "encerrar processo", ISOLATE: "isolar host", LIFT: "liberar host" }[d.command] || d.command;
  const pidtxt = (d.pid !== null && d.pid !== undefined) ? ` (pid ${d.pid})` : "";
  toast(`✓ ${label}${pidtxt} → ${esc(d.target_agent)}`);
}

// mostra uma notificacao temporaria no canto da tela
function toast(msg) {
  const box = document.getElementById("toasts");
  if (!box) return;
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 300);
  }, 3200);
}

// hora local formatada hh:mm:ss
function nowTime() {
  return new Date().toLocaleTimeString("pt-br", { hour12: false });
}

// escapa texto para evitar injecao no innerHTML
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// inicia conexao ao carregar
connect_websocket();
