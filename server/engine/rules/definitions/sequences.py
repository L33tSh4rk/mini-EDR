# sequencias de 2 e 3 eventos confirmadas pela janela de correlacao o evento atual e window[-1]; o historico e window[:-1]

from server.engine.rules.base import Rule
from server.engine.rules.definitions import _helpers as H

# processos de servidor web (web shell)
WEB_SERVERS = ("apache2", "nginx", "php-fpm", "httpd")
# criacao de usuario
USERADD = ("useradd", "adduser")
# binarios tipo gtfobins que, via sudo, permitem escapar para root/shell
SUDO_ABUSE_BINS = (
    "vim", "vi", "nano", "find", "less", "more", "man", "awk", "env",
    "python", "python3", "perl", "ruby", "nmap", "ftp", "gdb", "tar",
    "bash", "sh", "tee", "dd",
)


def _sudo_target(cmd):
    # retorna o basename do binario invocado por 'sudo' na cmdline, ou none
    toks = cmd.split()
    for i, t in enumerate(toks):
        if t == "sudo" and i + 1 < len(toks):
            return toks[i + 1].split("/")[-1]
    return None


# sequencias de 2 eventos

class DropperChmodExec(Rule):
    # arquivo dropado em tmp + chmod +x sobre ele
    name = "dropper_chmod_exec"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        c = H.cmd(cur)
        if not (H.is_proc(cur) and "chmod" in c and ("+x" in c or "755" in c) and H.in_tmp(c)):
            return None
        for s in window[:-1]:
            if H.is_file(s) and H.created(s) and H.in_tmp(H.fpath(s)):
                return self.make_hit(f"dropper: arquivo em tmp + chmod +x ({c})", cur.get("pid"))
        return None


class WebShellImplant(Rule):
    # servidor web ativo + criacao de .php no diretorio web
    name = "web_shell_implant"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        p = H.fpath(cur)
        if not (H.is_file(cur) and H.created(cur) and p.endswith(".php") and ("/var/www" in p or "/srv/www" in p)):
            return None
        for s in window[:-1]:
            if H.is_proc(s) and (H.pname(s) in WEB_SERVERS or any(w in H.cmd(s) for w in WEB_SERVERS)):
                return self.make_hit(f"web shell implantado: {p}")
        return None


class UserBackdoorConfirmed(Rule):
    # criacao de usuario + modificacao de /etc/passwd na janela
    name = "user_backdoor_confirmed"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        has_useradd = any(
            H.is_proc(s) and (H.pname(s) in USERADD or "useradd" in H.cmd(s) or "adduser" in H.cmd(s))
            for s in window
        )
        has_passwd = any(H.is_file(s) and H.fpath(s) == "/etc/passwd" for s in window)
        if has_useradd and has_passwd:
            return self.make_hit("backdoor de usuario confirmado (useradd + /etc/passwd)")
        return None


class DoublePersistence(Rule):
    # duas tecnicas de persistencia distintas em sequencia curta
    name = "double_persistence"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        kind = H.persist_kind(cur)
        if kind is None:
            return None
        for s in window[:-1]:
            other = H.persist_kind(s)
            if other and other != kind:
                return self.make_hit(f"dupla persistencia: {other} + {kind}")
        return None


class KernelModuleDrop(Rule):
    # drop de .ko seguido de insmod/modprobe
    name = "kernel_module_drop"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        c = H.cmd(cur)
        if not (H.is_proc(cur) and (H.pname(cur) in ("insmod", "modprobe") or "insmod" in c or "modprobe" in c)):
            return None
        for s in window[:-1]:
            if H.is_file(s) and H.created(s) and H.fpath(s).endswith(".ko"):
                return self.make_hit(f"rootkit: drop de .ko + carregamento ({c})", cur.get("pid"))
        return None


# sequencias de 3 eventos

