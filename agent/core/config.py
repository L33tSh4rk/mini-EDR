# constantes de configuracao do agente, lidas de env var com defaults

import os


def _env(name, default):
    # le variavel de ambiente ou usa default
    return os.environ.get(name, default)


# endereco e portas do servidor
SERVER_HOST = _env("SERVER_HOST", "127.0.0.1")
SERVER_HTTP_PORT = int(_env("SERVER_HTTP_PORT", "8000"))
SERVER_UDP_PORT = int(_env("SERVER_UDP_PORT", "9999"))

# endereco e porta do redis
REDIS_HOST = _env("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(_env("REDIS_PORT", "6379"))

# intervalo de descarregamento do buffer em segundos
FLUSH_INTERVAL = int(_env("FLUSH_INTERVAL", "5"))

# intervalo de envio de heartbeat em segundos
HEARTBEAT_INTERVAL = int(_env("HEARTBEAT_INTERVAL", "5"))

# tempo maximo sem contato com redis antes do auto-isolamento
REDIS_TIMEOUT = int(_env("REDIS_TIMEOUT", "20"))

# intervalo de polling de processos em segundos
PROC_POLL_INTERVAL = float(_env("PROC_POLL_INTERVAL", "2"))

# backoff maximo de reconexao em segundos
MAX_BACKOFF = int(_env("MAX_BACKOFF", "20"))

# tamanho maximo do buffer local de eventos (backpressure; dropa quando cheio)
EVENT_QUEUE_MAX = int(_env("EVENT_QUEUE_MAX", "5000"))

# intervalo de re-registro periodico (sobrevive a restart do servidor)
REENROLL_INTERVAL = int(_env("REENROLL_INTERVAL", "30"))

# caminhos vigiados pelo collector de arquivos
WATCH_PATHS = _env("WATCH_PATHS", "/etc,/tmp,/home").split(",")

# nomes fixos das estruturas no redis (contrato da spec)
TELEMETRY_QUEUE = "telemetry_queue"
ALERTS_CHANNEL = "alerts_channel"


def commands_channel(agent_id):
    # canal pub/sub de comandos para o agente
    return f"commands:{agent_id}"


def corr_key(agent_id):
    # chave ttl de estado de correlacao do agente
    return f"corr:{agent_id}"
