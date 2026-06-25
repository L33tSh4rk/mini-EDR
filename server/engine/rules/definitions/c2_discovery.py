# reconhecimento (discovery)

from server.engine.rules.base import Rule
from server.engine.rules.definitions import _helpers as H

# ferramentas de varredura de rede
RECON_TOOLS = ("nmap", "masscan", "arp-scan")


class PasswdEnum(Rule):
    # enumeracao do /etc/passwd
    name = "passwd_enum"
    severity = "MEDIUM"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        if (
            "cat /etc/passwd" in cmd
            or "getent passwd" in cmd
            or ("cut" in cmd and "/etc/passwd" in cmd)
        ):
            return self.make_hit(
                f"enumeracao de /etc/passwd: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None


class NetworkRecon(Rule):
    # varredura de rede ou de portas locais
    name = "network_recon"
    severity = "MEDIUM"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        name = (event.payload.process_name or "").lower()
        cmd = (event.payload.cmdline or "").lower()
        if name in RECON_TOOLS or "netstat -tlnp" in cmd:
            return self.make_hit(
                f"reconhecimento de rede: {event.payload.process_name or event.payload.cmdline}",
                event.payload.pid,
            )
        return None


class PrivEnumBurst(Rule):
    # 3+ eventos de enumeracao (id, whoami, uname, sudo -l) na janela
    name = "priv_enum_burst"
    severity = "MEDIUM"
    correlated = True

    def evaluate(self, event, window):
        count = sum(1 for s in window if H.is_recon(s))
        if count >= 3:
            return self.make_hit(
                f"burst de enumeracao de privilegio ({count} eventos)",
                window[-1].get("pid"),
            )
        return None
