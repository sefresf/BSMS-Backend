from flask import Blueprint, request
from sqlalchemy import text
from app.db import db

purchase_bp = Blueprint('purchase', __name__)

@purchase_bp.route('/')
def purchase_hello():
    """测试 purchase 蓝图是否生效"""
    return 'Purchase module OK'

   
# ========== 进货记录视图接口 ==========
@purchase_bp.route('/select', methods=['GET'])
def purchase_select():
    try:
        rows = db.session.execute(text("""
            SELECT purchase_id, purchase_time,
                   supplier_id, supplier_name,
                   isbn, title,
                   purchase_qty, purchase_price,
                   user_id, username
            FROM v_purchase_record
            ORDER BY purchase_time DESC
        """)).fetchall()

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": len(rows),
                "list": [dict(row._mapping) for row in rows]
            }
        }, 200
    except Exception as e:
        return {"code": 400, "msg": f"Fail.Reason:{e}"}, 201
    

# ========= 登记进货接口 ==========

@purchase_bp.route('/insert', methods=['POST'])
def purchase_insert():
    """
    登记进货接口
    请求 JSON: { "supplier_id": int, "isbn": str, "purchase_qty": int, "user_id": int }
    返回: {"code":200, "msg":"成功"} 或 错误信息
    """
    try:
        data = request.get_json(silent=True) or {}
        supplier_id = data.get("supplier_id")
        isbn = data.get("isbn")
        purchase_qty = data.get("purchase_qty")
        user_id = data.get("user_id")

        # 参数校验
        if not all([supplier_id, isbn, purchase_qty, user_id]):
            return {"code": 400, "msg": "缺少必填参数: supplier_id, isbn, purchase_qty, user_id"}, 201

        try:
            supplier_id = int(supplier_id)
            purchase_qty = int(purchase_qty)
            user_id = int(user_id)
        except ValueError:
            return {"code": 400, "msg": "supplier_id, purchase_qty, user_id 必须为整数"}, 201

        if purchase_qty <= 0:
            return {"code": 400, "msg": "purchase_qty 必须大于0"}, 201

        # 1. 获取供货价（优先 t_supply_info）
        row = db.session.execute(
            text("SELECT supply_price FROM t_supply_info WHERE supplier_id = :sid AND isbn = :isbn"),
            {"sid": supplier_id, "isbn": isbn}
        ).fetchone()

        if row and row[0] is not None:
            purchase_price = row[0]
        else:
            # 回退到图书定价
            row2 = db.session.execute(
                text("SELECT price FROM t_book WHERE isbn = :isbn"),
                {"isbn": isbn}
            ).fetchone()
            if row2 and row2[0] is not None:
                purchase_price = row2[0]
            else:
                return {"code": 400, "msg": "未找到供货价或图书定价，无法确定进货价格"}, 201

        # 2. 调用存储过程
        db.session.execute(
            text("CALL proc_purchase_book(:supplier_id, :isbn, :qty, :price, :user_id)"),
            {
                "supplier_id": supplier_id,
                "isbn": isbn,
                "qty": purchase_qty,
                "price": purchase_price,
                "user_id": user_id
            }
        )
        db.session.commit()

        #查询最新库存和最近进货记录，用于调试
        stock_row = db.session.execute(
            text("SELECT quantity FROM t_stock WHERE isbn = :isbn"),
            {"isbn": isbn}
        ).fetchone()

        purchase_row = db.session.execute(
            text("""
                SELECT * FROM t_purchase 
                WHERE isbn = :isbn
                ORDER BY purchase_time DESC
                LIMIT 1
            """),
            {"isbn": isbn}
        ).fetchone()

        return {
            "code": 200,
            "msg": "成功",
            "data": {
                "new_stock": stock_row[0] if stock_row else None,
                "latest_purchase": dict(purchase_row._mapping) if purchase_row else None
            }
        }, 200

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"code": 400, "msg": f"Fail.Reason:{e}"}, 201

    