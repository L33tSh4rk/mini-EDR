# constantes da configuracao do servidor, lidas do env var com defaults

import os

def _env(name, default):
    # le variavel de ambiente ou usa default
    return os.environ.get(name, default)


# escuta http da api (enrollment e dashboard)
HTTP_HOST = _env("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(_env("HTTP_PORT", "8000"))

# escuta udp pura de heartbeats
UDP_HOST = _env("UDP_HOST", "0.0.0.0")
UDP_PORT = int(_env("UDP_PORT", "9999"))

# endereco e porta do broker redis
REDIS_HOST = _env("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(_env("REDIS_PORT", "6379"))

# tempo sem heartbeat para considerar o agente offline
HEARTBEAT_TIMEOUT = int(_env("HEARTBEAT_TIMEOUT", "15"))

# intervalo de varredura de agentes offline
REAPER_INTERVAL = int(_env("REAPER_INTERVAL", "5"))

# tempo de vida do estado de correlacao (janela deslizante do worker)
CORR_TTL = int(_env("CORR_TTL", "20"))

# severidade padrao quando uma regra nao define a sua
DEFAULT_SEVERITY = _env("DEFAULT_SEVERITY", "CRITICAL")

# arvores de arquivo inequivocamente benignas - usadas pelo whitelist contextual para dropar ruido de fs na entrada
NOISE_PATHS = _env(
    "NOISE_PATHS",
    "/var/cache/,/var/lib/,/run/,/proc/,/sys/,/var/log/journal/",
).split(",")

# daemons rotineiros onde process_created e ruido benigno -> interpretadores (bash/sh/python/perl/ruby) vao para as regras
BENIGN_DAEMONS = set(
    _env(
        "BENIGN_DAEMONS",
        "systemd,systemd-journald,systemd-logind,rsyslogd,dbus-daemon,agetty,cron,CRON,polkitd,udevd",
    ).split(",")
)

# nomes fixos das estruturas no redis
TELEMETRY_QUEUE = "telemetry_queue"
ALERTS_CHANNEL = "alerts_channel"


def commands_channel(agent_id):
    # canal pub/sub de comandos para o agente
    return f"commands:{agent_id}"

def corr_key(agent_id):
    # chave ttl de estado de correlacao do agente
    return f"corr:{agent_id}"
