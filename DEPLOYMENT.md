# 🚀 Vocalis AI — Production Deployment Guide

This guide covers deploying the **Vocalis AI Backend to AWS** (using AWS App Runner / ECS) and the **Frontend to Vercel**.

---

## 🏗️ Architecture Overview

- **Backend**: FastAPI + Uvicorn + WebSockets running inside an optimized Docker container on AWS (App Runner or ECS Fargate).
- **Frontend**: Next.js 15 App Router deployed on Vercel Edge Network.
- **Communication**: Frontend connects to the AWS Backend via HTTPS REST endpoints and WSS (secure WebSockets).

---

## 1. 🌐 Deploying Backend to AWS

### Option A: AWS App Runner (Fastest & Simplest — Automatic HTTPS + WebSockets)

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
   - **Port**: `8005` (or leave default `$PORT`).
   - **Environment Variables**:
     ```
     HOST=0.0.0.0
     PORT=8005
     DEBUG=false
     GEMINI_API_KEY=<your_gemini_key>
     GROQ_API_KEY=<your_groq_key>
     ```
   - Click **Create & Deploy**.
   - Copy your service URL (e.g. `https://xxxxxx.us-east-1.awsapprunner.com`).

---

### Option B: AWS ECS Fargate + Application Load Balancer

1. **Build & Push to ECR** as shown above.
2. **Create ECS Task Definition**:
   - Image: `<aws_account_id>.dkr.ecr.<region>.amazonaws.com/vocalis-backend:latest`
   - Port Mapping: `8005` TCP
   - Health Check: `curl -f http://localhost:8005/ || exit 1`
3. **Attach to Application Load Balancer (ALB)**:
   - Target Group: Port `8005`, HTTP protocol.
   - Enable stickiness / WebSocket support on the ALB listener.

---

## 2. ▲ Deploying Frontend to Vercel

1. **Import Git Repository**:
   - Go to [vercel.com](https://vercel.com) → **Add New Project** → Select your GitHub repository (`Hridayesh68/jarvis-main`).
   - Set **Root Directory**: `frontend`.

2. **Configure Environment Variables in Vercel**:
   Add the following in the Vercel Project Settings:

   | Variable | Value Example | Description |
   |---|---|---|
   | `NEXT_PUBLIC_BACKEND_URL` | `https://xxxxxx.us-east-1.awsapprunner.com` | Your AWS Backend HTTPS URL |
   | `NEXT_PUBLIC_WS_URL` | `wss://xxxxxx.us-east-1.awsapprunner.com/ws/stream` | Secure WebSocket endpoint |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://nwabikfqyanjydplpqab.supabase.co` | Supabase URL |
   | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `<your_supabase_key>` | Supabase Public Key |

3. **Deploy**:
   - Click **Deploy**. Vercel will automatically build and deploy the Next.js frontend with 0 configuration.

---

## 3. 🐳 Local Docker Testing

To test the entire containerized stack locally before deploying to AWS/Vercel:

```bash
docker compose up --build
```

- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8005`
- **API Docs (Swagger)**: `http://localhost:8005/docs`
