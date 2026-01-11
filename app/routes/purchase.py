from flask import Blueprint, request
from app.models import VPurchaseRecord
from app.routes.auth import token_required
from app.db import db
from sqlalchemy import text, cast, String
from datetime import datetime
import time

purchase_bp = Blueprint('purchase', __name__)

@purchase_bp.route('/')
def purchase_hello():
    """测试 purchase 蓝图是否生效"""
    return 'Purchase module OK'

   
# ========== 进货记录视图接口 ==========
@purchase_bp.route('/select', methods=['GET'])
@token_required
def purchase_select():
    """进货记录视图查询"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        limit = request.args.get('limit', 100, type=int)
        sort_field = request.args.get('sort', 'purchase_time')
        sort_dir = request.args.get('dir', 'desc')  # 默认按时间降序

        # 验证limit范围
        if limit <= 0 or limit > 1000:
            limit = 100

        # 验证排序字段
        valid_sort_fields = ['purchase_id', 'purchase_time', 'supplier_id',
                             'supplier_name', 'isbn', 'title', 'purchase_qty',
                             'purchase_price', 'user_id', 'username']
        if sort_field not in valid_sort_fields:
            sort_field = 'purchase_time'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'desc'

        query = VPurchaseRecord.query

        # 关键词搜索（支持多字段搜索）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    VPurchaseRecord.supplier_name.like(keyword_pattern),
                    VPurchaseRecord.title.like(keyword_pattern),
                    VPurchaseRecord.isbn.like(keyword_pattern),
                    cast(VPurchaseRecord.purchase_id, String).like(keyword_pattern),
                    cast(VPurchaseRecord.user_id, String).like(keyword_pattern),
                    VPurchaseRecord.username.like(keyword_pattern)
                )
            )

        # 时间范围过滤
        if start_time:
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VPurchaseRecord.purchase_time >= start_dt)
            except ValueError:
                # 尝试其他格式
                try:
                    start_dt = datetime.strptime(start_time, '%Y-%m-%d')
                    query = query.filter(VPurchaseRecord.purchase_time >= start_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        if end_time:
            try:
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VPurchaseRecord.purchase_time <= end_dt)
            except ValueError:
                try:
                    end_dt = datetime.strptime(end_time, '%Y-%m-%d')
                    # 设置到当天的23:59:59
                    end_dt = datetime.combine(end_dt.date(), datetime.max.time())
                    query = query.filter(VPurchaseRecord.purchase_time <= end_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(VPurchaseRecord, sort_field, VPurchaseRecord.purchase_time)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        purchase_records = query.order_by(sort_column).limit(limit).all()

        # 构建返回数据
        purchase_list = []
        for record in purchase_records:
            purchase_list.append(record.to_dict())

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": purchase_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201
    

# ========= 登记进货接口 ==========
@purchase_bp.route('/insert', methods=['POST'])
@token_required
def purchase_insert():
    """登记进货"""
    try:
        data = request.json

        # 获取参数
        supplier_id = data.get('supplier_id')
        isbn = data.get('isbn')
        purchase_qty = data.get('purchase_qty')
        user_id = data.get('user_id')

        # 调用存储过程
        sql = text("CALL proc_purchase_insert(:supplier_id, :isbn, :purchase_qty, :user_id)")
        result = db.session.execute(sql, {
            'supplier_id': supplier_id,
            'isbn': isbn,
            'purchase_qty': purchase_qty,
            'user_id': user_id
        })

        # 获取存储过程返回的结果
        proc_result = result.fetchone()
        db.session.commit()

        # 构建返回信息
        if proc_result and proc_result.result_code == 0:
            return {
                "code": 200,
                "msg": proc_result.result_message,
                "data": {
                    "purchase_id": proc_result.purchase_id,
                    "purchase_price": float(proc_result.purchase_price),
                    "total_amount": float(proc_result.total_amount),
                    "purchase_qty": proc_result.purchase_qty
                }
            }, 200
        else:
            return {
                "code": 400,
                "msg": proc_result.result_message if proc_result else "进货失败"
            }, 201

    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        # 提取MySQL错误信息中的有用部分
        if "MySQL" in error_msg:
            # 尝试提取MySQL错误消息
            import re
            match = re.search(r"'(\d{5})'\):\s*(.*)", error_msg)
            if match:
                error_msg = match.group(2)
        return {
            "code": 400,
            "msg": f"Fail.Reason:{error_msg}",
        }, 201