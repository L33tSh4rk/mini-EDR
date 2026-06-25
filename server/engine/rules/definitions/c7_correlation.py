# correlacao temporal usando a janela (severidade critical)
# o evento atual e o ultimo da janela; o historico e window[:-1]

from server.engine.rules.base import Rule
from server.engine.rules.definitions import _helpers as H


class ReconThenPersist(Rule):
    # reconhecimento seguido de modificacao de persistencia na janela
    name = "recon_then_persist"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        if H.persist_kind(cur) is None:
            return None
        for s in window[:-1]:
            if H.is_recon(s):
                return self.make_hit(
                    f"reconhecimento seguido de persistencia: {H.fpath(cur)}"
                )
        return None


class DownloadThenExec(Rule):
    # download para um caminho + execucao desse mesmo caminho na janela
    name = "download_then_exec"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        if not H.is_proc(cur):
            return None
        cur_paths = H.paths_in(H.cmd(cur))
        if not cur_paths:
            return None
        for s in window[:-1]:
            if H.is_proc(s) and ("curl" in H.cmd(s) or "wget" in H.cmd(s)):
                if cur_paths & H.paths_in(H.cmd(s)):
                    return self.make_hit(
                        f"execucao de artefato baixado: {H.cmd(cur)}", cur.get("pid")
                    )
        return None


class ProcessThenSensitiveFile(Rule):
    # processo suspeito seguido de modificacao de arquivo em /etc/ na janela
    name = "process_then_sensitive_file"
    severity = "CRITICAL"
    correlated = True

    def evaluate(self, event, window):
        cur = window[-1]
        if not (H.is_file(cur) and H.fpath(cur).startswith("/etc/")):
            return None
        for s in window[:-1]:
            if H.is_suspicious_proc(s):
                return self.make_hit(
                    f"processo suspeito seguido de alteracao em {H.fpath(cur)}",
                    s.get("pid"),
                )
        return None
