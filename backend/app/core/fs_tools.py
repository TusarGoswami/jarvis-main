import os
import shutil
from typing import Dict, Any, List
from app.config import settings

def _resolve_safe_path(relative_path: str) -> str:
    """
    Resolves and validates that the target path remains strictly within settings.WORKSPACE_DIR.
    Prevents path traversal attacks (e.g. '../').
    """
    os.makedirs(settings.WORKSPACE_DIR, exist_ok=True)
    clean_rel = os.path.normpath(relative_path).lstrip(r"\/\\")
    full_path = os.path.abspath(os.path.join(settings.WORKSPACE_DIR, clean_rel))
    
    workspace_root = os.path.abspath(settings.WORKSPACE_DIR)
    if not full_path.startswith(workspace_root):
        raise PermissionError(f"Security sandbox violation: Access to '{relative_path}' outside workspace is denied.")
    return full_path

def fs_write(filepath: str, content: str) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the given content in the workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath)
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
    Reads the text contents of a file from the workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath)
        if not os.path.exists(full_path):
            return {"status": "error", "action": "fs_read", "filepath": filepath, "message": f"File '{filepath}' not found."}
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
    Replaces a specific snippet of text in a workspace file.
    """
    try:
        full_path = _resolve_safe_path(filepath)
        if not os.path.exists(full_path):
            return {"status": "error", "action": "fs_edit", "filepath": filepath, "message": f"File '{filepath}' not found."}
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
    Lists all files and directories within a workspace directory.
    """
    try:
        full_path = _resolve_safe_path(directory)
        if not os.path.exists(full_path):
            return {"status": "error", "action": "fs_list", "directory": directory, "message": f"Directory '{directory}' not found."}
        
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
    Deletes a file or directory within the workspace.
    """
    try:
        full_path = _resolve_safe_path(filepath)
        if not os.path.exists(full_path):
            return {"status": "error", "action": "fs_delete", "filepath": filepath, "message": f"Target '{filepath}' not found."}
        
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
