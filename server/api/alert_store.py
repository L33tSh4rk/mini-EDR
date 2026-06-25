# armazena os alertas ativos (ainda nao acionados) para reenvio no refresh
# estado em memoria no servidor. some no restart do servidor (sem persistencia)

import uuid
from collections import OrderedDict


class AlertStore:
    # guarda os frames new_alert ativos, indexados por um alert_id gerado

    def __init__(self, maxlen=200):
        self._alerts = OrderedDict()
        self.maxlen = maxlen

    def add(self, frame):
        # atribui um alert_id ao frame, guarda e retorna o id
        alert_id = str(uuid.uuid4())
        frame.setdefault("data", {})["alert_id"] = alert_id
        self._alerts[alert_id] = frame
        # limita o uso de memoria descartando os mais antigos
        while len(self._alerts) > self.maxlen:
            self._alerts.popitem(last=False)
        return alert_id

    def remove(self, alert_id):
        # remove um alerta (acionado/dispensado) e retorna frame ou none
        return self._alerts.pop(alert_id, None)

    def all(self):
        # lista alertas ativos por ordem de chegada
        return list(self._alerts.values())
