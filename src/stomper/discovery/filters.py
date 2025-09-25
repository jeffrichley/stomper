"""File filtering and pattern matching for Stomper."""

from pathlib import Path

import pathspec


class FileFilter:
    """Filters files based on patterns and criteria."""

    def __init__(self, project_root: Path):
        """Initialize the file filter with project root."""
        self.project_root = project_root.resolve()

    def filter_files(
        self,
        files: list[Path],
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[Path]:
        """
        Filter files based on include/exclude patterns.

        Args:
            files: List of files to filter
            include_patterns: List of include patterns (gitignore-style)
            exclude_patterns: List of exclude patterns (gitignore-style)

        Returns:
            Filtered list of files
        """
        if not files:
            return []

        # Create pathspec objects for pattern matching
        include_spec = None
        if include_patterns:
            include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)

        exclude_spec = None
        if exclude_patterns:
            exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)

        filtered_files = []

        for file_path in files:
            # Get relative path for pattern matching
            try:
                relative_path = file_path.relative_to(self.project_root)
            except ValueError:
                # File is outside project root, skip it
                continue

            # Check include patterns
            if include_spec and not include_spec.match_file(str(relative_path)):
                continue

            # Check exclude patterns
            if exclude_spec and exclude_spec.match_file(str(relative_path)):
                continue

            filtered_files.append(file_path)

        return filtered_files

    def get_common_patterns(self) -> dict:
        """Get common include/exclude patterns for Python projects."""
        return {
            "include": [
                "src/**/*.py",
                "tests/**/*.py",
                "**/*.py",
            ],
            "exclude": [
                "**/migrations/**",
                "**/legacy/**",
                "**/__pycache__/**",
                "**/.venv/**",
                "**/venv/**",
                "**/env/**",
                "**/node_modules/**",
                "**/build/**",
                "**/dist/**",
                "**/.git/**",
                "**/.pytest_cache/**",
                "**/coverage/**",
                "**/.coverage",
                "**/htmlcov/**",
            ],
        }

    def validate_patterns(self, patterns: list[str]) -> list[str]:
        """Validate and clean up patterns."""
        valid_patterns = []

        for pattern in patterns:
            # Basic validation
            if not pattern or not pattern.strip():
                continue

            # Clean up pattern
            clean_pattern = pattern.strip()

            # Skip empty patterns
            if not clean_pattern:
                continue

            valid_patterns.append(clean_pattern)

        return valid_patterns
