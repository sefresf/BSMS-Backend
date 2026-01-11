import json

from flask import Blueprint, request
from sqlalchemy import text, cast, String
from app.db import db
import time
import random
from datetime import datetime
from app.models import VSalesRecords
from app.routes.auth import token_required

order_bp = Blueprint('order', __name__)


@order_bp.route('/')
def order_hello():
    """测试 order 蓝图是否生效"""
    return 'order module OK'


@order_bp.route('/select', methods=['GET'])
@token_required
def order_select():
    """销售订单视图查询 - 连接销售订单表、销售明细表、图书信息表、系统用户表"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        limit = request.args.get('limit', 100, type=int)
        sort_field = request.args.get('sort', 'order_time')
        sort_dir = request.args.get('dir', 'desc')  # 默认按时间降序

        # 验证limit范围
        if limit <= 0 or limit > 1000:
            limit = 100

        # 验证排序字段
        valid_sort_fields = ['order_id', 'order_time', 'user_id',
                             'username', 'isbn', 'title', 'order_qty',
                             'order_price', 'total_amount']
        if sort_field not in valid_sort_fields:
            sort_field = 'order_time'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'desc'

        # 构建基础查询
        query = VSalesRecords.query

        # 关键词搜索（支持多字段搜索）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    VSalesRecords.username.like(keyword_pattern),
                    VSalesRecords.title.like(keyword_pattern),
                    VSalesRecords.isbn.like(keyword_pattern),
                    cast(VSalesRecords.order_id, String).like(keyword_pattern),
                    cast(VSalesRecords.user_id, String).like(keyword_pattern),
                    cast(VSalesRecords.total_amount, String).like(keyword_pattern)
                )
            )

        # 时间范围过滤
        if start_time:
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VSalesRecords.order_time >= start_dt)
            except ValueError:
                # 尝试其他格式
                try:
                    start_dt = datetime.strptime(start_time, '%Y-%m-%d')
                    query = query.filter(VSalesRecords.order_time >= start_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        if end_time:
            try:
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VSalesRecords.order_time <= end_dt)
            except ValueError:
                try:
                    end_dt = datetime.strptime(end_time, '%Y-%m-%d')
                    # 设置到当天的23:59:59
                    end_dt = datetime.combine(end_dt.date(), datetime.max.time())
                    query = query.filter(VSalesRecords.order_time <= end_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(VSalesRecords, sort_field, VSalesRecords.order_time)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        sales_records = query.order_by(sort_column).limit(limit).all()

        # 按订单ID分组，组装成订单结构
        orders_dict = {}
        for record in sales_records:
            order_id = record.order_id

            if order_id not in orders_dict:
                # 创建订单基础信息
                orders_dict[order_id] = {
                    'order_id': order_id,
                    'order_time': record.order_time.strftime('%Y-%m-%d %H:%M:%S') if record.order_time else None,
                    'user_id': record.user_id,
                    'username': record.username,
                    'total_amount': float(record.total_amount),
                    'details': []
                }

            # 添加订单明细
            orders_dict[order_id]['details'].append({
                'isbn': record.isbn,
                'title': record.title,
                'author': record.author,
                'publisher': record.publisher,
                'order_price': float(record.order_price),
                'order_qty': record.order_qty
            })

        # 转换为列表
        orders_list = list(orders_dict.values())

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": orders_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@order_bp.route('/insert', methods=['POST'])
@token_required
def order_insert():
    """登记销售 - 调用存储过程 proc_order_insert"""
    try:
        data = request.json

        # 获取参数
        user_id = data.get('user_id')
        details = data.get('details', [])

        # 将details转换为JSON字符串
        details_json = json.dumps(details)

        # 调用存储过程
        sql = text("CALL proc_order_insert(:user_id, :details_json)")
        result = db.session.execute(sql, {
            'user_id': user_id,
            'details_json': details_json
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
                    "order_id": proc_result.order_id,
                    "total_amount": float(proc_result.total_amount),
                    "detail_count": proc_result.detail_count
                }
            }, 200
        else:
            return {
                "code": 400,
                "msg": proc_result.result_message if proc_result else "销售失败"
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
