from __future__ import annotations

from ai_pdf_renamer import data_paths


def test_data_path_falls_back_to_package_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(data_paths, "data_dir", lambda: tmp_path)

    path = data_paths.data_path("meta_stopwords.json")

    assert path.exists()
    assert path.name == "meta_stopwords.json"
    assert path.parent.name == "data"
