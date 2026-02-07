import pytest
from copy import deepcopy

from src.managers.ResumeVariantManager import ResumeVariantManager


class FakeConfigManager:
    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return deepcopy(self._store.get(key, default))

    def set(self, key, value):
        self._store[key] = deepcopy(value)


def _ctx(tag="base"):
    return {"name": tag, "projects": [{"name": "P", "bullets": ["x"]}]}


def test_ensure_base_snapshot_creates_report_record():
    cfg = FakeConfigManager()
    mgr = ResumeVariantManager(cfg)

    mgr.ensure_base_snapshot(report_id=123, title="Report A", base_context=_ctx("base1"))

    data = cfg.get("resume_variants", [])
    assert len(data) == 1
    assert data[0]["report_id"] == 123
    assert data[0]["title"] == "Report A"
    assert data[0]["base_context"]["name"] == "base1"
    assert data[0]["variants"] == []


def test_ensure_base_snapshot_does_not_overwrite_existing_base():
    cfg = FakeConfigManager()
    mgr = ResumeVariantManager(cfg)

    mgr.ensure_base_snapshot(123, "Report A", _ctx("base1"))
    mgr.ensure_base_snapshot(123, "Report A NEW", _ctx("base2"))  # should not overwrite base

    data = cfg.get("resume_variants", [])
    assert len(data) == 1
    assert data[0]["report_id"] == 123
    # title/base should remain original (depending on your intended behavior)
    assert data[0]["title"] in {"Report A", "Report A NEW"}
    assert data[0]["base_context"]["name"] == "base1"


def test_create_variant_assigns_incrementing_ids():
    cfg = FakeConfigManager()
    mgr = ResumeVariantManager(cfg)

    mgr.ensure_base_snapshot(1, "R", _ctx("base"))
    v1 = mgr.create_variant(1, label="updated", context=_ctx("v1"))
    v2 = mgr.create_variant(1, label="v2", context=_ctx("v2"))

    assert v1["variant_id"] == 1
    assert v2["variant_id"] == 2

    variants = mgr.list_variants(1)
    assert [v["variant_id"] for v in variants] == [1, 2]


def test_list_variants_empty_if_report_missing():
    cfg = FakeConfigManager()
    mgr = ResumeVariantManager(cfg)

    assert mgr.list_variants(999) == []


def test_get_variant_returns_correct_context():
    cfg = FakeConfigManager()
    mgr = ResumeVariantManager(cfg)

    mgr.ensure_base_snapshot(10, "R10", _ctx("base10"))
    mgr.create_variant(10, label="updated", context=_ctx("hello"))
    mgr.create_variant(10, label="other", context=_ctx("world"))

    v = mgr.get_variant(10, 2)
    assert v is not None
    assert v["variant_id"] == 2
    assert v["label"] == "other"
    assert v["context"]["name"] == "world"

    assert mgr.get_variant(10, 999) is None
