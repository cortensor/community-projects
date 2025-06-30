from enum import Enum


class PERFORMANCE_STYLE(Enum):
    OFF = -1
    FULL = 0
    PIN = 1


class ChatConfig:
    def __init__(
        self,
        chat_id: str,
        notification_node_status: bool = True,
        notification_failed_tx: bool = False,
        metrics_warning_threshold: int = -100,
        metrics_drop_threshold: int = -1,
        active: bool = True,
        bonus_roles: int = 0,
        new_nodes: int = 0,
        performance_style: PERFORMANCE_STYLE = PERFORMANCE_STYLE.FULL
    ):
        self.chat_id = chat_id
        self.notification_node_status = notification_node_status
        self.notification_failed_tx = notification_failed_tx
        self.metrics_warning_threshold = metrics_warning_threshold
        self.metrics_drop_threshold = metrics_drop_threshold
        self.active = active
        self.bonus_roles = bonus_roles
        self.new_nodes = new_nodes
        self.performance_style = performance_style
