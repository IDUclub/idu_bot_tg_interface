from typing import AsyncIterator

from loguru import logger

from app.common.api_handlers import JSONAPIHandler, WebsocketAPIHandler


class IduLLMApiClient:

    def __init__(
        self,
        json_api_handler: JSONAPIHandler,
        websocket_api_handler: WebsocketAPIHandler,
    ):

        self.json_api_handler: JSONAPIHandler = json_api_handler
        self.websocket_api_handler: WebsocketAPIHandler = websocket_api_handler

    # TODO revise index handling
    async def get_available_indexes(self) -> list[str]:

        result = await self.json_api_handler.get("api/v1/llm/indexes")
        return [
            i
            for i in result
            if i
            not in ("Информация проекта", "Общее о проекте", "Информация о проекте")
        ]

    async def get_response_from_llm(
        self, index: str, user_request: str
    ) -> AsyncIterator[dict[str, str]]:

        request_data = {
            "index_name": index,
            "user_request": user_request,
        }
        try:
            async for chunk in self.websocket_api_handler.get_streaming_response(
                "ws/generate", request_data
            ):
                yield chunk
        except Exception as e:
            logger.exception(e)
            raise e
