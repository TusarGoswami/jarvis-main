import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger("vocalis.fs")

# Windows reserved device names (including files with extensions like CON.txt)
RESERVED_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def _resolve_safe_path(relative_path: str, must_exist: bool = False) -> str:
    """
    Resolves and strictly validates that the target path remains jailed within settings.WORKSPACE_DIR.
    Guards against:
      - Sibling directory collisions (e.g., ../workspace_backup)
      - Symlink & Windows junction escapes
      - Absolute paths and Windows drive-letter bypasses (C:\...)
      - UNC network paths (\\\\server\\share) and device paths (\\\\?\\...)
      - Windows reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
      - Null-byte injection (\x00) and empty/whitespace inputs
    """
    if not relative_path or not relative_path.strip():
        msg = "File path cannot be empty or whitespace-only."
        logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
        raise ValueError(msg)

    # 1. Null-byte injection check
    if "\x00" in relative_path:
        msg = "Security sandbox violation: Null byte detected in path."
        logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
        raise PermissionError(msg)

    clean_str = relative_path.strip()

    # 2. Reject Windows UNC paths and device paths (\\server\share, //server/share, \\?\...)
    if clean_str.startswith("\\\\") or clean_str.startswith("//") or clean_str.startswith(r"\??"):
        msg = f"Security sandbox violation: UNC and device paths are prohibited ('{clean_str}')."
        logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{clean_str}'")
        raise PermissionError(msg)

    workspace_root = Path(settings.WORKSPACE_DIR).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    # 3. Strip Windows drive letters (e.g. 'C:\' or 'D:') and leading slashes
    if re.match(r"^[a-zA-Z]:", clean_str):
        clean_str = clean_str[2:].lstrip("/\\")
    else:
        clean_str = clean_str.lstrip("/\\")

    if not clean_str:
        clean_str = "."

    # 4. Construct candidate path under workspace root
    target_unresolved = workspace_root / clean_str

    # 5. Check Windows reserved device names on all path parts
    for part in target_unresolved.parts:
        stem = Path(part).stem.upper()
        if stem in RESERVED_DEVICE_NAMES:
            msg = f"Security sandbox violation: Access to reserved device name '{stem}' is prohibited."
            logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
            raise PermissionError(msg)

    # 6. Resolve path and verify containment (handles symlinks & junctions)
    # If candidate exists, resolve candidate. If candidate does not exist yet (new file write), resolve candidate's parent
    if target_unresolved.exists():
        resolved_candidate = target_unresolved.resolve()
        try:
            resolved_candidate.relative_to(workspace_root)
        except ValueError:
            msg = f"Security sandbox violation: Path '{relative_path}' escapes workspace sandbox."
            logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
            raise PermissionError(msg)
    else:
        # Check parent directory containment for non-existent target files/directories
        resolved_parent = target_unresolved.parent.resolve()
        try:
            resolved_parent.relative_to(workspace_root)
        except ValueError:
            msg = f"Security sandbox violation: Parent path for '{relative_path}' escapes workspace sandbox."
            logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
            raise PermissionError(msg)
        
        # Verify synthesized final path remains within workspace root
        resolved_candidate = (resolved_parent / target_unresolved.name).resolve()
        try:
            resolved_candidate.relative_to(workspace_root)
        except ValueError:
            msg = f"Security sandbox violation: Target '{relative_path}' escapes workspace sandbox."
            logger.warning(f"[FS BLOCKED] Reason: {msg} | Target: '{relative_path}'")
            raise PermissionError(msg)

    # 7. Verify existence if required
    if must_exist and not resolved_candidate.exists():
        msg = f"Target '{relative_path}' does not exist in workspace."
        raise FileNotFoundError(msg)

    return str(resolved_candidate)

def fs_write(filepath: str, content: str) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the given content in the sandboxed workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath, must_exist=False)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "status": "success",
            "action": "fs_write",
            "filepath": filepath,
            "bytes_written": len(content.encode("utf-8")),
            "message": f"Successfully written to '{filepath}'"
        }
    except Exception as e:
        return {"status": "error", "action": "fs_write", "filepath": filepath, "message": str(e)}

def fs_read(filepath: str) -> Dict[str, Any]:
    """
    Reads the text contents of a file from the sandboxed workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath, must_exist=True)
        if os.path.isdir(full_path):
            return {"status": "error", "action": "fs_read", "filepath": filepath, "message": f"'{filepath}' is a directory, not a file."}
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {
            "status": "success",
            "action": "fs_read",
            "filepath": filepath,
            "content": content,
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {"status": "error", "action": "fs_read", "filepath": filepath, "message": str(e)}

def fs_edit(filepath: str, target_snippet: str, replacement_snippet: str) -> Dict[str, Any]:
    """
    Replaces a specific snippet of text in a sandboxed workspace file.
    """
    try:
        full_path = _resolve_safe_path(filepath, must_exist=True)
        with open(full_path, "r", encoding="utf-8") as f:
            original = f.read()
        
        if target_snippet not in original:
            return {
                "status": "error",
                "action": "fs_edit",
                "filepath": filepath,
                "message": f"Target snippet not found in '{filepath}'."
            }
        
        updated = original.replace(target_snippet, replacement_snippet, 1)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(updated)
            
        return {
            "status": "success",
            "action": "fs_edit",
            "filepath": filepath,
            "message": f"Successfully updated snippet in '{filepath}'"
        }
    except Exception as e:
        return {"status": "error", "action": "fs_edit", "filepath": filepath, "message": str(e)}

def fs_list(directory: str = ".") -> Dict[str, Any]:
    """
    Lists all files and directories within a sandboxed workspace directory.
    """
    try:
        full_path = _resolve_safe_path(directory, must_exist=True)
        entries: List[Dict[str, Any]] = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            entries.append({
                "name": item,
                "is_directory": is_dir,
                "size_bytes": size
            })
        return {
            "status": "success",
            "action": "fs_list",
            "directory": directory,
            "entries": entries,
            "total_items": len(entries)
        }
    except Exception as e:
        return {"status": "error", "action": "fs_list", "directory": directory, "message": str(e)}

def fs_delete(filepath: str) -> Dict[str, Any]:
    """
    Deletes a file or directory within the sandboxed workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath, must_exist=True)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return {
            "status": "success",
            "action": "fs_delete",
            "filepath": filepath,
            "message": f"Deleted '{filepath}'"
        }
    except Exception as e:
        return {"status": "error", "action": "fs_delete", "filepath": filepath, "message": str(e)}

