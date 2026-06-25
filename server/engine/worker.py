# entrypoint do worker: consome telemetry_queue, correlaciona e publica alertas

import asyncio
import json

import redis.asyncio as aioredis
import redis.exceptions
from pydantic import ValidationError

from server import config
from server.engine import correlation, whitelist
from server.engine.alerting import build_alert, publish_alert
from server.engine.rules.registry import (
    evaluate_correlation_rules,
    evaluate_event_rules,
)
from server.schemas.models import TelemetryEvent

# tokens/indicadores que tornam um evento "notavel" para a correlacao
NOTABLE_PROC_TOKENS = (
    "curl", "wget", "chmod", "insmod", "modprobe", "useradd", "adduser",
    "tee", "dd", "cp ", "cat", "strings", "sudo", "apache", "nginx", "php",
    "python", "perl", "ruby", "/tmp/", "/dev/shm/", "/var/tmp/", ".ko", "socket",
)
# nomes de processo (match exato) que sao indicadores de recon/sequencia
NOTABLE_PROC_NAMES = (
    "id", "whoami", "uname", "crontab", "insmod", "modprobe",
    "useradd", "adduser", "nc", "ncat", "socat",
)
NOTABLE_FILE_HINTS = (
    "/etc/", "/var/log/", "/var/spool/cron", "/var/www", "/srv/www",
    "/lib/modules/", "/.ssh/", ".bashrc", ".bash_profile", ".profile", ".ko",
    # diretorios de staging: arquivo criado em tmp completa cadeias de dropper
    "/tmp/", "/dev/shm/", "/var/tmp/",
)


def _is_notable(event, event_hits):
    # so vale rodar a correlacao (busca na janela) em evento notavel
    if event_hits:
        return True
    p = event.payload
    if event.event_type == "file_modified":
        path = p.file_path or ""
        return any(h in path for h in NOTABLE_FILE_HINTS)
    if event.event_type == "process_created":
        name = (p.process_name or "").lower()
        if name in NOTABLE_PROC_NAMES:
            return True
        text = ((p.cmdline or "") + " " + name)
        return any(t in text for t in NOTABLE_PROC_TOKENS)
    return False


async def _emit(client, agent_id, hit):
    # monta e publica o alerta de um hit
    alert = build_alert(agent_id, hit)
    await publish_alert(client, alert)
    print(f"[worker] alerta: {hit.rule_triggered} agente={agent_id} pid={hit.culprit_pid}")


async def process_event(client, raw_event):
    # valida, filtra, correlaciona e aplica regras a um unico evento
    try:
        event = TelemetryEvent.model_validate(raw_event)
    except ValidationError:
        # evento malformado, descarta
        return
    # descarta eventos benignos antes de qualquer regra
    if whitelist.is_whitelisted(event):
        return

    event_hits = evaluate_event_rules(event)

    # registra na janela de correlacao (ttl) e obtem estado
    state = await correlation.record_event(client, event)

    for hit in event_hits:
        await _emit(client, event.agent_id, hit)

    # correlacao so em evento notavel
    if not _is_notable(event, event_hits):
        return

    # regras de correlacao com dedup por janela (estado fired em corr)
    fired = state["fired"]
    changed = False
    for hit in evaluate_correlation_rules(event, state["window"]):
        if hit.rule_triggered in fired:
            # ja disparou nesta janela, suprime
            continue
        await _emit(client, event.agent_id, hit)
        fired.append(hit.rule_triggered)
        changed = True
    if changed:
        # persiste as regras marcadas como disparadas nesta janela
        await correlation.persist_fired(client, event.agent_id, state)


async def consume_events_queue(client):
    # loop bloqueante blpop consumindo lotes da fila de telemetria
    while True:
        # blpop com timeout curto e retorna none quando a fila esta ociosa
        try:
            item = await client.blpop(config.TELEMETRY_QUEUE, timeout=5)
        except redis.exceptions.TimeoutError:
            # ociosidade: o socket atingiu o timeout do blpop sem eventos -> apenas continua aguardando (sem reconectar)
            continue
        if item is None:
            continue
        _, raw = item
        try:
            batch = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # lote malformado, descarta
            continue
        if not isinstance(batch, list):
            # contrato espera um array de eventos
            continue
        for raw_event in batch:
            await process_event(client, raw_event)


async def main():
    # conecta no redis e roda consumo com reconexao em backoff
    backoff = 1
    while True:
        client = aioredis.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
        )
        try:
            print("[worker] consumindo telemetry_queue…")
            backoff = 1
            await consume_events_queue(client)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError) as exc:
            # perdeu o redis: reconecta com backoff exponencial
            print(f"[worker] conexao perdida ({exc}), retry em {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 20)
        finally:
            await client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # encerramento via ctrl+c
        print("\n[worker] encerrado")
