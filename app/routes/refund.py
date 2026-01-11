import json

from flask import Blueprint, request
from sqlalchemy import text, cast, String
import random, time
from datetime import datetime
from app.db import db
from app.models import VReturnRecords
from app.routes.auth import token_required

refund_bp = Blueprint('refund', __name__)


# ========== 退货订单视图接口 ==========
@refund_bp.route('/select', methods=['GET'])
@token_required
def refund_select():
    """退货订单视图查询"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        limit = request.args.get('limit', 100, type=int)
        sort_field = request.args.get('sort', 'return_time')
        sort_dir = request.args.get('dir', 'desc')  # 默认按时间降序

        # 验证limit范围
        if limit <= 0 or limit > 1000:
            limit = 100

        # 验证排序字段
        valid_sort_fields = ['return_id', 'order_id', 'return_time', 'user_id',
                             'username', 'isbn', 'title', 'return_qty',
                             'refund_price', 'total_amount']
        if sort_field not in valid_sort_fields:
            sort_field = 'return_time'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'desc'

        # 构建基础查询
        query = VReturnRecords.query

        # 关键词搜索（支持多字段搜索）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    VReturnRecords.username.like(keyword_pattern),
                    VReturnRecords.title.like(keyword_pattern),
                    VReturnRecords.isbn.like(keyword_pattern),
                    VReturnRecords.reason.like(keyword_pattern),
                    cast(VReturnRecords.return_id, String).like(keyword_pattern),
                    cast(VReturnRecords.order_id, String).like(keyword_pattern),
                    cast(VReturnRecords.user_id, String).like(keyword_pattern),
                    cast(VReturnRecords.total_amount, String).like(keyword_pattern)
                )
            )

        # 时间范围过滤
        if start_time:
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VReturnRecords.return_time >= start_dt)
            except ValueError:
                # 尝试其他格式
                try:
                    start_dt = datetime.strptime(start_time, '%Y-%m-%d')
                    query = query.filter(VReturnRecords.return_time >= start_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        if end_time:
            try:
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                query = query.filter(VReturnRecords.return_time <= end_dt)
            except ValueError:
                try:
                    end_dt = datetime.strptime(end_time, '%Y-%m-%d')
                    # 设置到当天的23:59:59
                    end_dt = datetime.combine(end_dt.date(), datetime.max.time())
                    query = query.filter(VReturnRecords.return_time <= end_dt)
                except ValueError:
                    pass  # 如果格式错误，忽略时间过滤

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(VReturnRecords, sort_field, VReturnRecords.return_time)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        refund_records = query.order_by(sort_column).limit(limit).all()

        # 按退货单ID分组，组装成退货单结构
        refunds_dict = {}
        for record in refund_records:
            return_id = record.return_id

            if return_id not in refunds_dict:
                # 创建退货单基础信息
                refunds_dict[return_id] = {
                    'return_id': return_id,
                    'order_id': record.order_id,
                    'return_time': record.return_time.strftime('%Y-%m-%d %H:%M:%S') if record.return_time else None,
                    'reason': record.reason,
                    'user_id': record.user_id,
                    'username': record.username,
                    'total_amount': float(record.total_amount),
                    'details': []
                }

            # 添加退货单明细
            refunds_dict[return_id]['details'].append({
                'isbn': record.isbn,
                'title': record.title,
                'author': record.author,
                'publisher': record.publisher,
                'refund_price': float(record.refund_price),
                'return_qty': record.return_qty
            })

        # 转换为列表
        refunds_list = list(refunds_dict.values())

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": refunds_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201
    
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


@refund_bp.route('/insert', methods=['POST'])
@token_required
def refund_insert():
    """登记退货 - 调用存储过程 proc_return_insert"""
    try:
        data = request.json

        # 获取参数
        order_id = data.get('order_id')
        user_id = data.get('user_id')
        reason = data.get('reason', '')
        details = data.get('details', [])

        # 将details转换为JSON字符串
        details_json = json.dumps(details)

        # 调用存储过程
        sql = text("CALL proc_return_insert(:order_id, :user_id, :reason, :details_json)")
        result = db.session.execute(sql, {
            'order_id': order_id,
            'user_id': user_id,
            'reason': reason,
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
                    "return_id": proc_result.return_id,
                    "detail_count": proc_result.detail_count
                }
            }, 200
        else:
            return {
                "code": 400,
                "msg": proc_result.result_message if proc_result else "退货失败"
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