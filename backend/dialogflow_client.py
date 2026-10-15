import os
from pathlib import Path

# 网页聊天窗口 -> 后端 /chat -> 这里调用 Dialogflow detectIntent -> Dialogflow 再调用我们的 webhook (POST /)
PROJECT_ID = "jiayi-chatbot-for-food-de-qfot"
LANGUAGE_CODE = "en"
# 服务账号密钥放在 backend 文件夹里，文件名 dialogflow-key.json
KEY_FILE = Path(__file__).resolve().parent / "dialogflow-key.json"

_client = None


def get_client():
    global _client
    if _client is None:
        if KEY_FILE.exists():
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(KEY_FILE))
        from google.cloud import dialogflow_v2 as dialogflow
        _client = dialogflow.SessionsClient()
    return _client


def detect_intent(session_id: str, text: str = "", event: str = ""):
    from google.cloud import dialogflow_v2 as dialogflow
    client = get_client()
    session = client.session_path(PROJECT_ID, session_id)
    if event:
        query_input = dialogflow.QueryInput(
            event=dialogflow.EventInput(name=event, language_code=LANGUAGE_CODE))
    else:
        query_input = dialogflow.QueryInput(
            text=dialogflow.TextInput(text=text, language_code=LANGUAGE_CODE))
    response = client.detect_intent(request={"session": session, "query_input": query_input})
    return response.query_result.fulfillment_text
