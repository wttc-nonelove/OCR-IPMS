"""认证和用户接口测试"""
from tests.conftest import auth_header


class TestLogin:
    """登录接口测试"""

    def test_login_success(self, client):
        resp = client.post("/api/v1/user/login", json={"username": "admin", "password": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "token" in data["data"]
        assert data["data"]["user"]["role"] == "admin"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/user/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/user/login", json={"username": "nobody", "password": "123"})
        assert resp.status_code == 401

    def test_login_all_roles(self, client):
        users = [
            ("admin", "admin"),
            ("business01", "business"),
            ("finance01", "finance"),
            ("pm01", "pm"),
        ]
        for username, expected_role in users:
            resp = client.post("/api/v1/user/login", json={"username": username, "password": "123456"})
            assert resp.status_code == 200
            assert resp.json()["data"]["user"]["role"] == expected_role


class TestUserList:
    """用户列表测试"""

    def test_list_users(self, client, admin_token):
        resp = client.get("/api/v1/user/list", headers=auth_header(admin_token))
        assert resp.status_code == 200
        users = resp.json()["data"]
        assert len(users) >= 4
        usernames = {u["username"] for u in users}
        assert "admin" in usernames


class TestHealthCheck:
    """健康检查测试"""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "ok"
