"""测试配置和通用 fixtures"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 测试数据库路径
TEST_DB_PATH = Path(__file__).parent / "test_project_mgmt.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# 设置环境变量（必须在导入 app 之前）
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

from app.db.session import Base, get_db
from app.main import app
from app.services.bootstrap import seed_initial_data

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """创建测试数据库表"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Windows 下可能有文件锁，延迟删除
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(autouse=True)
def clean_tables():
    """每个测试前清空数据并重新填充"""
    db = TestSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        seed_initial_data(db)
    finally:
        db.close()


@pytest.fixture
def db():
    """获取测试数据库会话"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """获取测试客户端"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    """获取管理员 token"""
    resp = client.post("/api/v1/user/login", json={"username": "admin", "password": "123456"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def business_token(client):
    """获取商务 token"""
    resp = client.post("/api/v1/user/login", json={"username": "business01", "password": "123456"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def finance_token(client):
    """获取财务 token"""
    resp = client.post("/api/v1/user/login", json={"username": "finance01", "password": "123456"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def pm_token(client):
    """获取项目经理 token"""
    resp = client.post("/api/v1/user/login", json={"username": "pm01", "password": "123456"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def auth_header(token: str) -> dict:
    """生成认证头"""
    return {"Authorization": f"Bearer {token}"}
