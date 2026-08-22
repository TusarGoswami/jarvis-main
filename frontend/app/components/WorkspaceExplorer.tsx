"use client";

import React, { useState, useEffect } from "react";
import { Folder, FileText, RefreshCw, Eye, Code } from "lucide-react";
import { getApiUrl } from "../lib/api";

interface WorkspaceEntry {
  name: string;
  is_directory: boolean;
  size_bytes: number;
}

export function WorkspaceExplorer() {
  const [files, setFiles] = useState<WorkspaceEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(getApiUrl("/api/workspace/files"));
      if (res.ok) {
        const data = await res.json();
        setFiles(data.entries || []);
      }
    } catch {
      // Offline fallback
    } finally {
      setLoading(false);
    }
  };

  const handleOpenFile = async (filename: string) => {
    try {
      const res = await fetch(getApiUrl(`/api/workspace/file?filepath=${encodeURIComponent(filename)}`));
      if (res.ok) {
        const data = await res.json();
        setSelectedFile(filename);
        setFileContent(data.content || "");
      }
    } catch {
      // Error handling
    }
  };

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const res = await fetch(getApiUrl("/api/workspace/files"));
        if (res.ok && isMounted) {
          const data = await res.json();
          setFiles(data.entries || []);
        }
      } catch {
        // Fallback
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="bg-black/40 border border-white/10 rounded-2xl p-4 backdrop-blur-xl flex flex-col h-full shadow-2xl">
      <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
        <div className="flex items-center gap-2">
          <Folder className="w-5 h-5 text-cyan-400" />
          <span className="text-sm font-semibold tracking-wider text-white uppercase">
            Workspace Artifacts ({files.length})
          </span>
        </div>
        <button
          onClick={fetchFiles}
          disabled={loading}
          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-colors"
          title="Refresh workspace"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 overflow-hidden min-h-[220px]">
        {/* File List */}
        <div className="overflow-y-auto space-y-1.5 pr-1 max-h-[220px]">
          {files.length === 0 ? (
            <div className="text-center py-8 text-white/40 text-xs italic">
              No files created yet. Ask Vocalis to create, edit, or run scripts!
            </div>
          ) : (
            files.map((file) => (
              <button
                key={file.name}
                onClick={() => handleOpenFile(file.name)}
                className={`w-full flex items-center justify-between p-2 rounded-lg text-left text-xs transition-all border ${
                  selectedFile === file.name
                    ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-300"
                    : "bg-white/5 border-white/5 text-white/70 hover:bg-white/10 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {file.is_directory ? (
                    <Folder className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  ) : (
                    <FileText className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  )}
                  <span className="truncate">{file.name}</span>
                </div>
                <span className="text-[10px] text-white/40 font-mono">
                  {file.size_bytes > 0 ? `${file.size_bytes}B` : "dir"}
                </span>
              </button>
            ))
          )}
        </div>

        {/* File Content Preview */}
        <div className="bg-black/60 border border-white/10 rounded-xl p-3 flex flex-col overflow-hidden max-h-[220px]">
          {selectedFile ? (
            <>
              <div className="flex items-center justify-between pb-2 border-b border-white/10 mb-2">
                <div className="flex items-center gap-1.5 truncate">
                  <Code className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-xs font-mono text-cyan-300 truncate">{selectedFile}</span>
                </div>
              </div>
              <pre className="flex-1 overflow-auto text-[11px] font-mono text-white/80 whitespace-pre-wrap leading-relaxed">
                {fileContent}
              </pre>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-white/30 text-xs">
              <Eye className="w-6 h-6 mb-1 text-white/20" />
              Select a file to inspect its content
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
