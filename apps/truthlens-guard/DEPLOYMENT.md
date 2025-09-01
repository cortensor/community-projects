# 🚀 TruthLens Deployment Guide

This guide covers deploying TruthLens to Vercel (frontend) and Render (backend) for production use.

## 📋 Prerequisites

- GitHub account
- Vercel account (https://vercel.com)
- Render account (https://render.com)
- Cortensor API key (for production use)

## 🎯 Quick Deployment (Recommended)

### Using Automated Scripts

1. **For Linux/Mac:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. **For Windows:**
   ```cmd
   deploy.bat
   ```

3. **Follow the prompts** to deploy frontend, backend, or both.

### Using GitHub Actions (Fully Automated)

1. **Set up repository secrets** in GitHub:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     ```
     VERCEL_TOKEN=your_vercel_token
     RENDER_API_KEY=your_render_api_key
     VITE_API_URL=https://your-backend.onrender.com/api
     CORTENSOR_API_KEY=your_cortensor_api_key
     CORTENSOR_SUBNET_UID=1
     CORS_ORIGIN=https://your-frontend.vercel.app
     RATE_LIMIT_WINDOW_MS=900000
     RATE_LIMIT_MAX_REQUESTS=1000
     LOG_LEVEL=info
     ```

2. **Push to main branch** - deployment will happen automatically!

## 🔧 Manual Deployment Steps

### Step 1: Deploy Backend to Render

#### Option A: Using Render Dashboard

1. **Create Render Account:**
   - Go to https://render.com and sign up
   - Connect your GitHub account

2. **Create Web Service:**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Set service name: `truthlens-backend`
   - Set runtime: `Node`
   - Set build command: `cd backend && npm install`
   - Set start command: `cd backend && npm start`

3. **Environment Variables:**
   ```
   NODE_ENV=production
   PORT=10000
   CORTENSOR_API_KEY=your_api_key_here
   CORTENSOR_SUBNET_UID=1
   CORS_ORIGIN=https://your-frontend.vercel.app
   RATE_LIMIT_WINDOW_MS=900000
   RATE_LIMIT_MAX_REQUESTS=1000
   LOG_LEVEL=info
   ```

4. **Deploy:** Click "Create Web Service"

#### Option B: Using Render CLI

```bash
# Install Render CLI
npm install -g render-cli

# Login
render login

# Deploy
render deploy
```

### Step 2: Deploy Frontend to Vercel

#### Option A: Using Vercel Dashboard

1. **Create Vercel Account:**
   - Go to https://vercel.com and sign up
   - Connect your GitHub account

2. **Import Project:**
   - Click "New Project"
   - Import your GitHub repository
   - Configure project:
     - **Framework Preset:** Vite
     - **Root Directory:** `./` (leave default)
     - **Build Command:** `npm run build`
     - **Output Directory:** `dist`

3. **Environment Variables:**
   ```
   VITE_API_URL=https://your-backend-url.onrender.com/api
   ```

4. **Deploy:** Click "Deploy"

#### Option B: Using Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Step 3: Post-Deployment Configuration

1. **Update CORS in Backend:**
   - In Render dashboard, go to your backend service
   - Update `CORS_ORIGIN` environment variable to your Vercel frontend URL
   - Example: `https://truthlens.vercel.app`

2. **Update API URL in Frontend:**
   - In Vercel dashboard, go to your frontend project
   - Update `VITE_API_URL` to your Render backend URL
   - Example: `https://truthlens-backend.onrender.com/api`

3. **Test Deployment:**
   ```bash
   # Test health endpoint
   curl https://your-backend.onrender.com/api/health

   # Test frontend
   open https://your-frontend.vercel.app
   ```

## 🔍 Troubleshooting

### Common Issues

1. **CORS Errors:**
   - Ensure `CORS_ORIGIN` in backend matches your frontend URL exactly
   - Include `https://` and no trailing slash

2. **API Connection Issues:**
   - Verify `VITE_API_URL` in frontend matches backend URL
   - Check Render backend logs for errors

3. **Build Failures:**
   - Ensure all dependencies are in `package.json`
   - Check build logs in Vercel/Render dashboards

4. **Environment Variables:**
   - Use the exact variable names as specified
   - Don't include quotes around values unless they contain spaces

### Checking Logs

- **Vercel:** Project dashboard → Functions/Deployments → View Logs
- **Render:** Service dashboard → Logs tab

### Health Checks

```bash
# Backend health
curl https://your-backend.onrender.com/api/health

# API status
curl https://your-backend.onrender.com/api/analysis/status

# Frontend accessibility
curl -I https://your-frontend.vercel.app
```

## 📊 Monitoring & Maintenance

### Vercel Monitoring
- Real-time metrics in dashboard
- Function execution logs
- Performance analytics
- Custom domain setup

### Render Monitoring
- Service metrics and logs
- Auto-scaling configuration
- Database connections (if added)
- Custom domain setup

### Backup Strategy
- Code is backed up in GitHub
- User data is stored in JSON files (consider database migration for production)
- Environment variables are managed in platform dashboards

## 🔒 Security Considerations

1. **API Keys:** Never commit API keys to code
2. **Environment Variables:** Use platform-specific secret management
3. **CORS:** Restrict to your domain only
4. **Rate Limiting:** Configured to prevent abuse
5. **HTTPS:** Automatic on both platforms

## 💰 Cost Estimation

- **Vercel:** Free tier sufficient for most use cases
- **Render:** Free tier for backend (750 hours/month)
- **Cortensor:** Costs depend on API usage

## 🎉 Success Checklist

- [ ] Backend deployed and healthy
- [ ] Frontend deployed and accessible
- [ ] API endpoints responding correctly
- [ ] CORS configured properly
- [ ] Environment variables set
- [ ] Test claims working
- [ ] Custom domain configured (optional)

## 📞 Support

- **Vercel Docs:** https://vercel.com/docs
- **Render Docs:** https://docs.render.com
- **TruthLens Issues:** Create GitHub issue in repository

---

**🎊 Congratulations!** Your TruthLens application is now live and ready to verify claims using decentralized AI!
