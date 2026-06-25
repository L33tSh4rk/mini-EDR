# builders dos frames json enviados aos dashboards via websocket

def _agent_view(agent):
    # projecao publica do estado de um agente
    return {
        "agent_id": agent["agent_id"],
        "hostname": agent.get("hostname", ""),
        "ip_address": agent.get("ip_address", ""),
        "status": agent["status"],
        # estado de isolamento lembrado pelo servidor (refletido na ui)
        "isolated": agent.get("isolated", False),
    }

def status_frame(agent):
    # frame de mudanca de status de unico agente
    return {"frame_type": "agent_status", "data": _agent_view(agent)}

def agent_list_frame(agents):
    # snapshot inicial com todos os agentes conhecidos
    return {"frame_type": "agent_list", "data": [_agent_view(a) for a in agents]}

def alert_list_frame(stored):
    # snapshot dos alertas ativos (reenvio no refresh); envia as data internas
    return {"frame_type": "alert_list", "data": [a.get("data", {}) for a in stored]}

def alert_resolved_frame(alert_id):
    # avisa os dashboards que um alerta foi acionado/dispensado
    return {"frame_type": "alert_resolved", "data": {"alert_id": alert_id}}

def command_ack_frame(command, target_agent, pid=None):
    # confirma que a ordem foi recebida e publicada pelo servidor (feedback/toast)
    return {
        "frame_type": "command_ack",
        "data": {"command": command, "target_agent": target_agent, "pid": pid},
    }
