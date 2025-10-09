# Windows/WSL Support for Cursor CLI

## Overview

Stomper now automatically detects your operating system and executes `cursor-agent` via WSL when running on Windows. This ensures seamless cross-platform compatibility.

## How It Works

### 1. **Automatic OS Detection**

When the `CursorClient` initializes, it automatically detects:

- ✅ **Windows Native** - Running on Windows outside of WSL
- ✅ **WSL Environment** - Running inside Windows Subsystem for Linux
- ✅ **Unix/Linux** - Running on Linux or macOS
- ✅ **WSL Availability** - Whether WSL is installed and accessible on Windows

### 2. **Smart Command Execution**

Based on the detected environment:

| Environment | Behavior |
|-------------|----------|
| **Windows + WSL Available** | Wraps `cursor-agent` with `wsl --cd <wsl_path> -- cursor-agent ...` |
| **Inside WSL** | Executes `cursor-agent` directly |
| **Unix/Linux** | Executes `cursor-agent` directly |
| **Windows (no WSL)** | Attempts direct execution (will fail if cursor-agent not installed) |

### 3. **Automatic Path Conversion**

Windows paths are automatically converted to WSL format:

```
Windows Path:  E:\workspaces\ai\tools\stomper
WSL Path:      /mnt/e/workspaces/ai/tools/stomper

Windows Path:  C:\Users\username\project
WSL Path:      /mnt/c/Users/username/project
```

## Implementation Details

### Detection Functions

```python
def _is_wsl() -> bool:
    """Check if currently running inside WSL."""
    # Checks for WSL-specific markers in /proc/version

def _is_windows() -> bool:
    """Check if running on Windows (not WSL)."""
    # Uses platform.system() == "Windows"

def _is_wsl_available() -> bool:
    """Check if WSL is available on Windows."""
    # Runs 'wsl --status' to verify WSL installation
```

### Command Preparation

```python
def _prepare_command(self, cmd: list[str], cwd: str) -> tuple[list[str], str]:
    """Prepare command for execution, wrapping with WSL if needed."""
    if self.use_wsl:
        wsl_cwd = _windows_path_to_wsl(cwd)
        
        # Build shell command with proper escaping
        # Use login shell (-l) to load PATH from profile (~/.bashrc, ~/.profile)
        # This ensures cursor-agent is found in ~/.local/bin or npm global paths
        escaped_cmd = " ".join(shlex.quote(arg) for arg in cmd)
        shell_cmd = f"cd {shlex.quote(wsl_cwd)} && {escaped_cmd}"
        
        # Wrap with WSL using bash login shell
        wsl_cmd = ["wsl", "bash", "-l", "-c", shell_cmd]
        
        return wsl_cmd, cwd
    else:
        return cmd, cwd
```

## Usage

No configuration needed! The system automatically adapts:

```python
from stomper.ai.cursor_client import CursorClient
from stomper.ai.sandbox_manager import SandboxManager

# Initialize (automatically detects environment)
sandbox_manager = SandboxManager(project_root)
cursor_client = CursorClient(sandbox_manager=sandbox_manager)

# Will log one of:
# "🪟 Running on Windows - cursor-agent will be executed via WSL"
# "🐧 Running inside WSL - cursor-agent will execute natively"  
# "🐧 Running on Unix/Linux - cursor-agent will execute natively"
```

## Requirements

### For Windows Users

1. **Install WSL** (if not already installed):
   ```powershell
   wsl --install
   ```

2. **Install cursor-agent in WSL**:
   ```bash
   # Inside WSL
   npm install -g @cursor.sh/cursor-agent
   ```

### For WSL/Linux Users

1. **Install cursor-agent**:
   ```bash
   npm install -g @cursor.sh/cursor-agent
   ```

## Troubleshooting

### "cursor-cli not available or not accessible"

**On Windows:**
- Verify WSL is installed: `wsl --status`
- Verify cursor-agent is installed in WSL: `wsl bash -l -c "cursor-agent -v"`
- **Note**: Use `bash -l` (login shell) to load your PATH properly

**On WSL/Linux:**
- Verify cursor-agent is installed: `cursor-agent -v`
- Check PATH: `which cursor-agent`

### PATH Issues in WSL

**Problem**: cursor-agent works in interactive WSL but not via `wsl -- cursor-agent`

**Cause**: Non-interactive WSL shells don't load `~/.bashrc` or `~/.profile`, so tools installed in `~/.local/bin` or npm global paths aren't found.

**Solution**: Stomper uses `bash -l` (login shell) which loads your profile and PATH:
```bash
# ❌ Doesn't work (non-interactive, no PATH)
wsl -- cursor-agent -v

# ✅ Works (login shell loads PATH)
wsl bash -l -c "cursor-agent -v"
```

If cursor-agent is installed but still not found:
1. Check installation location: `wsl bash -l -c "which cursor-agent"`
2. Ensure it's in a standard location like:
   - `~/.local/bin/cursor-agent`
   - `/usr/local/bin/cursor-agent`
   - npm global bin (check with `npm bin -g`)

### Path Conversion Issues

If you encounter path-related errors, ensure:
- Windows paths use backslashes: `E:\path\to\project`
- The drive letter is valid and accessible from WSL
- The path exists and is readable

## Testing

To verify the detection is working:

```python
from stomper.ai.cursor_client import (
    _is_wsl, 
    _is_windows, 
    _is_wsl_available,
    _windows_path_to_wsl
)

print(f"Is Windows? {_is_windows()}")
print(f"Is WSL? {_is_wsl()}")
print(f"Is WSL Available? {_is_wsl_available()}")

# Test path conversion
test_path = r"E:\workspaces\ai\tools\stomper"
wsl_path = _windows_path_to_wsl(test_path)
print(f"{test_path} -> {wsl_path}")
```

## Benefits

✅ **Seamless Cross-Platform** - Works on Windows, WSL, Linux, and macOS
✅ **Zero Configuration** - Automatically detects and adapts to your environment
✅ **Smart Path Handling** - Converts Windows paths to WSL format automatically
✅ **Backwards Compatible** - No changes needed for existing Linux/WSL users
✅ **Clear Logging** - Informative messages about the execution environment

