import subprocess
import os
import re
import shlex
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger("vocalis.terminal")

# Explicit list of permitted base executables
ALLOWED_BINARIES = {
    "python", "python3", "py",
    "node", "npm", "npx",
    "pip", "pytest", "uv",
    "git",
    "dir", "ls", "type", "cat", "mkdir", "echo"
}

# Subcommands that introduce remote code execution risks
RESTRICTED_SUBCOMMANDS = {
    "pip": {"install", "uninstall"},
    "npm": {"install", "i", "uninstall", "add", "publish"},
    "uv": {"pip", "add", "remove"}
}

# Dangerous shell metacharacters and subshell injection patterns (checked per token)
DANGEROUS_TOKEN_PATTERNS = [
    r"[;&|`]",            # Chaining and pipe operators
    r"[\r\n]",             # Newline injection
    r"\$\(.*\)",           # Command substitution $(...)
    r"`.*`",               # Backtick substitution
    r"\$\{.*\}",           # Variable interpolation ${...}
    r"(?:^|[^\w])(?:>|<|>>|<<)", # Stream redirection
]

def _is_token_dangerous(token: str) -> bool:
    """Checks if an individual argument token contains dangerous shell characters."""
    for pattern in DANGEROUS_TOKEN_PATTERNS:
        if re.search(pattern, token):
            return True
    return False

def execute_terminal_command(command: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """
    Executes a strictly allowlisted command safely within settings.WORKSPACE_DIR sandbox.
    Rejects raw shell chaining, unapproved binaries, and high-risk package install subcommands.
    """
    os.makedirs(settings.WORKSPACE_DIR, exist_ok=True)
    cmd_clean = command.strip()
    
    if not cmd_clean:
        return {"status": "error", "action": "terminal_exec", "message": "Command cannot be empty."}

    # 1. Parse into tokenized argument list
    try:
        # posix=True correctly strips matching quotes so subprocess.run doesn't double-escape args
        args = shlex.split(cmd_clean, posix=True)
    except Exception:
        try:
            args = shlex.split(cmd_clean, posix=False)
            args = [a.strip("\"'") for a in args]
        except Exception as e:
            msg = f"Security restriction: Malformed command line arguments ({str(e)})."
            logger.warning(f"[TERMINAL BLOCKED] Reason: {msg} | Command: {cmd_clean}")
            return {"status": "error", "action": "terminal_exec", "message": msg}

    if not args:
        return {"status": "error", "action": "terminal_exec", "message": "Command contains no executable tokens."}

    # 2. Extract and validate base executable
    raw_exe = args[0].strip("\"'").lower()
    base_exe = os.path.basename(raw_exe)
    if base_exe.endswith(".exe"):
        base_exe = base_exe[:-4]

    if base_exe not in ALLOWED_BINARIES:
        msg = f"Security restriction: Binary '{base_exe}' is not in the permitted sandbox allowlist."
        logger.warning(f"[TERMINAL BLOCKED] Reason: {msg} | Command: {cmd_clean}")
        return {"status": "error", "action": "terminal_exec", "message": msg}

    # 3. Per-token security validation (check every argument for metacharacters/subshells)
    for token in args:
        if _is_token_dangerous(token):
            msg = f"Security restriction: Argument token '{token}' contains prohibited shell metacharacters or subshell expressions."
            logger.warning(f"[TERMINAL BLOCKED] Reason: {msg} | Command: {cmd_clean}")
            return {"status": "error", "action": "terminal_exec", "message": msg}

    # 4. Check restricted subcommands (e.g., pip install, npm install)
    if base_exe in RESTRICTED_SUBCOMMANDS and len(args) > 1:
        subcommand = args[1].lower().strip("\"'")
        if subcommand in RESTRICTED_SUBCOMMANDS[base_exe]:
            msg = f"Security restriction: Subcommand '{base_exe} {subcommand}' is restricted in sandbox to prevent arbitrary package execution."
            logger.warning(f"[TERMINAL BLOCKED] Reason: {msg} | Command: {cmd_clean}")
            return {"status": "error", "action": "terminal_exec", "message": msg}

    # 5. Prepare execution arguments (handle Windows cmd built-ins safely without raw shell)
    cmd_builtins = {"dir", "ls", "type", "cat", "mkdir", "echo"}
    if base_exe in cmd_builtins:
        # Normalize ls -> dir, cat -> type for Windows cmd compatibility
        normalized_exe = "dir" if base_exe == "ls" else ("type" if base_exe == "cat" else base_exe)
        exec_args = ["cmd.exe", "/d", "/c", normalized_exe] + args[1:]
    else:
        exec_args = args

    try:
        proc = subprocess.run(
            exec_args,
            shell=False,
            cwd=settings.WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            errors="replace"
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        logger.warning(f"[TERMINAL TIMEOUT] Command: {cmd_clean}")
        return {
            "status": "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "message": f"Command timed out after {timeout_seconds} seconds."
        }
    except Exception as e:
        logger.error(f"[TERMINAL ERROR] {str(e)} | Command: {cmd_clean}")
        return {
            "status": "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "message": str(e)
        }

