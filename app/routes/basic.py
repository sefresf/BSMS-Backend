from flask import Blueprint, request
from app.models import Book,Supplier,SupplyInfo
from app.db import db
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

basic_bp = Blueprint('basic', __name__)
@basic_bp.route('/')
def hello_world():
    """测试后端启动"""
    return 'Hello World!'


@basic_bp.route('/test-db', methods=['GET'])
def test_db_connection():
    """测试数据库连接"""
    try:
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()

        return {
            "code": 200,
            "msg": "Database connection successful",
            "status": "connected"
        }, 200

    except Exception as e:
        return {
            "code": 500,
            "msg": f"Database connection failed: {str(e)}",
            "status": "disconnected"
        }, 500


@basic_bp.route('/book/insert', methods=['POST'])
def book_insert():
    try:
        data = request.json
        new_book = Book(
            isbn=data['isbn'],
            title=data['title'],
            author=data.get('author'),
            publisher=data.get('publisher'),
            price=data['price']
        )
        db.session.add(new_book)
        db.session.commit()
        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/book/update', methods=['POST'])
def book_update():
    """修改图书"""
    try:
        data = request.json
        isbn = data['isbn']

        # 查找图书
        book = Book.query.filter_by(isbn=isbn).first()
        if not book:
            return {
                "code": 404,
                "msg": f"Book with ISBN {isbn} not found.",
            }, 201

        # 更新字段
        if 'title' in data:
            book.title = data['title']
        if 'author' in data:
            book.author = data['author']
        if 'publisher' in data:
            book.publisher = data['publisher']
        if 'price' in data:
            book.price = data['price']

        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/book/delete', methods=['POST'])
def book_delete():
    """删除图书"""
    try:
        print('-----')
        data = request.json
        isbn = data['isbn']
        print('-----')
        # 查找图书
        book = Book.query.filter_by(isbn=isbn).first()

        print('-----')
        if not book:
            return {
                "code": 404,
                "msg": f"Book with ISBN {isbn} not found.",
            }, 201

        print('-----')
        db.session.delete(book)
        db.session.commit()

        print('-----')
        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201

# ========== 供应商相关接口 ==========

@basic_bp.route('/supplier/insert', methods=['POST'])
def supplier_insert():
    """添加供应商"""
    try:
        data = request.json
        new_supplier = Supplier(
            supplier_name=data['supplier_name']
        )
        db.session.add(new_supplier)
        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/supplier/update', methods=['POST'])
def supplier_update():
    """修改供应商"""
    try:
        data = request.json
        supplier_id = data['supplier_id']

        # 查找供应商
        supplier = Supplier.query.filter_by(supplier_id=supplier_id).first()
        if not supplier:
            return {
                "code": 404,
                "msg": f"Supplier with ID {supplier_id} not found.",
            }, 201

        # 更新字段
        if 'supplier_name' in data:
            supplier.supplier_name = data['supplier_name']

        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/supplier/delete', methods=['POST'])
def supplier_delete():
    """删除供应商"""
    try:
        data = request.json
        supplier_id = data['supplier_id']

        # 查找供应商
        supplier = Supplier.query.filter_by(supplier_id=supplier_id).first()
        if not supplier:
            return {
                "code": 404,
                "msg": f"Supplier with ID {supplier_id} not found.",
            }, 201

        db.session.delete(supplier)
        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


# ========== 供货报价相关接口 ==========

@basic_bp.route('/supply-info/insert', methods=['POST'])
def supply_info_insert():
    """添加供货报价"""
    try:
        data = request.json
        new_supply_info = SupplyInfo(
            supplier_id=data['supplier_id'],
            isbn=data['isbn'],
            supply_price=data['supply_price']
        )
        db.session.add(new_supply_info)
        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except IntegrityError as e:
        db.session.rollback()
        # 检查是否是唯一约束冲突
        if "Duplicate entry" in str(e):
            return {
                "code": 400,
                "msg": f"Supply relationship already exists for supplier {data['supplier_id']} and ISBN {data['isbn']}.",
            }, 201
        else:
            return {
                "code": 400,
                "msg": f"Fail.Reason:{str(e)}",
            }, 201
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/supply-info/update', methods=['POST'])
def supply_info_update():
    """修改供货报价"""
    try:
        data = request.json
        supplier_id = data['supplier_id']
        isbn = data['isbn']

        # 查找供货报价
        supply_info = SupplyInfo.query.filter_by(
            supplier_id=supplier_id,
            isbn=isbn
        ).first()

        if not supply_info:
            return {
                "code": 404,
                "msg": f"Supply info for supplier {supplier_id} and ISBN {isbn} not found.",
            }, 201

        # 更新供货价格
        if 'supply_price' in data:
            supply_info.supply_price = data['supply_price']

        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/supply-info/delete', methods=['POST'])
