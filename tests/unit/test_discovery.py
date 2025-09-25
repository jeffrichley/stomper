"""Tests for file discovery functionality."""

from pathlib import Path

from stomper.discovery import FileFilter, FileScanner


class TestFileScanner:
    """Test file scanner functionality."""

    def test_scanner_initialization(self):
        """Test scanner initialization."""
        project_root = Path.cwd()
        scanner = FileScanner(project_root)
        assert scanner.project_root == project_root.resolve()

    def test_discover_single_file(self, tmp_path):
        """Test discovering a single file."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        scanner = FileScanner(tmp_path)
        files = scanner.discover_files(target_path=test_file)

        assert len(files) == 1
        assert files[0] == test_file

    def test_discover_nonexistent_file(self, tmp_path):
        """Test discovering a nonexistent file."""
        scanner = FileScanner(tmp_path)
        nonexistent_file = tmp_path / "nonexistent.py"

        files = scanner.discover_files(target_path=nonexistent_file)
        assert len(files) == 0

    def test_discover_directory(self, tmp_path):
        """Test discovering files in a directory."""
        # Create test files
        (tmp_path / "file1.py").write_text("print('hello')")
        (tmp_path / "file2.py").write_text("print('world')")
        (tmp_path / "file3.txt").write_text("not python")

        scanner = FileScanner(tmp_path)
        files = scanner.discover_files(target_path=tmp_path)

        # Should find 2 Python files
        assert len(files) == 2
        file_names = {f.name for f in files}
        assert file_names == {"file1.py", "file2.py"}

    def test_discover_with_exclude_patterns(self, tmp_path):
        """Test discovering files with exclude patterns."""
        # Create test files
        (tmp_path / "file1.py").write_text("print('hello')")
        (tmp_path / "file2.py").write_text("print('world')")
        (tmp_path / "test_file.py").write_text("print('test')")

        scanner = FileScanner(tmp_path)
        files = scanner.discover_files(target_path=tmp_path, exclude_patterns=["**/test_*.py"])

        # Should find 2 files (excluding test_file.py)
        assert len(files) == 2
        file_names = {f.name for f in files}
        assert file_names == {"file1.py", "file2.py"}

    def test_discover_with_max_files(self, tmp_path):
        """Test discovering files with max_files limit."""
        # Create test files
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text(f"print('hello {i}')")

        scanner = FileScanner(tmp_path)
        files = scanner.discover_files(target_path=tmp_path, max_files=3)

        # Should find only 3 files due to limit
        assert len(files) == 3

    def test_get_file_stats(self, tmp_path):
        """Test getting file statistics."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("print('hello')")

        file2 = tmp_path / "file2.py"
        file2.write_text("print('world')")

        scanner = FileScanner(tmp_path)
        files = [file1, file2]
        stats = scanner.get_file_stats(files)

        assert stats["total_files"] == 2
        assert stats["total_size"] > 0
        assert len(stats["directories"]) == 1


class TestFileFilter:
    """Test file filter functionality."""

    def test_filter_initialization(self):
        """Test filter initialization."""
        project_root = Path.cwd()
        filter_obj = FileFilter(project_root)
        assert filter_obj.project_root == project_root.resolve()

    def test_filter_files_basic(self, tmp_path):
        """Test basic file filtering."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("print('hello')")

        file2 = tmp_path / "file2.py"
        file2.write_text("print('world')")

        filter_obj = FileFilter(tmp_path)
        files = [file1, file2]

        # No filtering should return all files
        filtered = filter_obj.filter_files(files)
        assert len(filtered) == 2

    def test_filter_files_with_exclude(self, tmp_path):
        """Test file filtering with exclude patterns."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("print('hello')")

        test_file = tmp_path / "test_file.py"
        test_file.write_text("print('test')")

        filter_obj = FileFilter(tmp_path)
        files = [file1, test_file]

        # Exclude test files
        filtered = filter_obj.filter_files(files, exclude_patterns=["**/test_*.py"])

        assert len(filtered) == 1
        assert filtered[0] == file1

    def test_filter_files_with_include(self, tmp_path):
        """Test file filtering with include patterns."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("print('hello')")

        test_file = tmp_path / "test_file.py"
        test_file.write_text("print('test')")

        filter_obj = FileFilter(tmp_path)
        files = [file1, test_file]

        # Include only test files
        filtered = filter_obj.filter_files(files, include_patterns=["**/test_*.py"])

        assert len(filtered) == 1
        assert filtered[0] == test_file

    def test_get_common_patterns(self):
        """Test getting common patterns."""
        project_root = Path.cwd()
        filter_obj = FileFilter(project_root)
        patterns = filter_obj.get_common_patterns()

        assert "include" in patterns
        assert "exclude" in patterns
        assert len(patterns["include"]) > 0
        assert len(patterns["exclude"]) > 0

    def test_validate_patterns(self):
        """Test pattern validation."""
        project_root = Path.cwd()
        filter_obj = FileFilter(project_root)

        # Test with valid patterns
        patterns = ["**/*.py", "src/**/*.py", ""]
        validated = filter_obj.validate_patterns(patterns)

        assert len(validated) == 2  # Empty pattern should be removed
        assert "**/*.py" in validated
        assert "src/**/*.py" in validated
