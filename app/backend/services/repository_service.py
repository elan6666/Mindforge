"""Lightweight local repository scanning and summary generation."""

from pathlib import Path

from app.backend.schemas.repository import RepoAnalysisResult, RepoKeyFile, RepoSummary

KNOWN_KEY_FILES: dict[str, str] = {
    "README.md": "documentation",
    "pyproject.toml": "python-config",
    "requirements.txt": "python-dependencies",
    "setup.py": "python-build",
    "package.json": "node-config",
    "package-lock.json": "node-lockfile",
    "pnpm-lock.yaml": "node-lockfile",
    "yarn.lock": "node-lockfile",
    "tsconfig.json": "typescript-config",
    "Dockerfile": "container",
    "docker-compose.yml": "container",
    "docker-compose.yaml": "container",
    ".env.example": "environment-template",
    ".gitignore": "scm-config",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "main.ts",
    "main.tsx",
    "index.tsx",
    "index.js",
    "index.ts",
}

STACK_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "Python"),
    ("requirements.txt", "Python"),
    ("setup.py", "Python"),
    ("package.json", "Node.js"),
    ("tsconfig.json", "TypeScript"),
    ("Cargo.toml", "Rust"),
    ("pom.xml", "Java"),
    ("build.gradle", "Java"),
    ("Dockerfile", "Docker"),
    ("docker-compose.yml", "Docker"),
    ("docker-compose.yaml", "Docker"),
)


class RepositoryAnalysisService:
    """Analyze a local repository using shallow deterministic rules."""

    def analyze(self, repo_path: str | None) -> RepoAnalysisResult:
        """Return a structured repo summary or a degraded result."""
        if not repo_path:
            return RepoAnalysisResult(
                status="skipped",
                warnings=["Repository analysis skipped because repo_path was not provided."],
            )

        candidate = Path(repo_path).expanduser()
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            return RepoAnalysisResult(
                status="failed",
                warnings=[f"Repository path '{repo_path}' does not exist."],
                error_message="Repository path not found.",
            )
        except OSError as exc:
            return RepoAnalysisResult(
                status="failed",
                warnings=[f"Repository path '{repo_path}' could not be resolved."],
                error_message=str(exc),
            )

        if not resolved.is_dir():
            return RepoAnalysisResult(
                status="failed",
                warnings=[f"Repository path '{resolved}' is not a directory."],
                error_message="Repository path is not a directory.",
            )

        top_level_directories = self._get_top_level_directories(resolved)
        key_files = self._find_key_files(resolved)
        entrypoints = self._find_entrypoints(resolved)
        detected_stack = self._detect_stack(key_files)
        summary = RepoSummary(
            repo_path=repo_path,
            resolved_path=str(resolved),
            repository_name=resolved.name,
            detected_stack=detected_stack,
            top_level_directories=top_level_directories,
            key_files=key_files,
            entrypoints=entrypoints,
            summary_text=self._build_summary_text(
                resolved=resolved,
                detected_stack=detected_stack,
                top_level_directories=top_level_directories,
                key_files=key_files,
                entrypoints=entrypoints,
            ),
        )
        warnings: list[str] = []
        if not key_files:
            warnings.append("No known key files were detected during lightweight scan.")
        if not entrypoints:
            warnings.append("No likely entrypoint files were detected during lightweight scan.")
        return RepoAnalysisResult(
            status="analyzed",
            repo_summary=summary,
            warnings=warnings,
        )

    def _get_top_level_directories(self, root: Path) -> list[str]:
        """Return a bounded list of top-level directories."""
        directories = [
            item.name
            for item in sorted(root.iterdir(), key=lambda path: path.name.lower())
            if item.is_dir() and not item.name.startswith(".")
        ]
        return directories[:12]

    def _find_key_files(self, root: Path) -> list[RepoKeyFile]:
        """Find important files using known file-name rules."""
        key_files: list[RepoKeyFile] = []
        for filename, category in KNOWN_KEY_FILES.items():
            matches = list(root.rglob(filename))[:2]
            for match in matches:
                relative = match.relative_to(root).as_posix()
                key_files.append(RepoKeyFile(path=relative, category=category))
        key_files.sort(key=lambda item: item.path)
        return key_files

    def _find_entrypoints(self, root: Path) -> list[str]:
        """Identify likely application entrypoints using bounded file-name rules."""
        matches: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name not in ENTRYPOINT_NAMES:
                continue
            relative = path.relative_to(root)
            if len(relative.parts) > 4:
                continue
            matches.append(relative.as_posix())
            if len(matches) >= 8:
                break
        return sorted(matches)

    def _detect_stack(self, key_files: list[RepoKeyFile]) -> list[str]:
        """Infer a lightweight technology stack from known files."""
        paths = {item.path.split("/")[-1] for item in key_files}
        stack: list[str] = []
        for marker, label in STACK_MARKERS:
            if marker in paths and label not in stack:
                stack.append(label)
        return stack

    def _build_summary_text(
        self,
        resolved: Path,
        detected_stack: list[str],
        top_level_directories: list[str],
        key_files: list[RepoKeyFile],
        entrypoints: list[str],
    ) -> str:
        """Create a compact natural-language summary for prompt injection."""
        stack = ", ".join(detected_stack) if detected_stack else "unknown stack"
        directories = ", ".join(top_level_directories[:6]) or "no major directories detected"
        files = ", ".join(item.path for item in key_files[:6]) or "no key files detected"
        entry_text = ", ".join(entrypoints[:4]) or "no likely entrypoints detected"
        return (
            f"Repository '{resolved.name}' appears to use {stack}. "
            f"Top-level directories: {directories}. "
            f"Key files: {files}. "
            f"Likely entrypoints: {entry_text}."
        )
