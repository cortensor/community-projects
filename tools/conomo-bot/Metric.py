KNOWN_METRIC_NAMES = [
    "Request",
    "Create",
    "Prepare",
    "Start",
    "Precommit",
    "Commit",
    "End",
    "Correctness",
    "Ping",
    "Global Ping"
]


class Metric:
    def __init__(
        self,
        name: str,
        points=0,
        counter: int = 0,
        # success_rate: float = None,#
        prior_success_rate_drop: float = 0.0,
        visible: bool = True
    ):
        self.name = name
        self.success_rate = None
        self.points = points
        self.counter = counter
        self._update_success_rate()
        self.prior_success_rate_drop = prior_success_rate_drop
        self.visible = visible

    def set_points(self, points):
        self.points = points
        self._update_success_rate()

    def set_counter(self, counter):
        self.counter = counter
        self._update_success_rate()


    def _update_success_rate(self) -> float:
        if self.name == "Ping" or self.name == "Global Ping":
            return
        self.success_rate = round((self.points / self.counter * 100), 2) if self.counter else None