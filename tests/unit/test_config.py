"""Unit tests for configuration system."""

import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from pydantic import ValidationError
import pytest

from stomper.config.loader import ConfigLoader
from stomper.config.models import ConfigOverride, GitConfig, IgnoreConfig, StomperConfig
from stomper.config.validator import ConfigValidator


@pytest.mark.unit
class TestStomperConfig:
    """Test StomperConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StomperConfig()

        assert config.quality_tools == ["ruff", "mypy"]
        assert config.ai_agent == "cursor-cli"
        assert config.max_retries == 3
        assert config.parallel_files == 1
        assert isinstance(config.ignores, IgnoreConfig)
        assert isinstance(config.git, GitConfig)

    def test_custom_config(self):
        """Test custom configuration values."""
        config = StomperConfig(
            quality_tools=["ruff", "mypy", "drill-sergeant"],
            ai_agent="cursor-cli",
            max_retries=5,
            parallel_files=2,
            ignores=IgnoreConfig(files=["tests/**"], errors=["E501"]),
            git=GitConfig(branch_prefix="fix", commit_style="simple"),
        )

        assert config.quality_tools == ["ruff", "mypy", "drill-sergeant"]
        assert config.ai_agent == "cursor-cli"
        assert config.max_retries == 5
        assert config.parallel_files == 2
        assert config.ignores.files == ["tests/**"]
        assert config.ignores.errors == ["E501"]
        assert config.git.branch_prefix == "fix"
        assert config.git.commit_style == "simple"

    def test_validation_quality_tools(self):
        """Test quality tools validation."""
        with pytest.raises(ValidationError) as exc_info:
            StomperConfig(quality_tools=["invalid-tool"])

        # Check structured error data
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("quality_tools", 0)
        assert errors[0]["type"] == "literal_error"

    def test_validation_ai_agent(self):
        """Test AI agent validation."""
        with pytest.raises(ValidationError) as exc_info:
            StomperConfig(ai_agent="invalid-agent")

        # Check structured error data
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("ai_agent",)
        assert errors[0]["type"] == "literal_error"

    def test_validation_max_retries(self):
        """Test max retries validation."""
        with pytest.raises(ValidationError) as exc_info:
            StomperConfig(max_retries=-1)

        # Check structured error data
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("max_retries",)
        assert errors[0]["type"] == "greater_than_equal"

    def test_validation_parallel_files(self):
        """Test parallel files validation."""
        with pytest.raises(ValidationError) as exc_info:
            StomperConfig(parallel_files=0)

        # Check structured error data
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("parallel_files",)
        assert errors[0]["type"] == "greater_than_equal"


@pytest.mark.unit
class TestConfigOverride:
    """Test ConfigOverride model."""

    def test_default_override(self):
        """Test default override values."""
        override = ConfigOverride()

        assert override.ruff is None
        assert override.mypy is None
        assert override.drill_sergeant is None
        assert override.file is None
        assert override.files is None
        assert override.error_type is None
        assert override.ignore is None
        assert override.max_errors is None
        assert override.dry_run is None
        assert override.verbose is None

    def test_custom_override(self):
        """Test custom override values."""
        override = ConfigOverride(
            ruff=True,
            mypy=False,
            file=Path("test.py"),
            files=[Path("file1.py"), Path("file2.py")],
            error_type="E501",
            ignore=["F401", "F841"],
            max_errors=50,
            dry_run=True,
            verbose=True,
        )

        assert override.ruff is True
        assert override.mypy is False
        assert override.file == Path("test.py")
        assert override.files == [Path("file1.py"), Path("file2.py")]
        assert override.error_type == "E501"
        assert override.ignore == ["F401", "F841"]
        assert override.max_errors == 50
        assert override.dry_run is True
        assert override.verbose is True

    def test_validation_max_errors(self):
        """Test max errors validation."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigOverride(max_errors=0)

        # Check structured error data
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("max_errors",)
        assert errors[0]["type"] == "greater_than_equal"


