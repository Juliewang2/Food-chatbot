from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import db_helper
import generic_helper
import dialogflow_client

app = FastAPI()

# 前端文件夹：FoodChatBot/frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# 每个会话正在下的订单，例如 {'session_id_1': {"Pizza": 2, "Mango Lassi": 1}}
inprogress_orders = {}


@app.get("/")
async def home():
    # 浏览器打开 ngrok 网址时返回网站首页；Dialogflow 的 webhook 走下面的 POST /
    return FileResponse(FRONTEND_DIR / "home.html")


@app.get("/health")
async def health():
    return {"status": "FoodChatBot backend is running"}


@app.post("/chat")
def chat(body: dict):
    # 注意这里用普通 def（在线程池里运行）：detectIntent 期间 Dialogflow 会回调本服务器的 POST /，
    # 如果用 async def 会卡住事件循环，webhook 进不来，导致超时
    session_id = str(body.get("session_id") or "default")
    try:
        reply = dialogflow_client.detect_intent(
            session_id, text=body.get("message", ""), event=body.get("event", ""))
    except Exception as e:
        print(f"[chat] Dialogflow error: {e}")
        return JSONResponse(status_code=500, content={
            "reply": "Sorry, the chatbot is not available right now. (Check the backend terminal for details.)"
        })
    return {"reply": reply or "Sorry, I didn't get that. Can you say it again?"}


@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    print(f"[webhook] intent={intent!r} parameters={parameters}")
    # payload['session'] 每次请求都有，比 outputContexts 可靠（contexts 过期后可能为空）
    session_id = generic_helper.extract_session_id(payload.get('session', ''))
    intent_handler_dict = {
        'new.order': new_order,
        'order.add - context: ongoing-order': add_to_order,
        'order.remove - context: ongoing-order': remove_from_order,
        'order.complete - context: ongoing-order': complete_order,
        'track.order - context: ongoing-tracking': track_order
    }
    if intent not in intent_handler_dict:
        # 后端不处理的 intent：返回空，让 Dialogflow 使用 intent 里写好的 Response
        return JSONResponse(content={})
    return intent_handler_dict[intent](parameters, session_id)


def new_order(parameters: dict, session_id: str):
    # 开始新订单时清空这个会话之前没下完的订单
    inprogress_orders.pop(session_id, None)
    # 不返回 fulfillmentText，Dialogflow 会继续使用 intent 里写好的 Response
    return JSONResponse(content={})


def add_to_order(parameters: dict, session_id: str):
    # 键名要和 Dialogflow 里的参数名完全一致
    food_items = parameters.get("food-item", [])
    quantities = parameters.get("number1", [])
    if not food_items or len(food_items) != len(quantities):
        fulfillment_text = "Sorry I did not understand. Can you please specify food items and quantities clearly?"
    else:
        current_food_dict = inprogress_orders.setdefault(session_id, {})
        # 同一道菜再点一次时累加数量，而不是覆盖
        for food, qty in zip(food_items, quantities):
            current_food_dict[food] = current_food_dict.get(food, 0) + int(qty)
        print(inprogress_orders[session_id])
        order_str = generic_helper.get_str_from_food_dict(current_food_dict)
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order please?"
        })

    current_order = inprogress_orders[session_id]
    food_items = parameters.get("food-item", [])
    # 数量参数可选：没说数量（"remove pizza"）就整道菜删掉；说了数量（"remove one pizza"）就做减法
    quantities = parameters.get("number", [])
    if not isinstance(quantities, list):
        quantities = [quantities]
    if quantities and len(quantities) != len(food_items):
        return JSONResponse(content={
            "fulfillmentText": "Sorry I did not understand. Can you please specify the quantity for each food item you want to remove?"
        })
    if not quantities:
        quantities = [None] * len(food_items)

    removed_items = []
    no_such_items = []
    for item, qty in zip(food_items, quantities):
        if item not in current_order:
            no_such_items.append(item)
            continue
        if qty is None or int(qty) >= current_order[item]:
            removed_items.append(f"{int(current_order[item])} {item}")
            del current_order[item]
        else:
            current_order[item] -= int(qty)
            removed_items.append(f"{int(qty)} {item}")

    fulfillment_text = ""
    if removed_items:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order! "
    if no_such_items:
        fulfillment_text += f"Your current order does not have {', '.join(no_such_items)}. "
    if not current_order:
        fulfillment_text += "Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f"Here is what is left in your order: {order_str}"
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text.strip()
    })


def complete_order(parameters: dict, session_id: str):
    if not inprogress_orders.get(session_id):
        fulfillment_text = "I'm having trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again."
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = f"Awesome. We have placed your order. " \
                               f"Here is your order id #{order_id}. " \
                               f"Your order total is {order_total} which you can pay at the time of delivery!"
        # 不管成功与否，这个会话的临时订单都清掉
        del inprogress_orders[session_id]
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def save_to_db(order: dict):
    # order = {"Pizza": 2, "Chole Bhature": 1}
    next_order_id = db_helper.get_next_order_id()
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if rcode == -1:
            return -1
    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id


def track_order(parameters: dict, session_id: str):
    try:
        order_id = int(parameters['order_id'])
    except (KeyError, TypeError, ValueError):
        return JSONResponse(content={
            "fulfillmentText": "Please tell me a valid order id, for example: track order 41"
        })
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


# 放在所有路由之后：styles.css、banner.jpg 等静态文件
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
