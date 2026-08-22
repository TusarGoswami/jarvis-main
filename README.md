# <p align="center">🎙️ Vocalis AI — Multimodal Voice & Vision Agentic OS 👁️</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776ab?style=for-the-badge&logo=python&logoColor=yellow" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-Modern_Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Package_Manager-uv-de5fe9?style=for-the-badge" alt="uv">
  <img src="https://img.shields.io/badge/Frontend-Next.js_15-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/Google_Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/Evals-20_Test_Harness-10b981?style=for-the-badge" alt="Evals">
</p>

<p align="center">
  <b>A State-of-the-Art Multimodal Operating System uniting Real-Time Vision, Multilingual Neural Speech, Agentic Tool Execution, and Safety Guardrails.</b>
</p>

---

## 🌟 What is Vocalis AI?

**Vocalis AI** is a next-generation desktop agent designed to fulfill the 2026 AI Hackathon mandate: *"Build something that couldn't have existed two years ago."*

Unlike legacy keyword-based assistants that only wrap chat prompts, **Vocalis AI** seamlessly bridges **Vision (live screen snapshotting & visual grounding)** and **Voice (multilingual STT & Edge TTS in English, Hindi, and Bengali)** with autonomous desktop tool orchestration, hybrid RAG memory, and safety guardrails.

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Frontend [Next.js Futuristic HUD]
        ARC[Interactive Arc Reactor Canvas]
        MIC[Web Audio Mic Input]
        VISION[Screen Capture & Vision Stream]
        TELE[Live Hardware Gauges]
        FEED[Action Stream & Guardrails Gate]
        EVAL_MODAL[20-Case Eval Viewer]
    end

    subgraph Backend [FastAPI + uv Backend (Port 8000)]
        WS[WebSocket Stream /ws/stream]
        REST[REST APIs: /api/agent & /api/system]
        ORCH[Agentic Orchestrator]
        RAG[Grounded Memory Store]
        GUARD[Confidence & Guardrail Verifier]
        EVAL_SUITE[Automated 20-Test Benchmark]
        TOOLS[System Tools: Windows, App Launcher, YouTube, Web]
    end

    MIC & VISION & ARC <-->|WebSocket / REST| WS & REST
    WS & REST --> ORCH
    ORCH --> RAG
    ORCH --> GUARD
    ORCH --> TOOLS
    ORCH --> EVAL_SUITE
```

---

## ✨ Key Capabilities

1. **👁️ Real-time Multimodal Vision**: Inspects your active screen or camera feed in real time to explain code, debug errors, and summarize open documents using Gemini 2.0 Flash.
2. **🗣️ Multilingual Neural Speech**: Fluently comprehends and speaks English, हिन्दी (Devanagari script), and বাংলা (Bengali script) using Edge Neural voices.
3. **🛡️ Confidence & Safety Guardrails**: Displays visible confidence percentages (0–100%) and enforces human-in-the-loop authorization gates for sensitive or destructive operations.
4. **📊 Real-time Telemetry Dashboard**: Live hardware monitoring showing CPU load, RAM memory distribution, storage partition capacity, and upstream/downstream network throughput.
5. **⚡ Sub-Millisecond Deterministic Dispatch**: Instant local execution (< 2ms) for desktop apps, window switching, YouTube playback, and system queries.
6. **🏆 20-Case Automated Eval Harness**: Built-in benchmark suite directly accessible via CLI (`uv run pytest evals/test_evals.py`) and visually in the HUD.

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- **Python 3.12+**
- **uv** (Astral package manager)
- **Node.js 20+** & **npm**

### 2. Backend Setup (uv)
```bash
# Sync all dependencies via uv
uv sync

# Run the 20-case evaluation suite
uv run pytest evals/test_evals.py -v
```

### 3. Frontend Setup (Next.js)
```bash
cd frontend
npm install
npm run build
```

### 4. Launch Vocalis AI (Unified Runner)
```bash
# From project root
python run_vocalis.py
```
- **HUD Interface**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **WebSocket Endpoint**: `ws://127.0.0.1:8000/ws/stream`

---

## 📧 Secure Email Dispatch (Gmail API / OAuth)

