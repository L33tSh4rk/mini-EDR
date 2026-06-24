# MINI-EDR - ENDPOINT DETECTION AND RESPONSE (LINUX)

## DESCRIÇÃO DO PROJETO

Este projeto é um mini EDR (Endpoint Detection and Response) exclusivo para ambientes Linux, construído para demonstrar conceitos de sistemas distribuídos assíncronos. O sistema monitora processos, arquivos e conexões de rede em máquinas remotas (endpoints), correlaciona os eventos coletados em tempo real para identificar comportamentos suspeitos e disponibiliza alertas e controles de mitigação através de um dashboard web.

A arquitetura é composta por três componentes principais: um agente leve executado em containers Docker que coleta e transmite telemetria, um message broker Redis que atua como sistema circulatório do sistema distribuído, e um servidor FastAPI que processa os eventos, gera alertas e os entrega ao dashboard via WebSocket.

---

## ARQUITETURA

O fluxo de dados percorre o sistema de forma unidirecional: coleta → transporte → processamento → visualização. O canal de comandos opera no sentido inverso, do dashboard ao agente.

```
┌─────────────────────────────────────────────────────────────┐
│                  AGENTE  (container Docker)                 │
│  collectors ──► asyncio.Queue ──► envio em lote (TCP RPUSH) │
│  action module ◄────────────────── escuta de ordens (TCP)   │
└──────┬─────────────────────────────────────┬────────────────┘
       │                                     │
       │ TCP (RPUSH)                         │ TCP (SUBSCRIBE)
       │ HTTP POST (enroll)                  │
       │ UDP (heartbeat)                     │
       ▼                                     │
┌────────────────────────┐       ┌───────────┴──────────────────────────┐
│         REDIS          │       │              SERVIDOR                │
│                        │ BLPOP │  ┌─────────────────────────────────┐ │
│  telemetry_queue LIST  ├──────►│  │  Worker (task background)       │ │
│  alerts_channel PUB/SUB│◄──────│  │  consome fila, correlaciona,    │ │
│  commands:{id}  PUB/SUB├──────►│  │  publica alertas                │ │
│  corr:{id}      TTL   ◄├──────►│  └─────────────────────────────────┘ │
│                        │       │  ┌─────────────────────────────────┐ │
└────────────────────────┘       │  │  API (FastAPI)                  │ │
                                 │  │  enroll, heartbeat UDP, WS      │ │
                                 │  └──────────────────┬──────────────┘ │
                                 └─────────────────────┼────────────────┘
                                                       │ WebSocket (frames JSON)
                                                       ▼
                                             ┌───────────────────┐
                                             │     DASHBOARD     │
                                             │    (HTML / JS)    │
                                             └───────────────────┘
```

---

## COMPONENTES E RESPONSABILIDADES

### AGENTE (ENDPOINT)

Coletor e atuador executado dentro de containers Docker. Utiliza loops assíncronos com `asyncio` para realizar coleta, envio e escuta de forma concorrente.

**Módulo de Coleta (Agent Module):**
- Realiza o enrollment inicial junto ao servidor via HTTP POST.
- Coleta eventos de processos, arquivos e rede continuamente.
- Agrupa eventos em uma `asyncio.Queue` local (buffer) e descarrega em lotes JSON a cada 5 segundos no Redis via `RPUSH`.
- Envia heartbeats UDP periódicos ao servidor para sinalizar disponibilidade.

**Módulo de Atuação (Action Module):**
- Escuta o canal de comandos `commands:{agent_id}` no Redis via `SUBSCRIBE`.
- Executa ações locais de resposta: encerramento de processo (`os.kill`) e isolamento de rede (`iptables`).

**Mecanismo de Emergência:**
- Se a conexão TCP com o Redis for perdida por mais de 20 segundos, o agente executa regras de `iptables` autonomamente para isolar o host, mantendo contato exclusivo com o servidor. O isolamento pode ser revertido remotamente pelo servidor a qualquer momento.

---

### MESSAGE BROKER (REDIS)

Atua como o sistema circulatório do projeto, intermediando toda a comunicação entre os componentes. Utiliza quatro estruturas lógicas com nomes fixos:

| Estrutura | Nome | Tipo | Função |
|---|---|---|---|
| Fila de Telemetria | `telemetry_queue` | LIST | Recebe lotes JSON dos agentes e os disponibiliza para o Worker via `BLPOP` |
| Estado de Correlação | `corr:{agent_id}` | KEY (TTL 20s) | Armazena estados temporários utilizados pelo Worker para correlação de eventos |
| Canal de Alertas | `alerts_channel` | PUB/SUB | Transporta alertas confirmados do Worker para a API |
| Canal de Comandos | `commands:{agent_id}` | PUB/SUB | Transporta ordens de mitigação da API para o agente correspondente |

---

### SERVIDOR (FASTAPI + WORKER)

Núcleo de processamento e coordenação do sistema. Composto por dois subsistemas que operam de forma concorrente dentro do mesmo processo.

**API (FastAPI):**
- Recebe o cadastro inicial dos agentes (`/register`).
- Mantém um socket UDP ativo para receber e processar heartbeats.
- Controla o estado online/offline dos agentes registrados.
- Mantém conexões WebSocket abertas com o dashboard e multiplexa o tráfego via frames JSON tipados.
- Recebe ordens de mitigação do dashboard e as publica no canal Redis do agente alvo.
- Escuta o canal `alerts_channel` do Redis em background e encaminha alertas ao dashboard.

**Worker (task background):**
- Executa loop infinito bloqueante via `BLPOP` na `telemetry_queue` (não bloqueante de CPU).
- Filtra eventos por whitelist antes de processar.
- Aplica regras de correlação temporal utilizando chaves com TTL (`corr:{agent_id}`) no Redis.
- Gera objetos de alerta e os publica no `alerts_channel`.

---

### DASHBOARD

Interface web servida pelo FastAPI via Jinja2. Toda a comunicação com o servidor ocorre exclusivamente via WebSocket — sem requisições HTTP redundantes. O tráfego é multiplexado em frames JSON identificados por um campo `frame_type`.

- Renderiza o estado online/offline dos agentes em tempo real.
- Exibe alertas confirmados como cards ao vivo no momento em que são gerados.
- Permite ao operador disparar ordens de mitigação (`KILL`, `ISOLATE`, `LIFT`) diretamente pela interface.

---

## INTERFACES DE SERVIÇO

```
Agent
 ├─ enroll_agent()              → HTTP POST ao servidor com dados de identificação do host
 ├─ send_heartbeat()            → disparo UDP periódico para sinalizar disponibilidade
 ├─ send_events_batch()         → RPUSH assíncrono de lote JSON na telemetry_queue do Redis
 └─ listen_commands()           → loop SUBSCRIBE no canal commands:{agent_id} do Redis
    
Worker     
 ├─ consume_events_queue()      → loop infinito BLPOP na telemetry_queue do Redis
 ├─ correlate_events()          → leitura e escrita de chaves TTL (corr:{agent_id}) no Redis
 └─ publish_alert()             → PUBLISH de alerta JSON no alerts_channel do Redis
  
API
 ├─ route_register_agent()      → endpoint HTTP que recebe e registra o agente
 ├─ listen_udp_heartbeats()     → socket UDP ativo processando sinais de vida dos agentes
 ├─ route_websocket_dashboard() → canal WebSocket que gerencia as sessões do dashboard
 ├─ listen_worker_alerts()      → task background que consome alerts_channel e empurra ao WS
 └─ route_trigger_mitigation()  → publica comando de mitigação no Redis via frame do WS

Dashboard
 ├─ connect_websocket()         → abre canal de tempo real com a API
 ├─ on_alert_received()         → manipula o DOM para renderizar card de alerta ao vivo
 ├─ on_agent_status_change()    → atualiza a lista de agentes online/offline
 └─ trigger_order()             → envia frame de ordem de mitigação pelo WebSocket
```

---

## CONTRATOS DE OPERAÇÃO

Todos os contratos são transportados como JSON. O agente utiliza dicionários nativos Python e o servidor juntamente com o Worker utilizam modelos Pydantic para validação.

### Registro Inicial (HTTP POST → `/register`)

```json
{
  "agent_id": "string",
  "ip_address": "string",
  "hostname": "string"
}
```

### Heartbeat (texto bruto via UDP)

```
ALIVE:[agent_id]
```

### Lote de Eventos (Array JSON → `telemetry_queue`)

