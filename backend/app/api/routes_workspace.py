import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.core.fs_tools import fs_list, fs_read, fs_write, fs_delete

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

class FileWriteRequest(BaseModel):
    filepath: str
    content: str

@router.get("/files")
def list_workspace_files(directory: str = Query(default=".")):
    res = fs_list(directory)
    if res.get("status") != "success":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.get("/file")
def read_workspace_file(filepath: str = Query(...)):
    res = fs_read(filepath)
    if res.get("status") != "success":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@router.post("/file")
def write_workspace_file(req: FileWriteRequest):
    res = fs_write(req.filepath, req.content)
    if res.get("status") != "success":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.delete("/file")
def delete_workspace_file(filepath: str = Query(...)):
    res = fs_delete(filepath)
    if res.get("status") != "success":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res