Vocalis AI includes real-world, hardened email sending capabilities with zero compromise on safety:
- **OAuth Scope Minimization**: Restricted to `https://www.googleapis.com/auth/gmail.send` only (never requests inbox/read access).
- **Encrypted Token at Rest**: OAuth refresh tokens and secrets are encrypted with Fernet keys via the internal Vault before being stored in `~/.jarvis/gmail_token.json`.
- **Guardrails Confirmation Gate**: Email actions require explicit human confirmation before sending (`CONFIRM ACTION: Send Email`).
- **Rate Limiting**: Sliding-window rate limiter prevents spam or runaway loops (max 5 sends/minute).
- **Sanitized Logging**: All API error traces are redacted of sensitive keys/tokens.

---

## 📅 Google Calendar & ⏰ Local Reminders

Vocalis AI integrates Google Calendar scheduling and local task reminders:

### 1. Google Calendar Integration
- **Unified OAuth Flow**: Extends the existing Google OAuth setup with `calendar.events` and `calendar.readonly` scopes.
- **Read-Only Safety**: Inspecting schedules ("What's on my calendar today?") executes safely without blocking.
- **Mutating Action Guardrails**: Creating or canceling calendar events triggers a formatted confirmation card requiring explicit human confirmation.
- **Flexible Natural Language Parsing**: Handles queries like *"Schedule a meeting with John tomorrow at 3pm for 30 minutes"* and defaults missing durations to 30 minutes.

### 2. Local Reminders & Task Management
- **Local SQLite Engine**: Stores task reminders in `jarvis.db` (`reminders` table) with full persistence across backend restarts.
- **APScheduler Background Trigger**: Dispatches reminders at their designated timestamp.
- **Activity Feed & Vocal Feedback**: Alerts the user both visually and vocally via the unified TTS pipeline.
- **Natural Time Parsing**: Resolves relative expressions (*"in 20 minutes"*, *"tomorrow at 9am"*, *"at 5pm"*) with zero external API dependency.

### One-Time OAuth Setup (Gmail + Calendar)
1. Open [Google Cloud Console](https://console.cloud.google.com) and enable **Gmail API** and **Google Calendar API**.
2. Run the unified setup script:
```bash
python backend/setup_gmail_auth.py credentials.json
```
A browser prompt will request approval for the combined Gmail & Calendar scopes and securely save the encrypted refresh token.

---

## ⚙️ Voice & Text System Control (Brightness, Settings, Wi-Fi)

Vocalis AI provides native Windows operating system control directly via voice or text without requiring guardrail confirmation:

- **Display Brightness Control**:
  - Sets absolute percentage (`0-100%`) or relative adjustments (`+10%`, `-10%`).
  - Clamps out-of-range values and gracefully handles unsupported virtual/external displays.
  - Examples: *"Increase brightness"*, *"Decrease brightness by 20"*, *"Set brightness to 70"*, *"Make the screen brighter"*.
- **Windows Settings Navigation**:
  - Uses `ms-settings:` URIs to open specific settings categories directly.
  - Examples: *"Open settings"*, *"Open display settings"*, *"Open wifi settings"*, *"Open bluetooth settings"*, *"Open sound settings"*.
- **Wi-Fi Adapter Toggle**:
  - Toggles interface state using Windows `netsh` interface control.
  - Returns friendly no-op if Wi-Fi is already in target state.
  - Gracefully catches non-elevated permissions and informs the user to run as Administrator without crashing.
  - Examples: *"Turn on wifi"*, *"Turn off wifi"*, *"Disable wireless"*, *"Enable wifi"*.

---

## 🧪 Hackathon Rubric Alignment

| Criterion | Vocalis AI Implementation |
| :--- | :--- |
| **Originality (25%)** | Real-time Vision + Multilingual Voice fused with autonomous desktop tools. Could not exist in 2023. |
| **Technical Depth (25%)** | Non-trivial orchestration, hybrid RAG grounding, confidence thresholding, and a 20-case eval harness. |
| **Working Demo (20%)** | Fully functioning Next.js client connected via full-duplex WebSockets to a non-blocking FastAPI backend. |
| **Problem Clarity (15%)** | Built for developers and power users needing hands-free screen understanding, automation, and system control. |
| **Failure Awareness (15%)** | Clear guardrail refusals, confidence scoring, and offline fallback degradation. |
