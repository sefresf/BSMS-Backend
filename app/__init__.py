from flask import Flask
import pymysql
from sqlalchemy import text
from app.config import Config
from app.db import db

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    print(uri)
    db.init_app(app)
    # 注册蓝图
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            print("在Flask应用上下文中，数据库连接成功")
        except Exception as e:
            print(f"在Flask应用上下文中，数据库连接失败: {e}")
    register_blueprints(app)


    return app


def register_blueprints(app):
    # 注册蓝图并指定URL前缀
    from app.routes.basic import basic_bp
    from app.routes.purchase import purchase_bp
    from app.routes.order import order_bp
    from app.routes.return_ import return_bp  #return是Python关键字，通常文件名为return_.py
    from app.routes.statistic import statistic_bp

    app.register_blueprint(basic_bp, url_prefix='/basic')
    app.register_blueprint(purchase_bp, url_prefix='/purchase')
    app.register_blueprint(order_bp, url_prefix='/order')
    app.register_blueprint(return_bp, url_prefix='/return')
    app.register_blueprint(statistic_bp, url_prefix='/statistic')