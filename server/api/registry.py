# registro em memoria do estado online/offline dos agentes

import time


class AgentRegistry:
    # mantem o ultimo estado conhecido de cada agente

    def __init__(self):
        # mapa agent_id -> dados de estado
        self._agents = {}

    def register(self, agent_id, ip_address, hostname):
        # registra dados de enrollment e marca o agente como online
        agent = self._agents.get(agent_id, {})
        agent.update(
            {
                "agent_id": agent_id,
                "ip_address": ip_address,
                "hostname": hostname,
                "status": "online",
                "last_seen": time.monotonic(),
            }
        )
        self._agents[agent_id] = agent
        return agent

    def touch(self, agent_id):
        # atualiza last_seen via heartbeat; retorna true se virou online agora.
        
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        changed = False
        if agent["status"] != "online":
            agent["status"] = "online"
            changed = True
        agent["last_seen"] = time.monotonic()
        return changed

    def expire(self, timeout):
        # marca offline agentes sem heartbeat recente e retorna os que mudaram
        now = time.monotonic()
        changed = []
        for agent in self._agents.values():
            if agent["status"] == "online" and now - agent["last_seen"] > timeout:
                agent["status"] = "offline"
                changed.append(agent)
        return changed

    def set_isolated(self, agent_id, value):
        # marca/desmarca estado de isolamento de um agente e retorna agente
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        agent["isolated"] = value
        return agent

    def get(self, agent_id):
        # retorna estado de um agente ou none
        return self._agents.get(agent_id)

    def all(self):
        # retorna lista dos agentes conhecidos
        return list(self._agents.values())
