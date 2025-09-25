# Stomper development commands

# Run only unit tests (fast)
test:
    uv run pytest tests/unit/ -v -m "not e2e"

# Run all tests (unit + integration + e2e)
test-all:
    uv run pytest tests/ -v

# Run tests with coverage
test-coverage:
    uv run pytest tests/ --cov=src/stomper --cov-report=html --cov-report=term

# Run linting
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Fix linting issues
lint-fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run type checking
type-check:
    uv run mypy src/

# Run all quality checks
check: lint type-check test

# Install dependencies
install:
    uv sync

# Run the CLI
run:
    uv run stomper

# Clean up cache files
clean:
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    rm -rf .pytest_cache/ 2>/dev/null || true
    rm -rf htmlcov/ 2>/dev/null || true
