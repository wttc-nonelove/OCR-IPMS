from tests.conftest import auth_header


class TestLLMConfig:
    def test_admin_can_read_default_llm_config(self, client, admin_token):
        resp = client.get("/api/v1/system/config/llm", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["enabled"] is False
        assert data["active_profile_id"]
        assert data["profiles"]
        profile = data["profiles"][0]
        assert profile["api_base_url"]
        assert profile["model"]
        assert profile["has_api_key"] is False
        assert "api_key" not in data
        assert "api_key" not in profile

    def test_non_admin_cannot_read_llm_config(self, client, business_token):
        resp = client.get("/api/v1/system/config/llm", headers=auth_header(business_token))
        assert resp.status_code == 403

    def test_save_llm_config_masks_api_key(self, client, admin_token):
        resp = client.put(
            "/api/v1/system/config/llm",
            json={
                "enabled": True,
                "active_profile_id": "model-a",
                "profiles": [
                    {
                        "id": "model-a",
                        "name": "测试模型A",
                        "api_base_url": "https://example.test/v1",
                        "model": "test-model",
                        "api_key": "sk-test-1234567890",
                    }
                ],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["enabled"] is True
        assert data["active_profile_id"] == "model-a"
        profile = data["profiles"][0]
        assert profile["api_base_url"] == "https://example.test/v1"
        assert profile["model"] == "test-model"
        assert profile["has_api_key"] is True
        assert profile["api_key_masked"].startswith("sk-t")
        assert "sk-test-1234567890" not in str(data)

    def test_blank_api_key_keeps_existing_value(self, client, admin_token):
        client.put(
            "/api/v1/system/config/llm",
            json={
                "enabled": True,
                "active_profile_id": "model-a",
                "profiles": [
                    {
                        "id": "model-a",
                        "name": "测试模型A",
                        "api_base_url": "https://example.test/v1",
                        "model": "test-model",
                        "api_key": "sk-test-abcdef",
                    }
                ],
            },
            headers=auth_header(admin_token),
        )
        resp = client.put(
            "/api/v1/system/config/llm",
            json={
                "enabled": False,
                "active_profile_id": "model-a",
                "profiles": [
                    {
                        "id": "model-a",
                        "name": "测试模型A",
                        "api_base_url": "https://example2.test/v1",
                        "model": "test-model-2",
                        "api_key": "",
                    }
                ],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["enabled"] is False
        profile = data["profiles"][0]
        assert profile["api_base_url"] == "https://example2.test/v1"
        assert profile["model"] == "test-model-2"
        assert profile["has_api_key"] is True

    def test_test_llm_config_without_key_returns_failure_payload(self, client, admin_token):
        resp = client.post(
            "/api/v1/system/config/llm/test",
            json={
                "enabled": True,
                "profile": {
                    "id": "model-a",
                    "name": "测试模型A",
                    "api_base_url": "https://example.test/v1",
                    "model": "test-model",
                    "api_key": "",
                },
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["reachable"] is False
        assert "API Key" in data["message"]
