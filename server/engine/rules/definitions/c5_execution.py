# execucao suspeita (severidade medium)

from server.engine.rules.base import Rule

# diretorios world-writable usados para staging de payloads
SUSPECT_DIRS = ("/tmp/", "/dev/shm/", "/var/tmp/")


class ExecFromTmpdir(Rule):
    # processo executado a partir de diretorio temporario
    name = "exec_from_tmpdir"
    severity = "MEDIUM"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        cmd = (event.payload.cmdline or "").lower()
        name = (event.payload.process_name or "").lower()
        if any(d in cmd for d in SUSPECT_DIRS) or any(d in name for d in SUSPECT_DIRS):
            return self.make_hit(
                f"execucao a partir de diretorio temporario: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None
