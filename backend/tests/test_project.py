"""项目管理接口测试"""
from tests.conftest import auth_header


class TestProjectList:
    """项目列表测试"""

    def test_list_empty(self, client, admin_token):
        resp = client.get("/api/v1/project/list", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_with_pagination(self, client, admin_token):
        for i in range(5):
            client.post(
                "/api/v1/project/draft/save",
                data={"name": f"项目{i}", "party_a": "甲方", "amount": "10000"},
                headers=auth_header(admin_token),
            )
        resp = client.get("/api/v1/project/list?page=1&page_size=2", headers=auth_header(admin_token))
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    def test_list_filter_by_status(self, client, admin_token):
        client.post(
            "/api/v1/project/draft/save",
            data={"name": "草稿项目", "party_a": "甲方", "amount": "10000"},
            headers=auth_header(admin_token),
        )
        resp = client.get("/api/v1/project/list?status=draft", headers=auth_header(admin_token))
        assert resp.json()["data"]["total"] == 1

    def test_list_filter_by_keyword(self, client, admin_token):
        client.post(
            "/api/v1/project/draft/save",
            data={"name": "测试项目ABC", "party_a": "甲方", "amount": "10000"},
            headers=auth_header(admin_token),
        )
        resp = client.get("/api/v1/project/list?keyword=ABC", headers=auth_header(admin_token))
        assert resp.json()["data"]["total"] == 1


class TestProjectDraft:
    """项目草稿测试"""

    def test_save_draft(self, client, admin_token):
        resp = client.post(
            "/api/v1/project/draft/save",
            data={"name": "新项目", "party_a": "测试甲方", "amount": "50000"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        project = resp.json()["data"]["project"]
        assert project["name"] == "新项目"
        assert project["status"] == "draft"

    def test_save_draft_generates_project_no(self, client, admin_token):
        resp = client.post(
            "/api/v1/project/draft/save",
            data={"name": "有编号项目", "party_a": "甲方", "amount": "10000"},
            headers=auth_header(admin_token),
        )
        project = resp.json()["data"]["project"]
        assert project["project_no"].startswith("PRJ-")

    def test_next_project_no(self, client, admin_token):
        resp = client.get("/api/v1/project/next-no", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert "project_no" in resp.json()["data"]


class TestProjectLifecycle:
    """项目生命周期测试"""

    def _create_draft(self, client, token):
        resp = client.post(
            "/api/v1/project/draft/save",
            data={"name": "生命周期测试", "party_a": "甲方", "party_b": "乙方", "amount": "100000"},
            headers=auth_header(token),
        )
        return resp.json()["data"]["project"]

    def test_submit_requires_fields(self, client, admin_token):
        resp = client.post(
            "/api/v1/project/draft/save",
            data={"name": "", "party_a": "", "amount": "0"},
            headers=auth_header(admin_token),
        )
        project = resp.json()["data"]["project"]
        resp = client.post(f"/api/v1/project/submit?project_id={project['id']}", headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_full_lifecycle(self, client, admin_token):
        # 创建草稿
        project = self._create_draft(client, admin_token)
        assert project["status"] == "draft"

        # 提交审核
        resp = client.post(f"/api/v1/project/submit?project_id={project['id']}", headers=auth_header(admin_token))
        assert resp.status_code == 200

        # 验证状态变为 pending
        resp = client.get(f"/api/v1/project/detail?project_id={project['id']}", headers=auth_header(admin_token))
        assert resp.json()["data"]["project"]["status"] == "pending"

        # 审批通过
        resp = client.post(
            "/api/v1/project/approve",
            json={"project_id": project["id"], "result": "approved", "opinion": "同意"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200

        # 确认开始
        resp = client.post(
            "/api/v1/project/start",
            json={"project_id": project["id"]},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200

        # 验证状态变为 active
        resp = client.get(f"/api/v1/project/detail?project_id={project['id']}", headers=auth_header(admin_token))
        assert resp.json()["data"]["project"]["status"] == "active"

    def test_approve_rejected(self, client, admin_token):
        project = self._create_draft(client, admin_token)
        client.post(f"/api/v1/project/submit?project_id={project['id']}", headers=auth_header(admin_token))
        resp = client.post(
            "/api/v1/project/approve",
            json={"project_id": project["id"], "result": "rejected", "reason": "信息不全"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        resp = client.get(f"/api/v1/project/detail?project_id={project['id']}", headers=auth_header(admin_token))
        assert resp.json()["data"]["project"]["status"] == "draft"


class TestProjectDelete:
    """项目删除测试"""

    def test_delete_draft(self, client, admin_token):
        resp = client.post(
            "/api/v1/project/draft/save",
            data={"name": "待删除", "party_a": "甲方", "amount": "10000"},
            headers=auth_header(admin_token),
        )
        project_id = resp.json()["data"]["project"]["id"]
        resp = client.delete(f"/api/v1/project/{project_id}", headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_delete_nonexistent(self, client, admin_token):
        resp = client.delete("/api/v1/project/99999", headers=auth_header(admin_token))
        assert resp.status_code == 404


class TestProjectOptions:
    """项目选项测试"""

    def test_options_empty(self, client, admin_token):
        resp = client.get("/api/v1/project/options", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_options_with_usage(self, client, admin_token):
        resp = client.get("/api/v1/project/options?usage=invoice", headers=auth_header(admin_token))
        assert resp.status_code == 200