@pytest.mark.unit
class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_default_config(self):
        """Test loading default configuration."""
        loader = ConfigLoader()
        config = loader.load_config()

        assert isinstance(config, StomperConfig)
        assert config.quality_tools == ["ruff", "mypy"]
        assert config.ai_agent == "cursor-cli"
        assert config.max_retries == 3
        assert config.parallel_files == 1

    def test_pyproject_config_loading(self):
        """Test loading configuration from pyproject.toml."""
        pyproject_content = """
[tool.stomper]
quality_tools = ["ruff", "mypy", "drill-sergeant"]
ai_agent = "cursor-cli"
max_retries = 5
parallel_files = 2

[tool.stomper.ignores]
files = ["tests/**", "migrations/**"]
errors = ["E501", "F401"]

[tool.stomper.git]
branch_prefix = "fix"
commit_style = "simple"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            pyproject_path = project_root / "pyproject.toml"

            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            loader = ConfigLoader(project_root)
            config = loader.load_config()

            assert config.quality_tools == ["ruff", "mypy", "drill-sergeant"]
            assert config.max_retries == 5
            assert config.parallel_files == 2
            assert config.ignores.files == ["tests/**", "migrations/**"]
            assert config.ignores.errors == ["E501", "F401"]
            assert config.git.branch_prefix == "fix"
            assert config.git.commit_style == "simple"

    def test_environment_overrides(self):
        """Test environment variable overrides."""
        env_vars = {
            "STOMPER_QUALITY_TOOLS": "ruff,mypy,drill-sergeant",
            "STOMPER_AI_AGENT": "cursor-cli",
            "STOMPER_MAX_RETRIES": "5",
            "STOMPER_PARALLEL_FILES": "2",
            "STOMPER_IGNORE_FILES": "tests/**,migrations/**",
            "STOMPER_IGNORE_ERRORS": "E501,F401",
            "STOMPER_BRANCH_PREFIX": "fix",
            "STOMPER_COMMIT_STYLE": "simple",
        }

        with patch.dict(os.environ, env_vars):
            loader = ConfigLoader()
            config = loader.load_config()

            assert config.quality_tools == ["ruff", "mypy", "drill-sergeant"]
            assert config.ai_agent == "cursor-cli"
            assert config.max_retries == 5
            assert config.parallel_files == 2
            assert config.ignores.files == ["tests/**", "migrations/**"]
            assert config.ignores.errors == ["E501", "F401"]
            assert config.git.branch_prefix == "fix"
            assert config.git.commit_style == "simple"

    def test_cli_overrides(self):
        """Test CLI argument overrides."""
        loader = ConfigLoader()
        loader.load_config()

        # Create CLI overrides
        overrides = ConfigOverride(ruff=False, mypy=True, drill_sergeant=True)

        # Apply overrides
        updated_config = loader.apply_cli_overrides(overrides)

        # Check that ruff is disabled and drill-sergeant is enabled
        assert "ruff" not in updated_config.quality_tools
        assert "mypy" in updated_config.quality_tools
        assert "drill-sergeant" in updated_config.quality_tools


@pytest.mark.unit
class TestConfigValidator:
    """Test ConfigValidator functionality."""

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = StomperConfig()
        project_root = Path.cwd()

        validator = ConfigValidator()
        result = validator.validate_config(config, project_root)

        assert result is True
        assert len(validator.errors) == 0

    def test_validate_config_invalid_git(self):
        """Test configuration validation with invalid git config."""
        config = StomperConfig()
        config.git.branch_prefix = ""  # Invalid empty prefix
        project_root = Path.cwd()

        validator = ConfigValidator()
        result = validator.validate_config(config, project_root)

        assert result is False
        assert len(validator.errors) > 0
        assert any("branch prefix cannot be empty" in error for error in validator.errors)

    def test_validate_cli_overrides_success(self):
        """Test successful CLI overrides validation."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            overrides = ConfigOverride(
                file=tmp_path, error_type="E501", ignore=["F401", "F841"], max_errors=50
            )

            validator = ConfigValidator()
            result = validator.validate_cli_overrides(overrides)

            assert result is True
            assert len(validator.errors) == 0
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    def test_validate_cli_overrides_invalid_file(self):
        """Test CLI overrides validation with invalid file."""
        overrides = ConfigOverride(file=Path("nonexistent.py"), error_type="E501")

        validator = ConfigValidator()
        result = validator.validate_cli_overrides(overrides)

        assert result is False
        assert len(validator.errors) > 0
        assert any("does not exist" in error for error in validator.errors)
