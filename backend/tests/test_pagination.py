"""分页功能测试"""
from tests.conftest import auth_header


class TestPagination:
    """分页响应格式测试"""

    def _create_projects(self, client, token, count):
        for i in range(count):
            client.post(
                "/api/v1/project/draft/save",
                data={"name": f"分页测试{i:03d}", "party_a": "甲方", "amount": str(10000 + i)},
                headers=auth_header(token),
            )

    def test_default_pagination(self, client, admin_token):
        self._create_projects(client, admin_token, 25)
        resp = client.get("/api/v1/project/list", headers=auth_header(admin_token))
        data = resp.json()["data"]
        assert data["total"] == 25
        assert len(data["items"]) == 20  # 默认 page_size=20
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 2

    def test_custom_page_size(self, client, admin_token):
        self._create_projects(client, admin_token, 10)
        resp = client.get("/api/v1/project/list?page_size=5", headers=auth_header(admin_token))
        data = resp.json()["data"]
        assert len(data["items"]) == 5
        assert data["total_pages"] == 2

    def test_second_page(self, client, admin_token):
        self._create_projects(client, admin_token, 10)
        resp = client.get("/api/v1/project/list?page=2&page_size=3", headers=auth_header(admin_token))
        data = resp.json()["data"]
        assert len(data["items"]) == 3
        assert data["page"] == 2

    def test_page_beyond_total(self, client, admin_token):
        self._create_projects(client, admin_token, 5)
        resp = client.get("/api/v1/project/list?page=100", headers=auth_header(admin_token))
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 5
