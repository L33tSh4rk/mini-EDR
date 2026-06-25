# builder e publisher de alertas no canal alerts_channel

import json
from datetime import datetime, timezone

from server import config
from server.schemas.models import AlertData, AlertFrame


def build_alert(agent_id, hit):
    # monta o frame de alerta no contrato estrito a partir de um rule hit
    data = AlertData(
        agent_id=agent_id,
        severity=hit.severity,
        rule_triggered=hit.rule_triggered,
        description=hit.description,
        culprit_pid=hit.culprit_pid,
    )
    return AlertFrame(
        frame_type="new_alert",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=data,
    )


async def publish_alert(client, alert):
    # publica o alerta serializado no canal de alertas
    await client.publish(config.ALERTS_CHANNEL, json.dumps(alert.model_dump()))
