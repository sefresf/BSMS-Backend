from flask import Blueprint, request
from sqlalchemy import text
from datetime import datetime
from app.db import db

statistic_bp = Blueprint('statistic', __name__)

@statistic_bp.route('/')
def statistic_hello():
    """测试 statistic 蓝图是否生效"""
    return 'statistic module OK'



# ========== 图书库存视图接口 ==========
@statistic_bp.route('/stock/select', methods=['GET'])
def stock_select():
    try:
        rows = db.session.execute(text("""
            SELECT isbn, title, author, publisher, price, quantity
            FROM v_book_inventory
            ORDER BY quantity ASC
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

# ========== 库存紧张预警视图接口 ==========
@statistic_bp.route('/stock/shortage', methods=['GET'])
def stock_shortage():
    try:
        rows = db.session.execute(text("""
            SELECT isbn, title, author, publisher, price, quantity, last_month_sales
            FROM v_inventory_shortage_warning
            ORDER BY quantity ASC
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
    

# ========== 日榜接口 ==========
@statistic_bp.route('/sales/rank/daily', methods=['GET'])
def daily_rank():
    from datetime import datetime
    from decimal import Decimal

    date_str = request.args.get('date')
    limit = request.args.get('limit', 10, type=int)
    sort_by = request.args.get('sort_by', 'qty')

    if not date_str:
        return {"code": 400, "msg": "date参数必填"}, 400

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return {"code": 400, "msg": "date参数格式应为YYYY-MM-DD"}, 400

    if sort_by not in ('qty', 'amount'):
        return {"code": 400, "msg": "sort_by参数只能是qty或amount"}, 400

    try:
        rows = db.session.execute(
            text("CALL proc_daily_rank(:p_date)"),
            {"p_date": date_str}
        ).mappings().all()

        if not rows:
            return {
                "code": 200,
                "msg": "成功",
                "data": {"count": 0, "list": []}
            }, 200

        data_list = []

        for row in rows:
            book = db.session.execute(
                text("""
                    SELECT author, publisher, price
                    FROM t_book
                    WHERE isbn = :isbn
                """),
                {"isbn": row['isbn']}
            ).mappings().first()

            total_sales_amount = Decimal('0.00')
            if book and book['price'] is not None:
                total_sales_amount = Decimal(row['total_sold']) * book['price']

            data_list.append({
                "isbn": row['isbn'],
                "title": row['title'],
                "author": book['author'] if book else None,
                "publisher": book['publisher'] if book else None,
                "price": float(book['price']) if book else None,
                "total_sold_qty": row['total_sold'],
                "total_sales_amount": float(total_sales_amount)
            })

        # 排序
        key_map = {
            "qty": lambda x: x['total_sold_qty'],
            "amount": lambda x: x['total_sales_amount']
        }
        data_list.sort(key=key_map[sort_by], reverse=True)

        ranked = []
        for idx, item in enumerate(data_list[:limit], start=1):
            item['rank'] = idx
            ranked.append(item)

        return {
            "code": 200,
            "msg": "成功",
            "data": {
                "count": len(ranked),
                "list": ranked
            }
        }, 200

    except Exception as e:
        return {"code": 400, "msg": f"Fail.Reason:{str(e)}"}, 400

# ========== 月榜接口 ==========
@statistic_bp.route('/sales/rank/monthly', methods=['GET'])
def monthly_rank():
    import re
    from decimal import Decimal

    month_str = request.args.get('month')
    limit = request.args.get('limit', 10, type=int)
    sort_by = request.args.get('sort_by', 'qty')

    if not month_str:
        return {"code": 400, "msg": "month参数必填"}, 400

    if not re.match(r'^\d{4}-\d{2}$', month_str):
        return {"code": 400, "msg": "month参数格式应为YYYY-MM"}, 400

    if sort_by not in ('qty', 'amount'):
        return {"code": 400, "msg": "sort_by参数只能是qty或amount"}, 400

    year, month = map(int, month_str.split('-'))

    try:
        rows = db.session.execute(
            text("CALL proc_monthly_rank(:p_year, :p_month)"),
            {"p_year": year, "p_month": month}
        ).mappings().all()

        if not rows:
            return {
                "code": 200,
                "msg": "成功",
                "data": {"count": 0, "list": []}
            }, 200

        data_list = []

        for row in rows:
            book = db.session.execute(
                text("""
                    SELECT author, publisher, price
                    FROM t_book
                    WHERE isbn = :isbn
                """),
                {"isbn": row['isbn']}
            ).mappings().first()

            total_sales_amount = Decimal('0.00')
            if book and book['price'] is not None:
                total_sales_amount = Decimal(row['total_sold']) * book['price']

            data_list.append({
                "isbn": row['isbn'],
                "title": row['title'],
                "author": book['author'] if book else None,
                "publisher": book['publisher'] if book else None,
                "price": float(book['price']) if book else None,
                "total_sold_qty": row['total_sold'],
                "total_sales_amount": float(total_sales_amount)
            })

        # 排序
        key_map = {
            "qty": lambda x: x['total_sold_qty'],
            "amount": lambda x: x['total_sales_amount']
        }
        data_list.sort(key=key_map[sort_by], reverse=True)

        ranked = []
        for idx, item in enumerate(data_list[:limit], start=1):
            item['rank'] = idx
            ranked.append(item)

        return {
            "code": 200,
            "msg": "成功",
            "data": {
                "count": len(ranked),
                "list": ranked
            }
        }, 200

    except Exception as e:
        return {"code": 400, "msg": f"Fail.Reason:{str(e)}"}, 400
