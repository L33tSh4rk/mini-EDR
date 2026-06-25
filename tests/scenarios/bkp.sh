#!/usr/bin/env bash
# endpoint bkp-05: anti-forense (log/historico) + persistencia via cron
# rodar dentro do agente: docker compose exec -T agent_bkp bash -s < tests/scenarios/bkp.sh
set -u
spoof() { bash -c "exec -a \"$1\" sleep 60" >/dev/null 2>&1 & }
step()  { sleep 3; }

echo "[bkp-05] (1) destruicao de log"
spoof "rm /var/log/auth.log"
step

echo "[bkp-05] (2) limpeza de historico"
spoof "history -c"
step

echo "[bkp-05] (3) persistencia via cron"
printf '* * * * * root /tmp/implant\n' >> /etc/crontab
step

echo "[bkp-05] concluido"
