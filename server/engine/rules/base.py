# interface base das regras de deteccao e o resultado de um disparo

from dataclasses import dataclass
from typing import Optional


@dataclass
class RuleHit:
    # resultado de uma regra que disparou
    rule_triggered: str
    severity: str
    description: str
    culprit_pid: Optional[int] = None
    # regra de correlacao
    correlated: bool = False


class Rule:
    # contrato que toda regra deve implementar
    name = "rule"
    # severidade do alerta gerado pela regra
    severity = "CRITICAL"
    # true para regras que usam a janela (dedup por janela aplicado pelo worker)
    correlated = False

    def make_hit(self, description, culprit_pid=None):
        # monta resultado preenchendo nome, severidade e tipo da propria regra
        return RuleHit(
            rule_triggered=self.name,
            severity=self.severity,
            description=description,
            culprit_pid=culprit_pid,
            correlated=self.correlated,
        )

    def evaluate(self, event, window) -> Optional[RuleHit]:
        # recebe evento atual e janela de correlacao e retorna hit ou none
        raise NotImplementedError
