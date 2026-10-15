import re
def extract_session_id(session_str: str):
    # 支持 ".../sessions/<id>" 和 ".../sessions/<id>/contexts/<name>" 两种格式
    match = re.search(r"/sessions/([^/]+)", session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string
    return ""
def get_str_from_food_dict(food_dict: dict):
    return ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
if __name__=="__main__":
    print(get_str_from_food_dict({"samosa": 2, "chhole": 5}))
    print(extract_session_id("projects/jiayi-chatbot-for-food-de-qfot/agent/sessions/172c1624-fc72-adb9-98cb-1804cbfeb813/contexts/ongoing-order"))