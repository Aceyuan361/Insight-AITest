# -*- coding: utf-8 -*-
"""EnvironmentDatabase CRUD + 单默认约束测试。"""
from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase


def _db(tmp_path):
    return EnvironmentDatabase(str(tmp_path / "api.db"))


def test_crud(tmp_path):
    db = _db(tmp_path)
    eid = db.create(name="dev", base_url="https://dev.example.com",
                    variables={"token": "dev-tkn"}, is_default=True)
    env = db.get(eid)
    assert env.name == "dev"
    assert env.base_url == "https://dev.example.com"
    assert env.variables == {"token": "dev-tkn"}
    assert env.is_default is True

    db.update(eid, base_url="https://dev2.example.com")
    assert db.get(eid).base_url == "https://dev2.example.com"

    assert db.delete(eid) is True
    assert db.get(eid) is None


def test_list(tmp_path):
    db = _db(tmp_path)
    db.create(name="dev", base_url="https://dev.example.com")
    db.create(name="prod", base_url="https://prod.example.com")
    envs = db.list()
    assert len(envs) == 2
    assert {e.name for e in envs} == {"dev", "prod"}


def test_single_default_constraint(tmp_path):
    """设一个为默认时，其他自动取消默认（全表至多一个默认）。"""
    db = _db(tmp_path)
    e1 = db.create(name="dev", base_url="https://dev.example.com", is_default=True)
    e2 = db.create(name="prod", base_url="https://prod.example.com", is_default=True)
    # e2 设默认后，e1 应取消
    assert db.get(e1).is_default is False
    assert db.get(e2).is_default is True


def test_update_set_default_clears_others(tmp_path):
    db = _db(tmp_path)
    e1 = db.create(name="dev", base_url="https://dev.example.com", is_default=True)
    e2 = db.create(name="prod", base_url="https://prod.example.com")
    db.update(e2, is_default=True)
    assert db.get(e1).is_default is False
    assert db.get(e2).is_default is True


def test_get_by_name(tmp_path):
    db = _db(tmp_path)
    db.create(name="dev", base_url="https://dev.example.com")
    env = db.get_by_name("dev")
    assert env is not None
    assert env.base_url == "https://dev.example.com"
    assert db.get_by_name("nope") is None
