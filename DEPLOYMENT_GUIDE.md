# Deployment Guide - Bet-That Dashboard

## What is Deployment?

**Deployment** means putting your app on the internet so others can access it.

### Current State
- 🏠 Runs on your computer: `http://localhost:5001`
- 👤 Only you can access it
- 💻 Stops when you close your laptop

### After Deployment
- 🌐 Runs on a web server (cloud)
- 👥 Anyone with the URL can access it
- ⏰ Available 24/7

---

## Recommended: Deploy to Render (Easiest & Free)

**Why Render?**
- ✅ Free tier (no credit card required)
- ✅ Auto-deploys from GitHub
- ✅ Easy setup (~10 minutes)
- ✅ Modern and reliable
- ✅ Built-in SSL (HTTPS)

### Step-by-Step: Deploy to Render

#### 1. Prepare Your App for Deployment

First, we need to create a few configuration files:

##### A. Create `Procfile` (tells Render how to run your app)

```bash
# Create file at project root
web: gunicorn dashboard.app:app
```

##### B. Update `requirements.txt` (add production server)

Add this line to your requirements.txt:
```
gunicorn==21.2.0
```

##### C. Create `render.yaml` (optional - Render configuration)

```yaml
services:
  - type: web
    name: bet-that-dashboard
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn dashboard.app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
```

##### D. Update `dashboard/app.py` (production settings)

Make sure your Flask app can run in production:
```python
if __name__ == '__main__':
    # Development mode
    app.run(host='0.0.0.0', port=5001, debug=True)
else:
    # Production mode (when run by gunicorn)
    # No need to call app.run()
    pass
```

#### 2. Push to GitHub

```bash
# Make sure all changes are committed
git add .
git commit -m "Prepare for deployment to Render"
git push origin main
```

#### 3. Deploy on Render

1. **Go to Render:** https://render.com
2. **Sign up** using your GitHub account
3. **Click "New +"** → **"Web Service"**
4. **Connect your GitHub repository:** `Bet-That_Proof-of-Concept`
5. **Configure the service:**
   - **Name:** `bet-that-dashboard`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn dashboard.app:app`
   - **Plan:** `Free`
6. **Click "Create Web Service"**

#### 4. Wait for Deployment (2-5 minutes)

Render will:
- Install your dependencies
- Start your Flask app
- Give you a URL like: `https://bet-that-dashboard.onrender.com`

#### 5. Access Your Deployed App! 🎉

Visit your URL: `https://bet-that-dashboard.onrender.com`

---

## Alternative: Deploy to Heroku

### Step-by-Step: Deploy to Heroku

#### 1. Install Heroku CLI

```bash
# macOS (using Homebrew)
brew install heroku/brew/heroku

# Verify installation
heroku --version
```

#### 2. Prepare Your App

##### A. Create `Procfile`
```
web: gunicorn dashboard.app:app
```

##### B. Update `requirements.txt`
Add:
```
gunicorn==21.2.0
```

##### C. Create `runtime.txt` (specify Python version)
```
python-3.9.18
```

#### 3. Create Heroku App

```bash
# Login to Heroku
heroku login

# Create app
heroku create bet-that-dashboard

# This gives you: https://bet-that-dashboard.herokuapp.com
```

#### 4. Deploy

```bash
# Push to Heroku
git push heroku main

# Open your app
heroku open
```

#### 5. View Logs (if needed)

```bash
heroku logs --tail
```

---

## Alternative: Deploy to PythonAnywhere

### Step-by-Step: Deploy to PythonAnywhere

#### 1. Sign Up

1. Go to: https://www.pythonanywhere.com
2. Create a free account
3. Choose username (becomes part of your URL)

#### 2. Upload Your Code

**Option A: Use Git**
```bash
# In PythonAnywhere Bash console
git clone https://github.com/VatoCodes/Bet-That_Proof-of-Concept.git
cd Bet-That_Proof-of-Concept
```

**Option B: Upload Files**
- Use Files tab to upload your project

#### 3. Create Virtual Environment

```bash
# In PythonAnywhere Bash console
mkvirtualenv --python=/usr/bin/python3.9 bet-that-env
pip install -r requirements.txt
```

#### 4. Configure Web App

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Flask**
4. Set Python version: **3.9**
5. Configure WSGI file to point to your app

Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:
```python
import sys
path = '/home/yourusername/Bet-That_Proof-of-Concept'
if path not in sys.path:
    sys.path.append(path)

from dashboard.app import app as application
```

#### 5. Reload Web App

Click **Reload** button

Your app will be at: `https://yourusername.pythonanywhere.com`

---

## Important Notes for Deployment

### 1. Database Considerations

Your app currently uses SQLite (local database file). For production:

**Current (Development):**
```python
database_path = 'dashboard/data/nfl_betting.db'
```

**Production Options:**

**A. Keep SQLite (Simple)**
- Works for small apps
- No changes needed
- Data stored on server disk

**B. Upgrade to PostgreSQL (Recommended for Production)**
- Better for concurrent users
- More reliable
- Available on Render/Heroku for free

**Example PostgreSQL setup:**
```python
import os
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///dashboard/data/nfl_betting.db')
```

### 2. Environment Variables

For sensitive data (API keys, etc.):

