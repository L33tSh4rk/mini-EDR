# evasao / anti-forense (severidade high)

from server.engine.rules.base import Rule


class LogWipe(Rule):
    # destruicao de logs do sistema
    name = "log_wipe"
    severity = "HIGH"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        # redirect destrutivo deve apontar PARA /var/log (alvo), nao so coexistir.
        # evita fp de "tail /var/log/x > /tmp/y" (le log, redireciona p/ outro lugar)
        redirect_to_log = "> /var/log" in cmd or ">/var/log" in cmd
        if (
            ("rm" in cmd and "/var/log" in cmd)
            or "truncate -s 0" in cmd
            or redirect_to_log
        ):
            return self.make_hit(
                f"destruicao de logs: {event.payload.cmdline}", event.payload.pid
            )
        return None


class HistoryWipe(Rule):
    # limpeza do historico de shell
    name = "history_wipe"
    severity = "HIGH"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        if (
            "history -c" in cmd
            or "histfile" in cmd
            or ".bash_history" in cmd
        ):
            return self.make_hit(
                f"limpeza de historico: {event.payload.cmdline}", event.payload.pid
            )
        return None


class TimestampTampering(Rule):
    # adulteracao de timestamps (timestomping)
    name = "timestamp_tampering"
    severity = "HIGH"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        name = (event.payload.process_name or "").lower()
        cmd = (event.payload.cmdline or "").lower()
        if "touch -t" in cmd or "touch -d" in cmd or name == "debugfs" or "debugfs" in cmd:
            return self.make_hit(
                f"adulteracao de timestamp: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None
