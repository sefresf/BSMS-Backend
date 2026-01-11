# BSMS-Backend

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg)](https://www.sqlalchemy.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-lightblue.svg)](https://www.mysql.com/)

图书销售管理系统后端 (Book Sales Management System-Backend)

## 📋 项目简介

BSMS-Backend 是一个基于 Flask 框架的后端系统，用于管理图书销售、订单、购买和退款等业务流程。系统提供了RESTful API接口，支持跨域访问，采用蓝图(Blueprint)架构组织路由，使用SQLAlchemy进行数据库操作。

## 📁 项目结构

```
BSMS-Backend/
├── 📄 README.md                 # 项目说明文档
├── 📄 requirements.txt          # 项目依赖列表
├── 📄 run.py                    # 应用启动入口
│
└── 📁 app/                      # 主应用目录
    ├── 📄 __init__.py           # Flask应用工厂和蓝图注册
    ├── 📄 config.py             # 应用配置（数据库、调试等）
    ├── 📄 db.py                 # 数据库实例初始化
    ├── 📄 models.py             # 数据模型定义
    │
    └── 📁 routes/               # API路由模块
        ├── 📄 auth.py           # 认证相关接口 (/auth)
        ├── 📄 basic.py          # 基础管理接口 (/basic)
        ├── 📄 purchase.py       # 采购管理接口 (/purchase)
        ├── 📄 order.py          # 订单管理接口 (/order)
        ├── 📄 refund.py         # 退款管理接口 (/refund)
        └── 📄 statistic.py      # 统计分析接口 (/statistic)
```

## 🔧 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.13 | 编程语言 |
| Flask | 3.1.2 | Web框架 |
| Flask-CORS | 6.0.1 | 跨域资源共享 |
| SQLAlchemy | 2.0 | ORM框架 |
| Flask-SQLAlchemy | 3.1.1 | Flask SQL工具包 |
| PyMySQL | 1.1.1 | MySQL数据库驱动 |
| python-dotenv | 1.1.0 | 环境变量管理 |

## 📦 主要功能模块

### 🔐 认证模块 (`routes/auth.py`)
- 用户登录/登出
- 用户注册/身份验证
- 权限管理

### 📚 基础管理模块 (`routes/basic.py`)
- 图书信息管理
- 库存管理
- 分类管理

### 🛒 采购管理模块 (`routes/purchase.py`)
- 采购单创建
- 采购单管理
- 供应商管理

### 📦 订单管理模块 (`routes/order.py`)
- 订单创建
- 订单查询
- 订单处理流程

### 💰 退款管理模块 (`routes/refund.py`)
- 退款申请
- 退款审核
- 退款处理

### 📊 统计分析模块 (`routes/statistic.py`)
- 销售统计
- 收入分析
- 报表生成

## 🚀 快速开始

### 前置要求
- Python 3.13+
- MySQL 8.0+
- pip 包管理工具

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd BSMS-Backend
```

2. **创建虚拟环境（推荐）**
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# 或
source venv/bin/activate      # Linux/Mac
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
创建 `.env` 文件并配置数据库连接：
```
FLASK_ENV=development
FLASK_APP=run.py
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:password@localhost:3306/bsms
```

5. **初始化数据库**
```bash
flask shell
>>> from app.db import db
>>> db.create_all()
>>> exit()
```

6. **运行应用**
```bash
python run.py
```

应用将在 `http://localhost:5000` 启动

## 📡 API 端点

| 模块 | 前缀 | 说明 |
|------|------|------|
| 认证 | `/auth` | 身份验证相关接口 |
| 基础 | `/basic` | 图书库存管理接口 |
| 采购 | `/purchase` | 采购单管理接口 |
| 订单 | `/order` | 订单管理接口 |
| 退款 | `/refund` | 退款管理接口 |
| 统计 | `/statistic` | 统计分析接口 |

## 🔄 跨域配置

系统已配置 CORS 支持，当前允许来自 `http://localhost:8848` 的请求。

修改允许的源：在 `app/__init__.py` 中更新 `CORS` 配置：
```python
CORS(app, origins=["http://your-frontend-url"], supports_credentials=True)
```

## 📝 项目架构说明

### 应用工厂模式
使用工厂模式创建 Flask 应用实例，便于测试和多环境配置：
```python
app = create_app()
```

### 蓝图（Blueprint）架构
各功能模块独立为蓝图，在 `register_blueprints()` 中统一注册：
- 提高代码组织性
- 便于功能扩展
- 支持模块级前缀

### 数据库连接
使用 SQLAlchemy 作为 ORM 框架，支持：
- 模型定义
- 数据库迁移
- 事务管理

## 🛠️ 开发指南

### 添加新的 API 端点

1. 在 `app/routes/` 目录创建新文件，例如 `newmodule.py`
2. 定义蓝图和路由
3. 在 `app/__init__.py` 的 `register_blueprints()` 中注册

### 添加数据模型

在 `app/models.py` 中定义 SQLAlchemy 模型：
```python
class YourModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 更多字段...
```

## 📧 联系方式

如有问题或建议，请提出 Issue 或 Pull Request

## 📄 许可证

MIT License

---

**最后更新**：2026-01-11
