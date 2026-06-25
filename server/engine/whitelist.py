# whitelist contextual por comportamento: dropa ruido benigno na entrada
# principio: nunca por process_name sozinho -> na duvida, passa para as regras

from server import config

# tokens que regras de evento unico procuram na cmdline
# se cmdline contem qualquer um o evento nao vai pra whitelist
SUSPICIOUS_TOKENS = (
    # shell reverso / c2
    "-i", "/dev/tcp/", "/dev/udp/", "nc -e", "ncat -e", "socket", "exec",
    "curl", "wget", "base64", "| bash", "| sh", "|bash", "|sh",
    # discovery
    "/etc/passwd", "/etc/shadow", "getent", "cut -d:", "id", "whoami",
    "uname", "sudo -l", "nmap", "masscan", "arp-scan", "netstat",
    # persistencia / privesc
    "crontab", "chmod +s", "chmod 4755", "insmod", "modprobe",
    "useradd", "adduser",
    # anti-forense
    "history -c", "histfile", "truncate", "touch -t", "touch -d", "debugfs",
    "rm ", ">",
    # exec suspeita
    "/tmp/", "/dev/shm/", "/var/tmp/",
)

# prefixos de binario padrao (processo so e candidato a benigno se vier daqui)
STD_BIN_PREFIXES = ("/usr/bin/", "/bin/", "/usr/sbin/", "/sbin/")


def _has_suspicious_token(cmdline):
    # checagem de substring contra o guard
    low = (cmdline or "").lower()
    return any(tok in low for tok in SUSPICIOUS_TOKENS)


def is_whitelisted(event):
    # retorna true quando contexto inteiro do evento e inequivocamente benigno
    payload = event.payload

    if event.event_type == "file_modified":
        # dropa apenas escritas em arvores que nenhuma regra observa
        path = payload.file_path or ""
        return any(path.startswith(prefix) for prefix in config.NOISE_PATHS)

    if event.event_type == "process_created":
        cmdline = payload.cmdline or ""
        # qualquer token suspeito derruba o whitelist (vai para as regras)
        if _has_suspicious_token(cmdline):
            return False
        name = payload.process_name or ""
        # so daemons rotineiros conhecidos sao ruido benigno
        if name not in config.BENIGN_DAEMONS:
            return False
        # e ainda assim so quando rodando de um path de binario padrao
        first = cmdline.split(" ", 1)[0] if cmdline else ""
        return first.startswith(STD_BIN_PREFIXES)

    return False