class ScriptDropperTrilogy(Rule):
    # download + materializacao em tmp + chmod +x
    name = "script_dropper_trilogy"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        c = H.cmd(cur)
        if not (H.is_proc(cur) and "chmod" in c and ("+x" in c or "755" in c) and H.in_tmp(c)):
            return None
        has_dl = any(H.is_proc(s) and ("curl" in H.cmd(s) or "wget" in H.cmd(s)) for s in window[:-1])
        has_drop = any(H.is_file(s) and H.created(s) and H.in_tmp(H.fpath(s)) for s in window[:-1])
        if has_dl and has_drop:
            return self.make_hit(f"trilogia dropper: download + drop + chmod ({c})", cur.get("pid"))
        return None


class CredentialDumpAndStage(Rule):
    # leitura de credenciais + staging em tmp + arquivo materializado
    name = "credential_dump_and_stage"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        if not (H.is_file(cur) and H.created(cur) and H.in_tmp(H.fpath(cur))):
            return None
        has_read = any(
            H.is_proc(s)
            and ("cat" in H.cmd(s) or "strings" in H.cmd(s) or H.pname(s) in ("cat", "strings"))
            and ("/etc/shadow" in H.cmd(s) or "/etc/passwd" in H.cmd(s))
            for s in window[:-1]
        )
        has_stage = any(
            H.is_proc(s)
            and (H.pname(s) in ("tee", "cp", "dd") or any(t in H.cmd(s) for t in ("tee", "cp ", "dd ")))
            and H.in_tmp(H.cmd(s))
            for s in window[:-1]
        )
        if has_read and has_stage:
            return self.make_hit(f"dump de credenciais + staging: {H.fpath(cur)}")
        return None


class SudoEnumThenAbuse(Rule):
    # sudo -l (enum) + sudo <gtfobin> (abuso para escapar/privesc) na janela.
    # nao usa user==root: em container tudo e root, o que gera fp; o sinal e o
    # abuso de um binario gtfobin via sudo, nao admin legitimo (ex.: sudo apt).
    name = "sudo_enum_then_abuse"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        has_enum = any(H.is_proc(s) and "sudo -l" in H.cmd(s) for s in window)
        abuse_pid = None
        for s in window:
            if not H.is_proc(s):
                continue
            target = _sudo_target(H.cmd(s))
            if target and target in SUDO_ABUSE_BINS:
                abuse_pid = s.get("pid")
        if has_enum and abuse_pid is not None:
            return self.make_hit(
                "enumeracao de sudo seguida de abuso de gtfobin", abuse_pid
            )
        return None


class RapidLogWipe(Rule):
    # 3+ delecoes em /var/log na janela.
    # conta so action=='deleted' (nao 'modified') para nao confundir com rotacao de log (logrotate gera modify/create em .1/.2/.gz, nao delecoes em massa)
    name = "rapid_log_wipe"
    severity = "HIGH"
    correlated = True

    def evaluate(self, event, window):
        count = sum(
            1
            for s in window
            if H.is_file(s)
            and H.fpath(s).startswith("/var/log")
            and s.get("action") == "deleted"
        )
        if count >= 3:
            return self.make_hit(f"limpeza rapida de logs ({count} delecoes em /var/log)")
        return None


class LolbinInterpreterDrop(Rule):
    # interpretador suspeito + staging + materializacao (living off the land)
    name = "lolbin_interpreter_drop"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        p = H.fpath(cur)
        if not (H.is_file(cur) and H.created(cur) and (H.in_tmp(p) or p.startswith("/etc/"))):
            return None
        has_interp = any(
            H.is_proc(s)
            and H.pname(s) in ("python", "python3", "perl", "ruby")
            and ("socket" in H.cmd(s) or "exec" in H.cmd(s))
            for s in window[:-1]
        )
        has_stage = any(
            H.is_proc(s)
            and (H.pname(s) in ("tee", "dd", "cp") or any(t in H.cmd(s) for t in ("tee", "dd ", "cp ")))
            for s in window[:-1]
        )
        if has_interp and has_stage:
            return self.make_hit(f"lolbin: interpretador + staging + drop ({p})")
        return None
