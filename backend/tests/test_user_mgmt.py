"""用户管理接口测试"""
from tests.conftest import auth_header


class TestUserCreate:
    """新增用户测试"""

    def test_create_user(self, client, admin_token):
        resp = client.post("/api/v1/user/create", json={
            "username": "newuser", "password": "123456", "name": "新用户",
            "phone": "13900000000", "role": "business", "dept": "市场部",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == "newuser"
        assert data["role"] == "business"
        assert data["status"] == 1

    def test_create_duplicate_username(self, client, admin_token):
        client.post("/api/v1/user/create", json={
            "username": "dup_user", "password": "123456", "name": "A",
            "phone": "13900000001", "role": "finance",
        }, headers=auth_header(admin_token))
        resp = client.post("/api/v1/user/create", json={
            "username": "dup_user", "password": "123456", "name": "B",
            "phone": "13900000002", "role": "finance",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_create_invalid_role(self, client, admin_token):
        resp = client.post("/api/v1/user/create", json={
            "username": "badrole", "password": "123456", "name": "C",
            "phone": "13900000003", "role": "superadmin",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_create_requires_admin(self, client, business_token):
        resp = client.post("/api/v1/user/create", json={
            "username": "nope", "password": "123456", "name": "D",
            "phone": "13900000004", "role": "business",
        }, headers=auth_header(business_token))
        assert resp.status_code == 403


class TestUserUpdate:
    """编辑用户测试"""

    def test_update_user(self, client, admin_token):
        # 先创建
        resp = client.post("/api/v1/user/create", json={
            "username": "to_update", "password": "123456", "name": "待编辑",
            "phone": "13900000010", "role": "pm",
        }, headers=auth_header(admin_token))
        uid = resp.json()["data"]["id"]
        # 更新
        resp = client.put("/api/v1/user/update", json={
            "user_id": uid, "name": "已编辑", "dept": "项目部",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "已编辑"
        assert resp.json()["data"]["dept"] == "项目部"

    def test_update_nonexistent(self, client, admin_token):
        resp = client.put("/api/v1/user/update", json={
            "user_id": 99999, "name": "不存在",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 404


class TestUserStatus:
    """启禁用测试"""

    def test_toggle_status(self, client, admin_token):
        resp = client.post("/api/v1/user/create", json={
            "username": "to_toggle", "password": "123456", "name": "待禁用",
            "phone": "13900000020", "role": "finance",
        }, headers=auth_header(admin_token))
        uid = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == 1
        # 禁用
        resp = client.put(f"/api/v1/user/{uid}/status", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == 0
        # 再启用
        resp = client.put(f"/api/v1/user/{uid}/status", headers=auth_header(admin_token))
        assert resp.json()["data"]["status"] == 1

    def test_cannot_disable_self(self, client, admin_token):
        # 获取 admin 用户 id
        resp = client.get("/api/v1/user/list", headers=auth_header(admin_token))
        admin_id = next(u["id"] for u in resp.json()["data"] if u["username"] == "admin")
        resp = client.put(f"/api/v1/user/{admin_id}/status", headers=auth_header(admin_token))
        assert resp.status_code == 400


class TestUserDelete:
    """删除用户测试"""

    def test_delete_user(self, client, admin_token):
        resp = client.post("/api/v1/user/create", json={
            "username": "to_delete", "password": "123456", "name": "待删除",
            "phone": "13900000030", "role": "business",
        }, headers=auth_header(admin_token))
        uid = resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/user/{uid}", headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_cannot_delete_self(self, client, admin_token):
        resp = client.get("/api/v1/user/list", headers=auth_header(admin_token))
        admin_id = next(u["id"] for u in resp.json()["data"] if u["username"] == "admin")
        resp = client.delete(f"/api/v1/user/{admin_id}", headers=auth_header(admin_token))
        assert resp.status_code == 400


class TestUserListFields:
    """用户列表字段完整性"""

    def test_list_returns_all_fields(self, client, admin_token):
        resp = client.get("/api/v1/user/list", headers=auth_header(admin_token))
        assert resp.status_code == 200
        user = resp.json()["data"][0]
        assert "phone" in user
        assert "email" in user
        assert "dept" in user
        assert "status" in user
