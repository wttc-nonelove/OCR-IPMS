"""发票和回款接口测试"""
from tests.conftest import auth_header


class TestInvoiceList:
    """发票列表测试"""

    def test_list_empty(self, client, finance_token):
        resp = client.get("/api/v1/invoice/list", headers=auth_header(finance_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_pagination(self, client, finance_token):
        resp = client.get("/api/v1/invoice/list?page=1&page_size=10", headers=auth_header(finance_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total" in data
        assert "items" in data
        assert "page" in data


class TestPaymentList:
    """回款列表测试"""

    def test_list_empty(self, client, finance_token):
        resp = client.get("/api/v1/payment/list", headers=auth_header(finance_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0

    def test_list_pagination(self, client, finance_token):
        resp = client.get("/api/v1/payment/list?page=1&page_size=10", headers=auth_header(finance_token))
        assert resp.status_code == 200
        assert "total" in resp.json()["data"]