```json
[
  {
    "agent_id": "string",
    "timestamp": "ISO-8601-String",
    "event_type": "process_created | file_modified",
    "event_id": "uuid-string",
    "payload": {
      "pid": "int (se processo)",
      "process_name": "string (se processo)",
      "cmdline": "string (se processo)",
      "user": "string (se processo)",
      "file_path": "string (se arquivo)",
      "action": "string (se arquivo)"
    }
  }
]
```

### Alerta Confirmado (`alerts_channel` → WebSocket)

```json
{
  "frame_type": "new_alert",
  "timestamp": "ISO-8601-String",
  "data": {
    "agent_id": "string",
    "severity": "CRITICAL",
    "rule_triggered": "string",
    "description": "string",
    "culprit_pid": "int"
  }
}
```

### Ordem de Comando (WebSocket → API → `commands:{agent_id}`)

```json
{
  "frame_type": "trigger_order",
  "data": {
    "target_agent": "string",
    "command": "ISOLATE | KILL",
    "parameters": {
      "pid": "int (opcional)"
    }
  }
}
```

---

## ESCOPOS DE SISTEMAS DISTRIBUÍDOS UTILIZADOS

### Concorrência entre Processos

O sistema opera com múltiplos fluxos de execução concorrentes. No agente, quatro loops assíncronos rodam simultaneamente: coleta de processos, monitoramento de arquivos, descarregamento de lotes no Redis e escuta de ordens do servidor. No servidor, o FastAPI gerencia conexões WebSocket abertas com o dashboard enquanto o Worker executa independentemente, consumindo a fila do Redis e publicando alertas.

### Tolerância a Falhas

O agente implementa reconexão com backoff exponencial ao detectar falha na conexão com o Redis. Caso a interrupção exceda 20 segundos, o agente assume que o canal foi comprometido e executa isolamento preventivo via `iptables`, mantendo contato exclusivo com o servidor até receber ordem de retorno. O Redis opera com persistência assíncrona para garantir durabilidade dos lotes recebidos antes do consumo pelo Worker.

### Gerenciamento de Estado e Janela Deslizante

O Worker mantém estado de correlação temporal por agente usando chaves Redis com TTL de 20 segundos (`corr:{agent_id}`). Esse mecanismo usa uma janela deslizante que permite identificar sequências de eventos relacionados dentro de um intervalo de tempo sem necessidade de banco de dados externo.

---

## COMO COMPILAR E EXECUTAR

### Pré-requisitos

* Docker e Docker Compose instalados na máquina host.
* Porta `6379` disponível para o Redis.
* Porta `8000` disponível para o servidor FastAPI.



Na raiz do projeto, suba toda a infraestrutura em segundo plano:

```bash
docker compose up --build -d
```

Para acompanhar os logs do servidor em tempo real:

```bash
docker logs -f mini_edr_server
```

Para acompanhar os logs de um agente específico:

```bash
docker logs -f mini_edr_agent_<id>
```

Acesse o dashboard pelo navegador em:

```
http://localhost:8000
```

---

## BIBLIOTECAS UTILIZADAS

As bibliotecas padrão do Python (`asyncio`, `socket`, `os`, `uuid`, `dataclasses`) são utilizadas sem necessidade de instalação. As bibliotecas externas estão descritas abaixo:

| Biblioteca | Componente | Descrição |
|---|---|---|
| `psutil` | Agente | Coleta de informações de processos ativos, uso de CPU, memória e conexões de rede em tempo real |
| `watchdog` | Agente | Monitoramento de eventos do sistema de arquivos (criação, modificação, deleção) via callbacks assíncronos |
| `fastapi` | Servidor | Framework web assíncrono para construção da API REST e dos endpoints WebSocket |
| `uvicorn` | Servidor | Servidor ASGI de alta performance utilizado para execução do FastAPI |
| `redis` (asyncio) | Servidor / Agente | Cliente Redis com suporte a operações assíncronas (`RPUSH`, `BLPOP`, `PUBLISH`, `SUBSCRIBE`) |
| `pydantic` | Servidor / Worker | Validação e serialização dos contratos JSON recebidos e emitidos pelo servidor |
| `jinja2` | Servidor / Dashboard | Engine de templates para renderização do dashboard HTML servido pelo FastAPI |

---
