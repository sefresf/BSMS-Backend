from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Role, Token
from datetime import datetime, timedelta
import hashlib
import secrets

from functools import wraps

auth_bp = Blueprint('auth', __name__)


def token_required(f):
    """验证token有效性的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return {
                "code": 401,
                "msg": "未提供认证令牌",
                "data": {}
            }, 401
        
        user = get_user_by_token(token)
        if not user:
            return {
                "code": 401,
                "msg": "无效或已过期的令牌",
                "data": {}
            }, 401

        return f(*args, **kwargs)
    
    return decorated


def generate_token():
    """生成安全的token"""
    return secrets.token_urlsafe(32)


def md5_hash(password):
    """MD5加密函数"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def get_token_from_header():
    """从请求头中提取token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None

    # 支持两种格式: Bearer <token> 或直接 <token>
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return auth_header


def verify_token(token):
    """验证token有效性"""
    if not token:
        return None

    # 查询token
    token_record = Token.query.filter_by(token=token).first()
    if not token_record:
        return None

    # 检查token是否过期
    if token_record.expire_time < datetime.now():
        # 删除过期token
        db.session.delete(token_record)
        db.session.commit()
        return None

    return token_record


def get_user_by_token(token):
    """通过token获取用户信息"""
    token_record = verify_token(token)
    if not token_record:
        return None

    # 获取用户信息
    user = User.query.filter_by(user_id=token_record.user_id).first()
    return user


# ========== 用户登录接口 ==========

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        # 获取请求数据
        data = request.json

        # 验证必要字段
        if not data or 'username' not in data or 'password' not in data:
            return {
                "code": 400,
                "msg": "用户名和密码不能为空",
                "data": {}
            }, 400

        username = data['username'].strip()
        password = data['password'].strip()

        if not username or not password:
            return {
                "code": 400,
                "msg": "用户名和密码不能为空",
                "data": {}
            }, 400

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if not user:
            return {
                "code": 400,
                "msg": "用户名或密码错误",
                "data": {}
            }, 400

        # 验证密码 (使用MD5加密对比)
        hashed_password = md5_hash(password)
        if user.password != hashed_password:
            return {
                "code": 400,
                "msg": "用户名或密码错误",
                "data": {}
            }, 400

        # 生成token
        token = generate_token()
        expire_time = datetime.now() + timedelta(days=7)  # token有效期7天

        # 创建token记录
        new_token = Token(
            user_id=user.user_id,
            token=token,
            expire_time=expire_time
        )

        # 如果用户已有token，先删除旧的
        existing_tokens = Token.query.filter_by(user_id=user.user_id).all()
        for old_token in existing_tokens:
            db.session.delete(old_token)

        # 保存新的token
        db.session.add(new_token)
        db.session.commit()

        # 获取用户角色信息
        role = Role.query.filter_by(role_id=user.role_id).first()

        return {
            "code": 200,
            "msg": "登录成功",
            "data": {
                "user_id": str(user.user_id),
                "username": user.username,
                "token": token,
                "role_id": user.role_id,
                "role_name": role.role_name if role else ""
            }
        }, 200

    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"登录失败: {str(e)}",
            "data": {}
        }, 400


# ========== 用户登出接口 ==========

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        # 从请求头获取token
        token = get_token_from_header()

        if not token:
            return {
                "code": 401,
                "msg": "未提供认证token",
                "data": {}
            }, 401

        # 查找并删除token
        token_record = Token.query.filter_by(token=token).first()

        if token_record:
            db.session.delete(token_record)
            db.session.commit()

        return {
            "code": 200,
            "msg": "登出成功",
            "data": {}
        }, 200

    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"登出失败: {str(e)}",
            "data": {}
        }, 400


# ========== 用户注册接口 ==========

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """用户注册"""
    try:
        # 获取请求数据
        data = request.json

        # 验证必要字段
        if not data or 'username' not in data or 'password' not in data:
            return {
                "code": 400,
                "msg": "用户名和密码不能为空",
                "data": {}
            }, 400

        username = data['username'].strip()
        password = data['password'].strip()

        if not username or not password:
            return {
                "code": 400,
                "msg": "用户名和密码不能为空",
                "data": {}
            }, 400

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return {
                "code": 400,
                "msg": "用户名已存在",
                "data": {}
            }, 400

        # 密码强度验证
        if len(password) < 6:
            return {
                "code": 400,
                "msg": "密码长度至少6位",
                "data": {}
            }, 400

        # 获取默认角色
        default_role_id = 3

        # 检查角色是否存在
        default_role = Role.query.filter_by(role_id=default_role_id).first()
        if not default_role:
            return {
                "code": 400,
                "msg": "默认角色不存在",
                "data": {}
            }, 400

        # 创建新用户
        hashed_password = md5_hash(password)

        # 查找最大用户ID，生成新ID
        max_user = User.query.order_by(User.user_id.desc()).first()
        new_user_id = max_user.user_id + 1 if max_user else 1

        new_user = User(
            user_id=new_user_id,
            username=username,
            password=hashed_password,
            role_id=default_role_id
        )

        db.session.add(new_user)
        db.session.commit()

        # 生成token
        token = generate_token()
        expire_time = datetime.now() + timedelta(days=7)

        new_token = Token(
            user_id=new_user.user_id,
            token=token,
            expire_time=expire_time
        )

        db.session.add(new_token)
        db.session.commit()

        return {
            "code": 200,
            "msg": "注册成功",
            "data": {
                "user_id": str(new_user.user_id),
                "username": new_user.username,
                "token": token,
                "role_id": new_user.role_id,
                "role_name": default_role.role_name
            }
        }, 200

    except Exception as e:
        db.session.rollback()
        return {
            "code": 400,
            "msg": f"注册失败: {str(e)}",
            "data": {}
        }, 400


# ========== 权限验证接口 ==========

@auth_bp.route('/verification', methods=['POST'])
@token_required
def verification():
    """验证权限/验证token有效性"""
    try:
        return {
            "code": 200,
            "msg": "验证成功",
            "data": {}
        }, 200

    except Exception as e:
        return {
            "code": 400,
            "msg": f"验证失败: {str(e)}",
            "data": {}
        }, 400

