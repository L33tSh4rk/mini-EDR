# modulo de atuacao: executa acoes locais de resposta (kill e isolamento)

import asyncio
import os
import signal
import socket
import subprocess

from agent.core import config


def _run(cmd):
    # executa um comando iptables; retorna true so quando teve sucesso (rc 0)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        # binario ausente ou argumento invalido
        print(f"[actions] falha ao executar {cmd} ({exc})")
        return False
    if proc.returncode != 0:
        # sem permissao, regra inexistente, etc.
        print(f"[actions] '{' '.join(cmd)}' rc={proc.returncode}: {proc.stderr.strip()}")
        return False
    return True


def _policy(chain):
    # le a politica default atual de uma chain (ACCEPT/DROP) para restaurar depois
    try:
        proc = subprocess.run(["iptables", "-S", chain], capture_output=True, text=True)
    except OSError:
        return "ACCEPT"
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "-P" and parts[1] == chain:
            return parts[2]
    return "ACCEPT"


def _resolve(host):
    # resolve hostname para ip; usado no isolamento enquanto o dns ainda funciona
    try:
        return socket.gethostbyname(host)
    except OSError:
        return host


def _iso_rules(server_ip, redis_ip):
    # excecoes de accept inseridas no isolamento, ja com IPs resolvidos.
    # usar ip (e nao hostname) garante que o -D no lift case sem depender de dns
    # (o dns fica bloqueado pela propria politica de isolamento).
    return [
        ["INPUT", "-i", "lo", "-j", "ACCEPT"],
        ["OUTPUT", "-o", "lo", "-j", "ACCEPT"],
        ["OUTPUT", "-d", server_ip, "-j", "ACCEPT"],
        ["INPUT", "-s", server_ip, "-j", "ACCEPT"],
        ["OUTPUT", "-d", redis_ip, "-j", "ACCEPT"],
        ["INPUT", "-s", redis_ip, "-j", "ACCEPT"],
    ]


async def execute_kill(pid):
    # encerra um processo local pelo pid via sigkill
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, os.kill, int(pid), signal.SIGKILL)
        return True
    except (ProcessLookupError, PermissionError, ValueError, TypeError):
        # pid inexistente, sem permissao ou invalido
        return False


async def execute_isolation(state):
    # isola o host via iptables, preservando regras pre-existentes
    if state.isolated:
        # ja isolado, nada a fazer
        return
    loop = asyncio.get_running_loop()
    # resolve server/redis para ip agora (dns ainda disponivel antes do drop)
    server_ip = await loop.run_in_executor(None, _resolve, config.SERVER_HOST)
    redis_ip = await loop.run_in_executor(None, _resolve, config.REDIS_HOST)
    # salva as politicas atuais para restaurar no lift (nao destruir firewall existente)
    saved = {}
    for chain in ("INPUT", "OUTPUT"):
        saved[chain] = await loop.run_in_executor(None, _policy, chain)
    rules = _iso_rules(server_ip, redis_ip)
    ok = True
    # insere as excecoes ANTES de fechar a politica (evita corte de server/redis)
    for r in rules:
        ok = await loop.run_in_executor(None, _run, ["iptables", "-A"] + r) and ok
    ok = await loop.run_in_executor(None, _run, ["iptables", "-P", "INPUT", "DROP"]) and ok
    ok = await loop.run_in_executor(None, _run, ["iptables", "-P", "OUTPUT", "DROP"]) and ok
    if ok:
        # so assume isolado quando o iptables confirmou (nao mente sobre o estado)
        state.iso_rules = rules
        state.iso_policies = saved
        state.isolated = True
        print("[actions] host isolado")
    else:
        # falhou no meio: remove o que deu pra inserir e nao marca como isolado
        print("[actions] isolamento incompleto (iptables falhou); revertendo parcial")
        for r in rules:
            await loop.run_in_executor(None, _run, ["iptables", "-D"] + r)


async def lift_isolation(state):
    # reverte o isolamento removendo SO as regras inseridas e restaurando politicas
    loop = asyncio.get_running_loop()
    for r in state.iso_rules:
        await loop.run_in_executor(None, _run, ["iptables", "-D"] + r)
    for chain in ("INPUT", "OUTPUT"):
        policy = state.iso_policies.get(chain, "ACCEPT")
        await loop.run_in_executor(None, _run, ["iptables", "-P", chain, policy])
    state.iso_rules = []
    state.iso_policies = {}
    state.isolated = False
    print("[actions] isolamento revertido")
