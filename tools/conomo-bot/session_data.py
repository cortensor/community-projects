class SessionData:
    def __init__(
        self,
        id: int = None,
        created: str = None,
        started: str = None,
        ended: str = None
    ):
        self.id = id
        self.created = created
        self.started = started
        self.ended = ended

    def __str__(self):
        return f"Id: {self.id}\nCreated: {self.created}\nStarted: {self.started}\nEnded: {self.ended}\n"
