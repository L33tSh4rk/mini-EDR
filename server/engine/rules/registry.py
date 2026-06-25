# registro das regras ativas, separadas por tipo (evento unico x correlacao)

from server.engine.rules.definitions.c1_shell import (
    Base64Exec,
    DownloadExecPipe,
    ReverseShellClassic,
    ReverseShellInterpreter,
)
from server.engine.rules.definitions.c2_discovery import (
    NetworkRecon,
    PasswdEnum,
    PrivEnumBurst,
)
from server.engine.rules.definitions.c3_persistence import (
    CrontabCmdModified,
    CrontabFileModified,
    ShellProfileBackdoor,
    SshAuthorizedKeys,
    SystemdServiceDrop,
)
from server.engine.rules.definitions.c4_privesc import (
    LdPreloadHijack,
    ShadowModified,
    SudoersModified,
    SuidBinaryCreated,
)
from server.engine.rules.definitions.c5_execution import ExecFromTmpdir
from server.engine.rules.definitions.c6_antiforensics import (
    HistoryWipe,
    LogWipe,
    TimestampTampering,
)
from server.engine.rules.definitions.c7_correlation import (
    DownloadThenExec,
    ProcessThenSensitiveFile,
    ReconThenPersist,
)
from server.engine.rules.definitions.sequences import (
    CredentialDumpAndStage,
    DoublePersistence,
    DropperChmodExec,
    KernelModuleDrop,
    LolbinInterpreterDrop,
    RapidLogWipe,
    ScriptDropperTrilogy,
    SudoEnumThenAbuse,
    UserBackdoorConfirmed,
    WebShellImplant,
)

# regras de evento unico: rodam em todo evento
EVENT_RULES = [
    ReverseShellClassic(),
    ReverseShellInterpreter(),
    DownloadExecPipe(),
    Base64Exec(),
    PasswdEnum(),
    NetworkRecon(),
    CrontabFileModified(),
    CrontabCmdModified(),
    ShellProfileBackdoor(),
    SshAuthorizedKeys(),
    SystemdServiceDrop(),
    ShadowModified(),
    SudoersModified(),
    LdPreloadHijack(),
    SuidBinaryCreated(),
    ExecFromTmpdir(),
    LogWipe(),
    HistoryWipe(),
    TimestampTampering(),
]

# regras de correlacao: usam a janela rodam so em evento notavel com dedup
CORRELATION_RULES = [
    PrivEnumBurst(),
    ReconThenPersist(),
    DownloadThenExec(),
    ProcessThenSensitiveFile(),
    DropperChmodExec(),
    WebShellImplant(),
    UserBackdoorConfirmed(),
    DoublePersistence(),
    KernelModuleDrop(),
    ScriptDropperTrilogy(),
    CredentialDumpAndStage(),
    SudoEnumThenAbuse(),
    RapidLogWipe(),
    LolbinInterpreterDrop(),
]


def evaluate_event_rules(event):
    # roda as regras de evento unico e retorna a lista de hits
    hits = []
    for rule in EVENT_RULES:
        hit = rule.evaluate(event, None)
        if hit is not None:
            hits.append(hit)
    return hits


def evaluate_correlation_rules(event, window):
    # roda as regras de correlacao sobre a janela e retorna a lista de hits
    hits = []
    for rule in CORRELATION_RULES:
        hit = rule.evaluate(event, window)
        if hit is not None:
            hits.append(hit)
    return hits
