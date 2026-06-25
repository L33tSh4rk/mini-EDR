# command & control / shell reverso

from server.engine.rules.base import Rule

# interpretadores usados como shell reverso
INTERPRETERS = ("python", "python3", "perl", "ruby")


class ReverseShellClassic(Rule):
    # cmdline classica de shell reverso
    name = "reverse_shell_classic"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        if any(tok in cmd for tok in ("bash -i", "/dev/tcp/", "nc -e", "ncat -e")):
            return self.make_hit(
                f"shell reverso classico: {event.payload.cmdline}", event.payload.pid
            )
        return None


class ReverseShellInterpreter(Rule):
    # interpretador com socket + exec na cmdline
    name = "reverse_shell_interpreter"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        name = (event.payload.process_name or "").lower()
        cmd = (event.payload.cmdline or "").lower()
        if name in INTERPRETERS and "socket" in cmd and (
            "exec" in cmd or "/bin/sh" in cmd or "spawn" in cmd or "system(" in cmd
        ):
            return self.make_hit(
                f"shell reverso via interpretador: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None


class DownloadExecPipe(Rule):
    # download canalizado direto para o shell (curl|bash, wget|sh)
    name = "download_exec_pipe"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        has_dl = "curl" in cmd or "wget" in cmd
        has_pipe = any(p in cmd for p in ("| bash", "|bash", "| sh", "|sh"))
        if has_dl and has_pipe:
            return self.make_hit(
                f"download canalizado para shell: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None


class Base64Exec(Rule):
    # execucao de payload codificado em base64
    name = "base64_exec"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        piped = "base64" in cmd and any(
            p in cmd for p in ("| bash", "|bash", "| sh", "|sh")
        )
        if "base64 -d" in cmd or piped:
            return self.make_hit(
                f"execucao de payload base64: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None
