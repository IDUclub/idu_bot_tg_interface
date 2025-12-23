class BotRequestException(Exception):

    def __init__(
        self,
        msg: str,
        http_code: int,
        _input: dict | None = None,
        _detail: dict | None = None,
    ):

        self.msg = msg
        self.http_code = http_code
        self._input = _input
        self._detail = _detail
        super().__init__(msg)
