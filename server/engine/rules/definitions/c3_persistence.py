# persistencia (severidade critical)

from server.engine.rules.base import Rule


class CrontabFileModified(Rule):
    # alteracao de arquivos de cron
    name = "crontab_file_modified"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if path == "/etc/crontab" or path.startswith("/var/spool/cron"):
            return self.make_hit(f"alteracao de cron: {path}")
        return None


class CrontabCmdModified(Rule):
    # uso de crontab -e / -r para editar agendamentos
    name = "crontab_cmd_modified"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "process_created":
            return None
        name = (event.payload.process_name or "").lower()
        cmd = (event.payload.cmdline or "").lower()
        if name == "crontab" and (" -e" in cmd or " -r" in cmd):
            return self.make_hit(
                f"edicao de crontab via cli: {event.payload.cmdline}",
                event.payload.pid,
            )
        return None


class ShellProfileBackdoor(Rule):
    # backdoor em arquivos de profile de shell
    name = "shell_profile_backdoor"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if (
            path.endswith("/.bashrc")
            or path.endswith("/.bash_profile")
            or path.endswith("/.profile")
            or path == "/etc/profile"
            or path.startswith("/etc/profile.d/")
        ):
            return self.make_hit(f"backdoor em profile de shell: {path}")
        return None


class SshAuthorizedKeys(Rule):
    # alteracao de chaves ssh autorizadas
    name = "ssh_authorized_keys"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if path.endswith("/.ssh/authorized_keys"):
            return self.make_hit(f"alteracao de authorized_keys: {path}")
        return None


class SystemdServiceDrop(Rule):
    # criacao de unidade systemd (servico persistente)
    name = "systemd_service_drop"
    severity = "CRITICAL"

    def evaluate(self, event, window):
        if event.event_type != "file_modified":
            return None
        path = event.payload.file_path or ""
        if (
            path.startswith("/etc/systemd/system/")
            and path.endswith(".service")
            and event.payload.action == "created"
        ):
            return self.make_hit(f"drop de servico systemd: {path}")
        return None
