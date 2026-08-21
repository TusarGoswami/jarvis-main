import subprocess
import sys
import os
import time

def start():
    print("=" * 60)
    print("  INITIALIZING VOCALIS AI MULTIMODAL AGENTIC OS")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    # Clean port bindings to avoid Address Already In Use / lock conflicts
    import re
    for port in [3000, 8005]:
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            pids = set()
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 5:
                        pids.add(parts[-1])
            for pid in pids:
                print(f"Port {port} is occupied by PID {pid}. Terminating process...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        except Exception:
            pass


    # Auto-detect virtual environment python executable
    python_exe = sys.executable
    venv_candidates = [
        os.path.join(backend_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(base_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(backend_dir, "venv", "Scripts", "python.exe"),
        os.path.join(base_dir, "venv", "Scripts", "python.exe"),
    ]
    for candidate in venv_candidates:
        if os.path.exists(candidate):
            python_exe = candidate
            print(f"Using virtual environment Python: {python_exe}")
            break

    print("[1/2] Starting FastAPI Backend on http://127.0.0.1:8005 ...")
    backend_proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn", "app.main:app", 
            "--host", "127.0.0.1", "--port", "8005", "--reload",
            "--reload-dir", "app"
        ],
        cwd=backend_dir
    )

    time.sleep(2)

    print("[2/2] Starting Next.js Frontend on http://localhost:3000 ...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True
    )

    print("\nVocalis AI is running!")
    print("   - HUD Interface: http://localhost:3000")
    print("   - Backend Docs:  http://127.0.0.1:8005/docs")
    print("   - WebSocket:     ws://127.0.0.1:8005/ws/stream\n")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping Vocalis AI services...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    start()
