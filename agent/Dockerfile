# imagem do agente (endpoint) do mini-edr

FROM python:3.12-slim

# iptables: usado pelo modulo de atuacao (isolamento de host)
# procps: inspecao de processos
RUN apt-get update \
    && apt-get install -y --no-install-recommends iptables procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# garante que /var/www exista no boot para o watchdog observar (web shell demo)
RUN mkdir -p /var/www/html

# instala as dependencias do agente primeiro (cache de camada)
COPY agent/requirements.txt agent/requirements.txt
RUN pip install --no-cache-dir -r agent/requirements.txt

# copia o codigo do agente
COPY agent/ agent/

# inicia o agente como modulo (imports de pacote agent.*)
CMD ["python", "-m", "agent.main"]
