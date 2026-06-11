from app.services import ocr
from app.services.ocr import _complete_contract_info, _extract_contract
from app.services.system_config import LLMRuntimeConfig


def test_weak_label_contract_extracts_total_amount_and_empty_contract_no():
    text = """
项目编号：ZYZB-2024-Z-010-
2024年度xx财政预算管理一体化系统
运行维护项目（二次）合同

甲方：新疆杜云飞
乙方：栗姜涛
丙方：刘沐沛

签订日期：2026 年 6 月 10 日

五、合同金额及付款方式
本合同总金额：人民币小写：1000000.00元。
第一期支付合同金额的30%，即人民币小写：300000.00元。
第二期支付合同金额的20%，即人民币小写：200000.00元。
"""
    info = _extract_contract(text)

    assert info["contract_amount"] == "1000000.00"
    assert info["contract_no"] == "ZYZB-2024-Z-010-"
    assert info["sign_date"] == "2026-06-10"
    assert info["party_a"] == "新疆杜云飞"
    assert info["party_b"] == "栗姜涛"
    assert info["party_c"] == "刘沐沛"


def test_llm_does_not_override_explicit_contract_total_amount(monkeypatch):
    text = "甲方：新疆杜云飞\n乙方：栗姜涛\n本合同总金额：人民币小写：1000000.00元。\n第一期：300000.00元。"
    info = _extract_contract(text)

    monkeypatch.setattr(
        ocr,
        "get_llm_runtime_config",
        lambda _db: LLMRuntimeConfig(
            enabled=True,
            api_key="sk-test",
            api_base_url="https://example.test/v1",
            model="test-model",
            source="test",
            profile_id="test",
            profile_name="测试模型",
        ),
    )
    monkeypatch.setattr(
        ocr,
        "_call_llm_contract_extract",
        lambda _text, _config: {"contract_amount": "300000.00", "party_a": "错误甲方", "party_b": "错误乙方"},
    )

    merged, llm_used, field_sources, manual_required, llm_error = _complete_contract_info(None, text, info)

    assert llm_used is True
    assert llm_error == ""
    assert manual_required == ["项目名称"]
    assert merged["contract_amount"] == "1000000.00"
    assert merged["party_a"] == "新疆杜云飞"
    assert merged["party_b"] == "栗姜涛"
    assert field_sources["contract_amount"] == "rule"
