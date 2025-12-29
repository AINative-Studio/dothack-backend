# Railway Environment Variables - dothack-backend

## 🔐 Production Credentials for Railway

Copy these environment variables to your Railway dashboard:
**Railway Dashboard → Your Project → python-api Service → Variables**

---

### ✅ REQUIRED CREDENTIALS

```bash
# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
API_VERSION=v1

# Server
HOST=0.0.0.0
PORT=8000

# CORS (Update with your actual frontend domain)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ZeroDB Configuration
ZERODB_API_KEY=9khD3l6lpI9O7AwVOkxdl5ZOQP0upsu0vIsiQbLCUGk
ZERODB_PROJECT_ID=dothack-hackathon-platform
ZERODB_BASE_URL=https://api.ainative.studio
ZERODB_TIMEOUT=30.0

# Security - Generated for you
SECRET_KEY=aT2MsAOwyb3EjPDq1koCicfPtaQwChBBlC8E1fgEU1c
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI (for embeddings) - ADD YOUR KEY
OPENAI_API_KEY=your-openai-api-key-here
```

---

### 📦 OPTIONAL (External Services)

```bash
# Email Service (Resend)
RESEND_API_URL=https://api.resend.com
RESEND_API_KEY=your-resend-key

# Go WebSocket Services
GO_EVENT_STREAM_PORT=9000
GO_ANALYTICS_PORT=9001

# CRM & Enrichment (Optional)
HUBSPOT_API_URL=https://api.hubapi.com
HUBSPOT_API_KEY=placeholder
CLEARBIT_API_URL=https://person.clearbit.com
CLEARBIT_API_KEY=placeholder
APOLLO_API_URL=https://api.apollo.io
APOLLO_API_KEY=placeholder
```

---

## 📋 Quick Setup Instructions

### 1. Copy Variables to Railway

1. Go to https://railway.app
2. Select your dothack project
3. Click on **python-api** service
4. Go to **Variables** tab
5. Click **+ New Variable**
6. Paste each variable from above
7. Click **Deploy**

### 2. Verify Deployment

After deployment completes:

```bash
# Test health endpoint
curl https://your-railway-url.railway.app/health

# View API docs
open https://your-railway-url.railway.app/v1/docs
```

---

## 🔑 Your Project Details

**ZeroDB Project ID**: `dothack-hackathon-platform`
**SECRET_KEY** (Generated): `aT2MsAOwyb3EjPDq1koCicfPtaQwChBBlC8E1fgEU1c`

### ⚠️ IMPORTANT

1. **Replace** `OPENAI_API_KEY` with your actual OpenAI API key
2. **Update** `ALLOWED_ORIGINS` with your actual frontend domain
3. **Keep** the `SECRET_KEY` secure - don't commit to git
4. **Never** share these credentials publicly

---

## 🚀 Deploy Command

```bash
# From your local machine
railway login
railway link <your-project-id>
railway up --service python-api
```

---

**Generated**: 2025-12-29
**For**: dothack-backend Railway deployment