**Don't do this:**
```python
API_KEY = "secret-key-123"  # BAD - visible in code
```

**Do this:**
```python
import os
API_KEY = os.environ.get('API_KEY')  # GOOD - stored securely
```

Set environment variables in Render:
- Dashboard → Environment tab → Add Environment Variable

### 3. Data Updates

Your scraping scripts won't run automatically on deployment. Options:

**A. Render Cron Jobs (Paid plans)**
Schedule scripts to run automatically

**B. GitHub Actions (Free)**
Run scraper on GitHub, update database

**C. External Scheduler**
Use service like Heroku Scheduler or Railway

**D. Manual Updates**
Run scraper locally, upload database

### 4. Static Files

Your CSS/JS files should work automatically, but verify:
```python
# In app.py
app.static_folder = 'static'
app.template_folder = 'templates'
```

---

## Quick Start: Deploy Now!

Want to deploy right now? Here's the fastest path:

### Option 1: Render (Recommended - 10 minutes)

```bash
# 1. Add gunicorn to requirements
echo "gunicorn==21.2.0" >> requirements.txt

# 2. Create Procfile
echo "web: gunicorn dashboard.app:app" > Procfile

# 3. Commit and push
git add .
git commit -m "Add deployment configuration for Render"
git push origin main

# 4. Go to render.com, sign up with GitHub, connect repo, deploy!
```

### Option 2: Heroku (15 minutes)

```bash
# 1. Install Heroku CLI
brew install heroku/brew/heroku

# 2. Add files
echo "gunicorn==21.2.0" >> requirements.txt
echo "web: gunicorn dashboard.app:app" > Procfile
echo "python-3.9.18" > runtime.txt

# 3. Deploy
git add .
git commit -m "Add deployment configuration for Heroku"
heroku login
heroku create bet-that-dashboard
git push heroku main
heroku open
```

---

## Troubleshooting

### Common Issues

#### 1. "Application Error" after deployment

**Check logs:**
```bash
# Render: View logs in dashboard
# Heroku: heroku logs --tail
```

**Common causes:**
- Missing dependencies in requirements.txt
- Database path issues
- Port configuration

#### 2. Static files not loading

**Check Flask configuration:**
```python
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
```

#### 3. Database not found

**Update database path for production:**
```python
import os
if os.environ.get('PRODUCTION'):
    db_path = '/opt/render/project/src/dashboard/data/nfl_betting.db'
else:
    db_path = 'dashboard/data/nfl_betting.db'
```

#### 4. Port issues

**Use environment variable for port:**
```python
port = int(os.environ.get('PORT', 5001))
app.run(host='0.0.0.0', port=port)
```

---

## Cost Comparison

| Platform | Free Tier | Paid Plans | Best For |
|----------|-----------|------------|----------|
| **Render** | ✅ Yes (Limited hours) | From $7/mo | Modern apps, easy deploy |
| **Heroku** | ⚠️ No longer free | From $5/mo | Established platform |
| **PythonAnywhere** | ✅ Yes (Limited) | From $5/mo | Python-specific apps |
| **Railway** | ✅ $5 free credit | From $5/mo | Modern, auto-scaling |
| **Fly.io** | ✅ Generous free tier | From $0/mo | Edge deployment |
| **AWS** | ✅ 1 year free | Pay as you go | Enterprise, scalability |
| **DigitalOcean** | ❌ No | From $4/mo | Full control, droplets |

---

## Security Checklist Before Deploying

- [ ] Remove or secure any API keys
- [ ] Set `DEBUG = False` in production
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS (automatic on Render/Heroku)
- [ ] Add authentication if needed (protect betting data)
- [ ] Review what data is public vs private
- [ ] Set up error monitoring (optional)

---

## Next Steps After Deployment

1. **Share Your URL** 🔗
   - Give the URL to friends to test
   - Share on social media (if public)

2. **Monitor Performance** 📊
   - Check response times
   - Monitor uptime
   - Review error logs

3. **Add Custom Domain** (Optional) 🌐
   - Buy domain (e.g., from Namecheap)
   - Point to your Render/Heroku app
   - Example: `https://bet-that-analytics.com`

4. **Set Up Analytics** (Optional) 📈
   - Add Google Analytics
   - Track user behavior
   - Monitor popular features

5. **Continuous Deployment** 🚀
   - Every push to `main` auto-deploys
   - Already set up if using Render with GitHub

---

## Questions?

**Q: Will my app be available 24/7?**
A: On free tiers, apps may "sleep" after inactivity. First request wakes them up (takes 30s). Paid plans = always on.

**Q: Can I update my app after deploying?**
A: Yes! Just push to GitHub. Render/Heroku auto-deploys.

**Q: How do I update my database?**
A: Either run scraper on server, or upload updated database file.

**Q: Is it secure?**
A: Yes, if you follow security checklist. Use HTTPS, hide secrets, disable DEBUG.

**Q: How much traffic can it handle?**
A: Free tiers: ~100 concurrent users. Paid plans: thousands+.

---

## Ready to Deploy?

I can help you deploy right now! Just let me know which platform you'd like to use:

1. **Render** (easiest, recommended)
2. **Heroku** (popular, well-documented)
3. **PythonAnywhere** (Python-specific)
4. **Other** (tell me your preference)

I'll walk you through step by step! 🚀
