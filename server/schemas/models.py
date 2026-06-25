# modelos pydantic baseados em contratos json 

from typing import Literal, Optional

from pydantic import BaseModel


class EnrollRequest(BaseModel):
    # contrato de registro inicial recebido via http post
    agent_id: str
    ip_address: str
    hostname: str


class TriggerParameters(BaseModel):
    # parametros opcionais de uma ordem de mitigacao
    pid: Optional[int] = None


class TriggerOrderData(BaseModel):
    # corpo da ordem de mitigacao
    target_agent: str
    command: Literal["ISOLATE", "KILL", "LIFT"]
    parameters: TriggerParameters = TriggerParameters()


class TriggerOrder(BaseModel):
    # frame de ordem recebido do dashboard via websocket
    frame_type: Literal["trigger_order"]
    data: TriggerOrderData


class AlertData(BaseModel):
    # corpo de um alerta confirmado pelo worker
    agent_id: str
    severity: str
    rule_triggered: str
    description: str
    culprit_pid: Optional[int] = None


class AlertFrame(BaseModel):
    # frame de alerta publicado em alerts_channel
    frame_type: Literal["new_alert"]
    timestamp: str
    data: AlertData


class EventPayload(BaseModel):
    # payload de um evento de telemetria (campos opcionais conforme o tipo)
    pid: Optional[int] = None
    process_name: Optional[str] = None
    cmdline: Optional[str] = None
    user: Optional[str] = None
    file_path: Optional[str] = None
    action: Optional[str] = None


class TelemetryEvent(BaseModel):
    # envelope de um evento enviado pelo agente na telemetry_queue
    agent_id: str
    timestamp: str
    event_type: Literal["process_created", "file_modified"]
    event_id: str
    payload: EventPayload
