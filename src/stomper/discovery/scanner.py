"""File discovery and scanning logic for Stomper."""

import glob
import os
from pathlib import Path

import pathspec


class FileScanner:
    """Scans and discovers files based on various criteria."""

    def __init__(self, project_root: Path):
        """Initialize the file scanner with project root."""
        self.project_root = project_root.resolve()

    def discover_files(
        self,
        target_path: Path | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_files: int | None = None,
    ) -> list[Path]:
        """
        Discover files based on target path and patterns.

        Args:
            target_path: Specific file, directory, or None for project root
            include_patterns: List of include patterns (glob-style)
            exclude_patterns: List of exclude patterns (gitignore-style)
            max_files: Maximum number of files to return

        Returns:
            List of discovered file paths
        """
        if target_path is None:
            target_path = self.project_root
        else:
            target_path = target_path.resolve()

        # Handle single file
        if target_path.is_file():
            return [target_path]

        # Handle directory
        if target_path.is_dir():
            return self._scan_directory(
                target_path,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                max_files=max_files,
            )

        # Handle glob patterns
        if "*" in str(target_path) or "?" in str(target_path):
            return self._scan_glob_pattern(
                str(target_path),
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                max_files=max_files,
            )

        # Default: return empty list for invalid paths
        return []

    def _scan_directory(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_files: int | None = None,
    ) -> list[Path]:
        """Scan a directory for Python files."""
        discovered_files: list[Path] = []

        # Default include pattern for Python files
        if include_patterns is None:
            include_patterns = ["**/*.py"]

        # Use pathspec for efficient pattern matching
        include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)

        exclude_spec = None
        if exclude_patterns:
            exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)

        # Scan directory using os.scandir for performance
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)

                # Check include patterns
                if not include_spec.match_file(str(relative_path)):
                    continue

                # Check exclude patterns
                if exclude_spec and exclude_spec.match_file(str(relative_path)):
                    continue

                discovered_files.append(file_path)

                # Respect max_files limit
                if max_files and len(discovered_files) >= max_files:
                    break

            # Break outer loop if we've hit the limit
            if max_files and len(discovered_files) >= max_files:
                break

        return discovered_files

    def _scan_glob_pattern(
        self,
        pattern: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_files: int | None = None,
    ) -> list[Path]:
        """Scan using glob patterns."""
        discovered_files: list[Path] = []

        # Find all matching files
        for file_path in glob.glob(pattern, recursive=True):
            path = Path(file_path)
            if not path.is_file() or path.suffix != ".py":
                continue

            relative_path = path.relative_to(self.project_root)

            # Check include patterns
            if include_patterns:
                include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)
                if not include_spec.match_file(str(relative_path)):
                    continue

            # Check exclude patterns
            if exclude_patterns:
                exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)
                if exclude_spec.match_file(str(relative_path)):
                    continue

            discovered_files.append(path)

            # Respect max_files limit
            if max_files and len(discovered_files) >= max_files:
                break

        return discovered_files

    def get_file_stats(self, files: list[Path]) -> dict:
        """Get statistics about discovered files."""
        if not files:
            return {
                "total_files": 0,
                "total_size": 0,
                "directories": set(),
            }

        total_size = sum(f.stat().st_size for f in files if f.exists())
        directories = {f.parent for f in files}

        return {
            "total_files": len(files),
            "total_size": total_size,
            "directories": directories,
        }
