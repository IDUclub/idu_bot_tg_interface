from iduconfig import Config

from app.api_clients import IduLLMApiClient
from app.common.api_handlers import JSONAPIHandler, WebsocketAPIHandler

config = Config()

idu_llm_json_api_handler = JSONAPIHandler(config.get("IDU_LLM_HTTP_URL"))
ws_api_handler = WebsocketAPIHandler(config.get("IDU_LLM_WS_URL"))

idu_llm_api_client = IduLLMApiClient(idu_llm_json_api_handler, ws_api_handler)
