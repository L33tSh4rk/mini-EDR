# escalonamento de privilegio (severidade critical)

from server.engine.rules.base import Rule


class ShadowModified(Rule):
    # alteracao direta de shadow/passwd
    name = "shadow_modified"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if path in ("/etc/shadow", "/etc/passwd"):
            return self.make_hit(f"alteracao de base de credenciais: {path}")
        return None


class SudoersModified(Rule):
    # alteracao de sudoers
    name = "sudoers_modified"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if path == "/etc/sudoers" or path.startswith("/etc/sudoers.d/"):
            return self.make_hit(f"alteracao de sudoers: {path}")
        return None


class LdPreloadHijack(Rule):
    # sequestro via ld.so.preload
    name = "ld_preload_hijack"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        if (event.payload.file_path or "") == "/etc/ld.so.preload":
            return self.make_hit("sequestro via /etc/ld.so.preload")
        return None


class SuidBinaryCreated(Rule):
    # atribuicao de bit suid a um binario
    name = "suid_binary_created"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        if "chmod +s" in cmd or "chmod 4755" in cmd or "chmod u+s" in cmd:
            return self.make_hit(
                f"criacao de binario suid: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None
