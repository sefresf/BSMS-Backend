from flask import Blueprint, request
from sqlalchemy import text
from datetime import datetime
from app.db import db
from app.models import VInventoryShortageWarning, VBookInventory
from app.routes.auth import token_required

statistic_bp = Blueprint('statistic', __name__)


@statistic_bp.route('/')
def statistic_hello():
    """测试 statistic 蓝图是否生效"""
    return 'statistic module OK'


@statistic_bp.route('/stock/select', methods=['GET'])
@token_required
def stock_select():
    """图书库存视图查询 - 连接图书基础信息表、库存表"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 50, type=int)
        sort_field = request.args.get('sort', 'quantity')
        sort_dir = request.args.get('dir', 'asc')

        # 验证limit范围
        if limit <= 0 or limit > 500:
            limit = 50

        # 验证排序字段
        valid_sort_fields = ['isbn', 'title', 'author', 'publisher', 'price', 'quantity']
        if sort_field not in valid_sort_fields:
            sort_field = 'quantity'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'asc'

        # 构建基础查询
        query = VBookInventory.query

        # 关键词搜索（支持图书名称和ISBN搜索）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    VBookInventory.title.like(keyword_pattern),
                    VBookInventory.isbn.like(keyword_pattern),
                    VBookInventory.author.like(keyword_pattern),
                    VBookInventory.publisher.like(keyword_pattern)
                )
            )

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(VBookInventory, sort_field, VBookInventory.quantity)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        inventory_records = query.order_by(sort_column).limit(limit).all()

        # 构建返回数据
        inventory_list = []
        for record in inventory_records:
            inventory_list.append({
                'isbn': record.isbn,
                'title': record.title,
                'author': record.author,
                'publisher': record.publisher,
                'price': float(record.price),
                'quantity': record.quantity
            })

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": inventory_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@statistic_bp.route('/stock/shortage', methods=['GET'])
@token_required
def stock_shortage():
    """库存紧张预警视图 - 获取急需补货的图书列表"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 20, type=int)

        # 验证limit范围
        if limit <= 0 or limit > 100:
            limit = 20

        # 构建基础查询
        query = VInventoryShortageWarning.query

        # 关键词搜索
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    VInventoryShortageWarning.title.like(keyword_pattern),
                    VInventoryShortageWarning.isbn.like(keyword_pattern),
                    VInventoryShortageWarning.author.like(keyword_pattern),
                    VInventoryShortageWarning.publisher.like(keyword_pattern)
                )
            )

        # 获取总数
        total_count = query.count()

        # 应用分页（默认按库存数量升序）
        shortage_records = query.order_by(
            VInventoryShortageWarning.quantity.asc()
        ).limit(limit).all()

        # 构建返回数据
        shortage_list = []
        for record in shortage_records:
            shortage_list.append({
                'isbn': record.isbn,
                'title': record.title,
                'author': record.author,
                'publisher': record.publisher,
                'price': float(record.price),
                'quantity': record.quantity,
                'last_month_sales': record.last_month_sales
            })

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": shortage_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@statistic_bp.route('/sales/rank/daily', methods=['GET'])
@token_required
def daily_sales_rank():
    """图书销售日榜"""
    try:
        # 获取查询参数
        date_str = request.args.get('date', '')
        sort_by = request.args.get('sort_by', 'qty')
        limit = request.args.get('limit', 10, type=int)

        # 参数验证
        if not date_str:
            return {
                "code": 400,
                "msg": "查询日期不能为空",
                "data": {}
            }, 201

        # 验证日期格式 (YYYY-MM-DD)
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {
                "code": 400,
                "msg": "日期格式错误，应为 YYYY-MM-DD",
                "data": {}
            }, 201

        # 验证排序参数
        if sort_by not in ['qty', 'amount']:
            sort_by = 'qty'

        # 验证限制数量
        if limit <= 0 or limit > 100:
            limit = 10

        # 调用存储过程
        sql = text("CALL proc_daily_rank(:p_date, :p_sort_by, :p_limit)")
        result = db.session.execute(sql, {
            'p_date': date_str,
            'p_sort_by': sort_by,
            'p_limit': limit
        })

        # 获取存储过程返回的结果集
        rows = result.fetchall()

        # 构建返回数据
        rank_list = []
        for i, row in enumerate(rows, 1):
            rank_list.append({
                'rank': i,
                'isbn': row.isbn,
                'title': row.title,
                'author': row.author or '',
                'publisher': row.publisher or '',
                'price': float(row.price),
                'total_sold_qty': row.total_sold_qty,
                'total_sales_amount': float(row.total_sales_amount)
            })

        return {
            "code": 200,
            "msg": "Success",
            "data": {
                "count": len(rank_list),
                "list": rank_list,
            }
        }, 200

    except Exception as e:
        error_msg = str(e)
        # 提取MySQL错误信息中的有用部分
        if "MySQL" in error_msg:
            import re
            match = re.search(r"'(\d{5})'\):\s*(.*)", error_msg)
            if match:
                error_msg = match.group(2)

        return {
            "code": 400,
            "msg": f"Fail.Reason: {error_msg}",
            "data": {}
        }, 201


@statistic_bp.route('/sales/rank/monthly', methods=['GET'])
@token_required
def monthly_sales_rank():
    """图书销售月榜"""
    try:
        # 获取查询参数
        month_str = request.args.get('month', '')
        sort_by = request.args.get('sort_by', 'qty')
        limit = request.args.get('limit', 10, type=int)

        # 参数验证
        if not month_str:
            return {
                "code": 400,
                "msg": "查询月份不能为空",
                "data": {}
            }, 201

        # 验证月份格式 (YYYY-MM)
        import re
        if not re.match(r'^\d{4}-\d{2}$', month_str):
            return {
                "code": 400,
                "msg": "月份格式错误，应为 YYYY-MM",
                "data": {}
            }, 201

        # 验证月份有效性
        try:
            year, month = map(int, month_str.split('-'))
            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            return {
                "code": 400,
                "msg": "月份无效，应为 01-12",
                "data": {}
            }, 201

        # 验证排序参数
        if sort_by not in ['qty', 'amount']:
            sort_by = 'qty'

        # 验证限制数量
        if limit <= 0 or limit > 100:
            limit = 10

        # 调用存储过程
        sql = text("CALL proc_monthly_rank(:p_date, :p_sort_by, :p_limit)")
        result = db.session.execute(sql, {
            'p_date': month_str,
            'p_sort_by': sort_by,
            'p_limit': limit
        })

        # 获取存储过程返回的结果集
        rows = result.fetchall()

        # 构建返回数据
        rank_list = []
        for i, row in enumerate(rows, 1):
            rank_list.append({
                'rank': i,
                'isbn': row.isbn,
                'title': row.title,
                'author': row.author or '',
                'publisher': row.publisher or '',
                'price': float(row.price),
                'total_sold_qty': row.total_sold_qty,
                'total_sales_amount': float(row.total_sales_amount)
            })

        return {
            "code": 200,
            "msg": "Success",
            "data": {
                "count": len(rank_list),
                "list": rank_list
            }
        }, 200

    except Exception as e:
        error_msg = str(e)
        # 提取MySQL错误信息中的有用部分
        if "MySQL" in error_msg:
            import re
            match = re.search(r"'(\d{5})'\):\s*(.*)", error_msg)
            if match:
                error_msg = match.group(2)

        return {
            "code": 400,
            "msg": f"Fail.Reason: {error_msg}",
            "data": {}
        }, 201