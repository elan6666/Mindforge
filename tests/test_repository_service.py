from pathlib import Path

from app.backend.services.repository_service import RepositoryAnalysisService


def create_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_repository_analysis_skips_when_repo_path_missing():
    service = RepositoryAnalysisService()

    result = service.analyze(None)

    assert result.status == "skipped"
    assert result.repo_summary is None
    assert result.warnings


def test_repository_analysis_detects_stack_key_files_and_entrypoints(tmp_path):
    create_file(tmp_path / "README.md", "# Demo")
    create_file(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    create_file(tmp_path / "app" / "main.py", "print('hello')")
    create_file(tmp_path / "frontend" / "index.tsx", "export {}")

    service = RepositoryAnalysisService()
    result = service.analyze(str(tmp_path))

    assert result.status == "analyzed"
    assert result.repo_summary is not None
    assert "Python" in result.repo_summary.detected_stack
    assert "app" in result.repo_summary.top_level_directories
    assert any(item.path == "README.md" for item in result.repo_summary.key_files)
    assert "app/main.py" in result.repo_summary.entrypoints
    assert result.repo_summary.summary_text


def test_repository_analysis_fails_for_missing_path():
    service = RepositoryAnalysisService()

    result = service.analyze("Z:/definitely-missing-repo")

    assert result.status == "failed"
    assert result.repo_summary is None
    assert result.error_message


def test_repository_analysis_fails_for_file_path(tmp_path):
    file_path = tmp_path / "single-file.txt"
    create_file(file_path, "hello")
    service = RepositoryAnalysisService()

    result = service.analyze(str(file_path))

    assert result.status == "failed"
    assert result.error_message == "Repository path is not a directory."
