# 🚀 Vocalis AI — Complete Production Deployment Guide

This guide provides the exact step-by-step instructions for deploying **Vocalis AI**:
- **Backend**: FastAPI + Uvicorn + WebSockets running on **AWS (App Runner or Render/Railway/EC2)**.
- **Frontend**: Next.js 15 App Router deployed on **Vercel**.

---

## 🏗️ Architecture Overview

```
Frontend (Vercel Edge)  ──HTTPS REST──>  Backend (AWS / Render / EC2 on Port 8005)
                        ──WSS Stream───>  WebSocket /ws/stream
```

---

## 1. 🌐 Step 1: Deploy Backend (AWS App Runner / Render)

You can deploy the backend using **AWS App Runner** (recommended for AWS) or **Render / Railway** (simplest 1-click container deployment).

### Option A: AWS App Runner (Recommended for AWS)

1. **Push Backend Image to Amazon ECR**:
   ```bash
   # 1. Log in to your Amazon ECR registry
   aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com

   # 2. Create ECR repository (if not already created)
   aws ecr create-repository --repository-name vocalis-backend --region <your-region>

   # 3. Build & Tag the Docker image
   docker build -t vocalis-backend ./backend
   docker tag vocalis-backend:latest <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/vocalis-backend:latest

   # 4. Push to ECR
   docker push <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/vocalis-backend:latest
   ```

2. **Create App Runner Service**:
   - Go to the **AWS App Runner Console** → **Create Service**.
   - **Source**: Select *Container Registry* → *Amazon ECR* → Choose `vocalis-backend:latest`.
   - **Port**: `8005`.
   - **Environment Variables**:
     ```env
     HOST=0.0.0.0
     PORT=8005
     DEBUG=false
     GEMINI_API_KEY=<your_gemini_api_key>
     GROQ_API_KEY=<your_groq_api_key>
     GOOGLE_CLIENT_ID=<your_google_client_id>
     GOOGLE_CLIENT_SECRET=<your_google_client_secret>
     ```
   - Click **Create & Deploy**.
   - Copy your service URL (e.g. `https://xxxxxx.us-east-1.awsapprunner.com`).

---

### Option B: Render / Railway (Zero CLI Alternative)

1. Go to [render.com](https://render.com) or [railway.app](https://railway.app).
2. Click **New Web Service** → Connect your GitHub repo (`TusarGoswami/jarvis-main`).
3. Set **Root Directory**: `backend` (or choose Dockerfile).
4. Set **Port**: `8005`.
5. Add the Environment Variables (`GEMINI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
6. Deploy and copy your backend URL (e.g. `https://vocalis-backend.onrender.com`).

---

## 2. ▲ Step 2: Deploy Frontend to Vercel

1. **Import Git Repository**:
   - Go to [vercel.com](https://vercel.com) → **Add New Project**.
   - Select your GitHub repository (`TusarGoswami/jarvis-main`).
   - In **Root Directory**, click *Edit* and select: `frontend`.

2. **Configure Environment Variables in Vercel**:
   In the **Environment Variables** accordion, add:

   | Variable Name | Value (Example) | Description |
   |:---|:---|:---|
   | `NEXT_PUBLIC_BACKEND_URL` | `https://xxxxxx.us-east-1.awsapprunner.com` | Your live HTTPS backend URL (without trailing slash) |
   | `NEXT_PUBLIC_WS_URL` | `wss://xxxxxx.us-east-1.awsapprunner.com/ws/stream` | Your live WSS WebSocket endpoint |

3. **Deploy**:
   - Click **Deploy**.
   - Vercel will automatically build the Next.js app and assign a live production URL (e.g. `https://jarvis-main-xyz.vercel.app`).

---

## 3. 🔗 Step 3: Configure Google OAuth Redirect URI

Once you have your production Frontend & Backend URLs:

1. Go to the [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**.
2. Click on your **OAuth 2.0 Client ID**.
3. Under **Authorized JavaScript origins**, add:
   - Your frontend URL (e.g. `https://jarvis-main-xyz.vercel.app`)
   - `http://localhost:3000` (for local dev)
4. Under **Authorized redirect URIs**, add:
   - `<YOUR_BACKEND_URL>/api/auth/google/callback` (e.g. `https://xxxxxx.us-east-1.awsapprunner.com/api/auth/google/callback`)
   - `http://localhost:8005/api/auth/google/callback`
5. Click **Save**.

---

## 4. 🐳 Step 4: Local Full-Stack Docker Verification (Optional)

You can run both containers simultaneously locally to verify production readiness:

```bash
docker compose up --build
```
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8005](http://localhost:8005)
- **Interactive Swagger Docs**: [http://localhost:8005/docs](http://localhost:8005/docs)
