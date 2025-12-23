import json
from typing import AsyncIterator

import websockets


class WebsocketAPIHandler:

    def __init__(self, base_url: str):

        self.base_url = base_url.rstrip("/")

    async def get_streaming_response(
        self,
        endpoint_url: str,
        json_message: dict,
    ) -> AsyncIterator[dict]:

        url = f"{self.base_url}/{endpoint_url.lstrip('/')}"

        async with websockets.connect(
            url,
        ) as ws:

            await ws.send(json.dumps(json_message))

            async for message in ws:
                yield json.loads(message)