def supply_info_delete():
    """删除供货报价"""
    try:
        data = request.json
        supplier_id = data['supplier_id']
        isbn = data['isbn']

        # 查找供货报价
        supply_info = SupplyInfo.query.filter_by(
            supplier_id=supplier_id,
            isbn=isbn
        ).first()

        if not supply_info:
            return {
                "code": 404,
                "msg": f"Supply info for supplier {supplier_id} and ISBN {isbn} not found.",
            }, 201

        db.session.delete(supply_info)
        db.session.commit()

        return {
            "code": 200,
            "msg": "Success.",
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/book/select', methods=['GET'])
def book_select():
    """图书基础信息表 - 支持分页、排序和搜索"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 100, type=int)
        sort_field = request.args.get('sort', 'isbn')
        sort_dir = request.args.get('dir', 'asc')

        # 验证limit范围
        if limit <= 0 or limit > 1000:
            limit = 100

        # 验证排序字段
        valid_sort_fields = ['isbn', 'title', 'author', 'publisher', 'price']
        if sort_field not in valid_sort_fields:
            sort_field = 'isbn'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'asc'

        # 构建基础查询
        query = Book.query

        # 关键词搜索（支持ISBN、书名、作者、出版社）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    Book.isbn.like(keyword_pattern),
                    Book.title.like(keyword_pattern),
                    Book.author.like(keyword_pattern),
                    Book.publisher.like(keyword_pattern)
                )
            )

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(Book, sort_field, Book.isbn)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        books = query.order_by(sort_column).limit(limit).all()

        # 构建返回数据
        book_list = []
        for book in books:
            book_list.append({
                'isbn': book.isbn,
                'title': book.title or '',
                'author': book.author or '',
                'publisher': book.publisher or '',
                'price': float(book.price) if book.price else 0.0
            })

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": book_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201


@basic_bp.route('/supplier/select', methods=['GET'])
def supplier_select():
    """供应商表 - 支持分页、排序和搜索"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 100, type=int)
        sort_field = request.args.get('sort', 'supplier_id')
        sort_dir = request.args.get('dir', 'asc')

        # 验证limit范围
        if limit <= 0 or limit > 1000:
            limit = 100

        # 验证排序字段
        valid_sort_fields = ['supplier_id', 'supplier_name']
        if sort_field not in valid_sort_fields:
            sort_field = 'supplier_id'

        # 验证排序方向
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'asc'

        # 构建基础查询
        query = Supplier.query

        # 关键词搜索（供应商名称）
        if keyword:
            keyword_pattern = f'%{keyword}%'
            query = query.filter(Supplier.supplier_name.like(keyword_pattern))

        # 获取总数
        total_count = query.count()

        # 构建排序
        sort_column = getattr(Supplier, sort_field, Supplier.supplier_id)
        if sort_dir == 'desc':
            sort_column = sort_column.desc()

        # 应用排序和分页
        suppliers = query.order_by(sort_column).limit(limit).all()

        # 构建返回数据
        supplier_list = []
        for supplier in suppliers:
            supplier_list.append({
                'supplier_id': supplier.supplier_id,
                'supplier_name': supplier.supplier_name or ''
            })

        return {
            "code": 200,
            "msg": "Success.",
            "data": {
                "count": total_count,
                "list": supplier_list
            }
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"Fail.Reason:{str(e)}",
        }, 201
    
# ========== 供货信息视图接口 ==========
@basic_bp.route('/supply-info/select', methods=['GET'])
def supply_info_select():
    try:
        rows = db.session.execute(text("""
            SELECT supplier_id, supplier_name, isbn, title, author, publisher, supply_price
            FROM v_supply_info
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
    
