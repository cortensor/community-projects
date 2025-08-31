# TODO: Name NOTIFY_STATUS and no CANCEL?
from enum import Enum
from datetime import datetime


class NODE_STATUS(Enum):
    UNKNOWN = -1
    OFFLINE = 0
    ONLINE = 1
    STALL = 2


class NodeData:
    def __init__(
        self,
        address: str,
        balance=0.0,
        last_block: int = 0,
        last_block_ts: int = 0,
        failed_txs: list=None,
        timestamps: list[int]=None,
        history: str = "",
        history_end_ts: int = None,
        status: NODE_STATUS = NODE_STATUS.UNKNOWN,
        updated_at: datetime = None,
        notify=False,
        consecutive_pings: int = 0,
        metrics = [],
        rank_score = 0,
        rank: int = None,
        too_many_pings = False,
        level = 0
    ):
        self.address = address.lower()
        self.status = status
        self.balance = balance
        self.last_block = last_block
        self.last_block_ts = last_block_ts
        self.history = history
        self.history_end_ts = history_end_ts
        self.timestamps = timestamps if timestamps is not None else []
        self.failed_txs = failed_txs if failed_txs is not None else []
        self.updated_at = updated_at
        self.notify = notify
        self.consecutive_pings = consecutive_pings
        self.metrics = metrics
        self.rank_score = rank_score
        self.rank = rank
        self.too_many_pings = too_many_pings
        self.level = level
