#!/usr/bin/env bash
# dispara 5 cenarios de ataque em paralelo, cada um dentro do seu endpoint.
# pre-requisito: docker compose --profile demo up -d  (os 5 agentes no ar)
# uso: bash tests/scenarios/demo_all.sh

set -u
cd "$(dirname "$0")/../.." || exit 1   # raiz do projeto (onde esta o docker-compose.yml)

for role in web db app adm bkp; do
  echo ">> atacando agent_${role} (cenario ${role})"
  docker compose exec -T "agent_${role}" bash -s < "tests/scenarios/${role}.sh" &
done
wait
echo ">> demonstracao concluida (veja o dashboard / logs do worker)"
