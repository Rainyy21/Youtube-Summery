import pytest

import config


@pytest.fixture(autouse=True)
def fake_config_file(tmp_path, monkeypatch):
    # never touch the real ~/.config file
    path = tmp_path / "cfg" / "config.json"
    monkeypatch.setattr(config, "CONFIG_FILE", path)
    return path


def test_default_when_no_config():
    assert config.get_output_dir() == config.DEFAULT_DIR


def test_default_when_config_is_broken(fake_config_file):
    fake_config_file.parent.mkdir(parents=True)
    fake_config_file.write_text("not json")
    assert config.get_output_dir() == config.DEFAULT_DIR


def test_set_then_get(tmp_path):
    full = config.set_output_dir(tmp_path / "notes")
    assert full == str((tmp_path / "notes").resolve())
    assert config.get_output_dir() == full
