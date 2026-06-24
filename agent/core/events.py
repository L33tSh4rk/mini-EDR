# fabrica de eventos em dict nativo seguindo o contrato de lote de eventos

import uuid
from datetime import datetime, timezone


def _now_iso():
    # timestamp atual em iso-8601 com timezone
    return datetime.now(timezone.utc).isoformat()


def make_event(agent_id, event_type, payload):
    # monta o envelope padrao de um evento
    return {
        "agent_id": agent_id,
        "timestamp": _now_iso(),
        "event_type": event_type,
        "event_id": str(uuid.uuid4()),
        "payload": payload,
    }


def process_event(agent_id, pid, process_name, cmdline, user):
    # monta evento de criacao de processo
    payload = {
        "pid": pid,
        "process_name": process_name,
        "cmdline": cmdline,
        "user": user,
    }
    return make_event(agent_id, "process_created", payload)


def file_event(agent_id, file_path, action):
    # monta evento de modificacao de arquivo
    payload = {
        "file_path": file_path,
        "action": action,
    }
    return make_event(agent_id, "file_modified", payload)
