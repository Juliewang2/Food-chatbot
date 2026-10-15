import os
import mysql.connector

# 数据库连接信息从环境变量读取，避免把密码写进代码；没设置时使用本地默认值
cnx = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "root"),
    database=os.getenv("DB_NAME", "pandeyji_eatery")
)
def get_cursor():
    # 长时间不用时 MySQL 会断开连接，这里自动重连
    cnx.ping(reconnect=True, attempts=3, delay=1)
    return cnx.cursor()


def insert_order_item(food_item: str, quantity: int, order_id: int):
    # 调用数据库里的存储过程 insert_order_item，成功返回 1，失败返回 -1
    try:
        cursor = get_cursor()
        cursor.callproc("insert_order_item", (food_item, quantity, order_id))
        cnx.commit()
        cursor.close()
        print(f"Order item inserted: {food_item} x {quantity} (order {order_id})")
        return 1
    except mysql.connector.Error as err:
        print(f"Error inserting order item: {err}")
        cnx.rollback()
        return -1
    except Exception as e:
        print(f"An error occurred: {e}")
        cnx.rollback()
        return -1


def insert_order_tracking(order_id: int, status: str):
    cursor = get_cursor()
    query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
    cursor.execute(query, (order_id, status))
    cnx.commit()
    cursor.close()


def get_next_order_id():
    cursor = get_cursor()
    cursor.execute("SELECT MAX(order_id) FROM orders")
    result = cursor.fetchone()[0]
    cursor.close()
    if result is None:
        return 1
    return result + 1


def get_total_order_price(order_id: int):
    cursor = get_cursor()
    cursor.execute("SELECT get_total_order_price(%s)", (order_id,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result


def get_order_status(order_id: int):
    cursor = get_cursor()
    query = "SELECT status FROM order_tracking WHERE order_id = %s"
    cursor.execute(query, (order_id,))
    result = cursor.fetchone()
    cursor.close()
    if result is not None:
        return result[0]
    return None
