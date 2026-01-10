from flask import Blueprint, request
from sqlalchemy import text
from app.db import db
import time
import random
from datetime import datetime

order_bp = Blueprint('order', __name__)

@order_bp.route('/')
def order_hello():
    """测试 order 蓝图是否生效"""
    return 'order module OK'


# ========== 销售订单视图接口 ==========
@order_bp.route('/select', methods=['GET'])
def order_select():
    try:
        orders = db.session.execute(text("""
            SELECT order_id, order_time, user_id, username, total_amount
            FROM v_sales_records
            ORDER BY order_time DESC
        """)).fetchall()

        result = []
        for o in orders:
            details = db.session.execute(text("""
                SELECT
                    od.isbn,
                    b.title,
                    b.author,
                    b.publisher,
                    od.order_price,
                    od.order_qty
                FROM t_order_detail od
                INNER JOIN t_book b ON od.isbn = b.isbn
                WHERE od.order_id = :oid
            """), {"oid": o.order_id}).fetchall()

            result.append({
                "order_id": o.order_id,
                "order_time": o.order_time.isoformat(),
                "user_id": o.user_id,
                "username": o.username,
                "total_amount": float(o.total_amount),
                "details": [dict(d._mapping) for d in details]
            })

        return {"code": 200, "msg": "Success.", "data": {"list": result}}, 200
    except Exception as e:
        return {"code": 400, "msg": f"Fail.Reason:{e}"}, 201
    

# ========= 登记销售接口 ==========
def generate_order_id():
    """生成唯一订单ID"""
    # 基础部分：年月日时分秒
    base_id = int(datetime.now().strftime("%Y%m%d%H%M%S"))
    
    # 添加随机部分（0-999）
    for _ in range(10):  # 尝试10次
        candidate_id = base_id * 1000 + random.randint(0, 999)
        
        # 检查是否已存在
        exists = db.session.execute(
            text("SELECT COUNT(*) FROM t_order WHERE order_id = :order_id"),
            {"order_id": candidate_id}
        ).scalar()
        
        if not exists:
            return candidate_id
    
    # 如果所有尝试都失败，使用时间戳+进程ID
    return int(time.time() * 1000) * 100 + random.randint(1000, 9999)

@order_bp.route('/insert', methods=['POST'])
def order_insert():
    data = request.get_json()
    user_id = data.get('user_id')
    details = data.get('details', [])
    
    if not user_id or not details:
        return {"code": 400, "msg": "user_id and details are required"}, 400
    
    try:
        # 生成唯一订单ID
        order_id = generate_order_id()
        
        # 创建订单
        db.session.execute(
            text("INSERT INTO t_order (order_id, order_time, user_id) VALUES (:order_id, NOW(), :user_id)"),
            {"order_id": order_id, "user_id": user_id}
        )
        
        
        db.session.commit()
        return {
            "code": 200, 
            "msg": "成功",
            "data": {
                "order_id": order_id,
                "user_id": user_id,
                "total_items": len(details)
            }
        }, 200
        
    except Exception as e:
        db.session.rollback()
        return {"code": 400, "msg": f"Fail.Reason:{str(e)}"}, 400