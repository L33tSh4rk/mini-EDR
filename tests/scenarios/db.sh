#!/usr/bin/env bash
# endpoint db-02: enumeracao de credenciais + dump com staging
# rodar dentro do agente: docker compose exec -T agent_db bash -s < tests/scenarios/db.sh
set -u
spoof() { bash -c "exec -a \"$1\" sleep 60" >/dev/null 2>&1 & }
step()  { sleep 3; }

echo "[db-02] (1) enumeracao de /etc/passwd"
spoof "cat /etc/passwd"
step

echo "[db-02] (2) dump de credenciais + staging em /tmp"
spoof "cat /etc/shadow"
step
spoof "tee /tmp/dump.txt"
step
printf 'root:HASH\n' > /tmp/dump.txt
step

echo "[db-02] concluido"
