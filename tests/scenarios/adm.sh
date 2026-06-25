#!/usr/bin/env bash
# endpoint adm-04: abuso de sudo (gtfobin) + criacao de binario suid
# rodar dentro do agente: docker compose exec -T agent_adm bash -s < tests/scenarios/adm.sh
set -u
spoof() { bash -c "exec -a \"$1\" sleep 60" >/dev/null 2>&1 & }
step()  { sleep 3; }

echo "[adm-04] (1) enumeracao de sudo + abuso de gtfobin (vim)"
spoof "sudo -l"
step
spoof "sudo vim /etc/shadow"
step

echo "[adm-04] (2) criacao de binario suid"
spoof "chmod +s /usr/local/bin/backdoor"
step

echo "[adm-04] concluido"
