# predicados sobre resumos da janela usados pelas regras de correlacao

# diretorios de staging usados por droppers
TMP_DIRS = ("/tmp/", "/dev/shm/", "/var/tmp/")


def cmd(s):
    # cmdline em minusculas
    return (s.get("cmdline") or "").lower()

def pname(s):
    # process_name em minusculas
    return (s.get("process_name") or "").lower()

def fpath(s):
    # caminho do arquivo
    return s.get("file_path") or ""

def is_proc(s):
    # resumo de criacao de processo
    return s.get("event_type") == "process_created"

def is_file(s):
    # resumo de modificacao de arquivo
    return s.get("event_type") == "file_modified"

def created(s):
    # arquivo criado
    return s.get("action") == "created"

def in_tmp(text):
    # caminho/cmdline aponta para diretorio de staging
    return any(d in (text or "") for d in TMP_DIRS)

def paths_in(text):
    # extrai tokens que parecem caminhos absolutos
    return {tok for tok in (text or "").split() if tok.startswith("/")}

# tokens de reconhecimento
RECON_NAMES = ("id", "whoami", "uname")
RECON_TOKENS = ("sudo -l", "uname", "/etc/passwd", "getent passwd")


def is_recon(s):
    # processo de enumeracao/reconhecimento
    return is_proc(s) and (pname(s) in RECON_NAMES or any(t in cmd(s) for t in RECON_TOKENS))

# tokens de processo inequivocamente suspeito (subset dos sinais de evento unico)
SUSPICIOUS_PROC_TOKENS = (
    "bash -i", "/dev/tcp/", "nc -e", "ncat -e", "base64 -d",
    "chmod +s", "chmod 4755", "| bash", "|bash", "| sh", "|sh", "socket",
)

def is_suspicious_proc(s):
    # processo que ja seria suspeito por si so
    return is_proc(s) and any(t in cmd(s) for t in SUSPICIOUS_PROC_TOKENS)

def persist_kind(s):
    # categoria de persistencia do arquivo modificado, ou none
    if not is_file(s):
        return None
    p = fpath(s)
    if "/etc/crontab" in p or "/var/spool/cron" in p:
        return "cron"
    if (
        p.endswith("/.bashrc")
        or p.endswith("/.bash_profile")
        or p.endswith("/.profile")
        or p == "/etc/profile"
        or p.startswith("/etc/profile.d/")
    ):
        return "profile"
    if p.endswith("/.ssh/authorized_keys"):
        return "ssh"
    if p.startswith("/etc/systemd/system/") and p.endswith(".service"):
        return "systemd"
    return None
