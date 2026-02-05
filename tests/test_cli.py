from __future__ import annotations

import pytest


def test_cli_exits_on_missing_directory(monkeypatch, tmp_path) -> None:
    import ai_pdf_renamer.cli as cli

    monkeypatch.setattr(cli, "setup_logging", lambda **k: None)

    missing = tmp_path / "missing"
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "--dir",
                str(missing),
                "--language",
                "de",
                "--case",
                "kebabCase",
                "--project",
                "",
                "--version",
                "",
            ]
        )

    assert "Directory does not exist" in str(excinfo.value)


def test_cli_reprompts_on_invalid_choices(monkeypatch, tmp_path) -> None:
    import builtins

    import ai_pdf_renamer.cli as cli

    monkeypatch.setattr(cli, "setup_logging", lambda **k: None)

    inputs = iter(["fr", "en", "badcase", "snakecase"])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(inputs))

    captured: dict[str, object] = {}

    def _fake_rename(directory, *, config):
        captured["directory"] = directory
        captured["config"] = config

    monkeypatch.setattr(cli, "rename_pdfs_in_directory", _fake_rename)

    cli.main(
        [
            "--dir",
            str(tmp_path),
            "--project",
            "",
            "--version",
            "",
        ]
    )

    config = captured["config"]
    assert config.language == "en"
    assert config.desired_case == "snakeCase"
