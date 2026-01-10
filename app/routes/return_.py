from flask import Blueprint, request
from sqlalchemy import text
import random, time
from datetime import datetime
from app.db import db

return_bp = Blueprint('return', __name__)

@return_bp.route('/')
def return_hello():
    """测试 return 蓝图是否生效"""
    return 'return module OK'

    
# ========== 退货订单视图接口 ==========
@return_bp.route('/select', methods=['GET'])
def return_select():
    try:
        returns = db.session.execute(text("""
            SELECT return_id, order_id, return_time, reason,
                   user_id, username, total_amount
            FROM v_return_records
            ORDER BY return_time DESC
        """)).fetchall()

        result = []
        for r in returns:
            details = db.session.execute(text("""
                SELECT
                    rd.isbn,
                    b.title,
                    b.author,
                    b.publisher,
                    od.order_price AS refund_price,
                    rd.return_qty
                FROM t_return_detail rd
                INNER JOIN t_book b ON rd.isbn = b.isbn
                INNER JOIN t_order_detail od
                    ON rd.isbn = od.isbn AND od.order_id = :oid
                WHERE rd.return_id = :rid
            """), {"rid": r.return_id, "oid": r.order_id}).fetchall()

            result.append({
                "return_id": r.return_id,
                "order_id": r.order_id,
                "return_time": r.return_time.isoformat(),
                "reason": r.reason,
                "user_id": r.user_id,
                "username": r.username,
                "total_amount": float(r.total_amount),
                "details": [dict(d._mapping) for d in details]
            })

        return {"code": 200, "msg": "Success.", "data": {"list": result}}, 200
    except Exception as e:
        return {"code": 400, "msg": f"Fail.Reason:{e}"}, 201
    
# ========= 登记退货接口 ==========
def generate_return_id():
    """生成唯一退货单ID"""
    base_id = int(datetime.now().strftime("%Y%m%d%H%M%S"))
    for _ in range(10):
        candidate_id = base_id * 1000 + random.randint(0, 999)
        exists = db.session.execute(
            text("SELECT COUNT(*) FROM t_return WHERE return_id = :return_id"),
            {"return_id": candidate_id}
        ).scalar()
        if not exists:
            return candidate_id
    return int(time.time() * 1000) * 100 + random.randint(1000, 9999)

@return_bp.route('/insert', methods=['POST'])
def return_insert():
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id')
    user_id = data.get('user_id')
    reason = data.get('reason', '')
    details = data.get('details', [])

    if not order_id or not user_id or not details:
        return {"code": 400, "msg": "order_id, user_id, and details are required"}, 400

    try:
        for item in details:
            isbn = item.get('isbn')
            return_qty = item.get('return_qty')

            if not isbn or return_qty is None:
                return {"code": 400, "msg": "Each detail must contain isbn and return_qty"}, 400
            try:
                return_qty = int(return_qty)
            except (TypeError, ValueError):
                return {"code": 400, "msg": "return_qty must be an integer"}, 400
            if return_qty <= 0:
                return {"code": 400, "msg": "return_qty must be > 0"}, 400

            # 生成唯一退货单ID
            return_id = generate_return_id()

            # 调用存储过程
            db.session.execute(
                text("CALL proc_return_book(:return_id, :order_id, :isbn, :qty, :reason, :user_id)"),
                {
                    "return_id": return_id,
                    "order_id": order_id,
                    "isbn": isbn,
                    "qty": return_qty,
                    "reason": reason,
                    "user_id": user_id
                }
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
        err_text = str(e)
        #解析存储过程 SIGNAL 错误，返回提示
        if "return quantity exceeds sold quantity" in err_text:
            return {"code": 400, "msg": "退货数量超过已售数量"}, 400
        if "order detail not found" in err_text:
            return {"code": 400, "msg": "订单明细不存在"}, 400
        return {"code": 400, "msg": f"Fail.Reason:{err_text}"}, 400

    
