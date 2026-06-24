# estado interno do agente compartilhado entre os loops assincronos

import socket
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class AgentState:
    # identidade e estado de runtime do agente
    agent_id: str
    ip_address: str
    hostname: str
    isolated: bool = False
    last_redis_ok: float = field(default_factory=time.monotonic)
    # regras de iptables inseridas no isolamento (para remover apenas elas no LIFT)
    iso_rules: list = field(default_factory=list)
    # politicas default originais salvas antes do isolamento
    iso_policies: dict = field(default_factory=dict)

    def mark_redis_ok(self):
        # registra contato bem sucedido com o redis
        self.last_redis_ok = time.monotonic()

    def seconds_since_redis(self):
        # tempo decorrido desde o ultimo contato com o redis
        return time.monotonic() - self.last_redis_ok


def build_state():
    # monta o estado inicial resolvendo identidade do host
    hostname = socket.gethostname()
    try:
        # resolve o ip local a partir do hostname
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        # fallback quando o hostname nao resolve
        ip_address = "127.0.0.1"
    # usa env var se fornecida senao gera id unico
    import os
    agent_id = os.environ.get("AGENT_ID") or str(uuid.uuid4())
    return AgentState(agent_id=agent_id, ip_address=ip_address, hostname=hostname)
