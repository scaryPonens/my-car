# Deployment Guide

This guide covers deploying Smart Car VA to Railway and other platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Telegram Bot Setup](#telegram-bot-setup)
4. [Smartcar Setup](#smartcar-setup)
5. [Railway Deployment](#railway-deployment)
6. [Alternative Deployments](#alternative-deployments)
7. [Post-Deployment](#post-deployment)

## Prerequisites

Before deploying, ensure you have:

- [ ] GitHub account (for deployment)
- [ ] Supabase account
- [ ] Telegram account
- [ ] Smartcar developer account
- [ ] OpenAI or Anthropic API key
- [ ] Railway account (or alternative hosting)

## Supabase Setup

### 1. Create a New Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Enter project name (e.g., "smart-car-va")
4. Set a strong database password
5. Choose a region close to your users
6. Wait for the project to be created

### 2. Run Database Schema

1. Go to **SQL Editor** in your Supabase dashboard
2. Create a new query
3. Copy the contents of `database/schema.sql`
4. Run the query
5. Verify tables were created in **Table Editor**

### 3. Get API Keys

1. Go to **Project Settings** > **API**
2. Copy these values:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role** key → `SUPABASE_SERVICE_KEY` (keep this secret!)

## Telegram Bot Setup

### 1. Create a Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts:
   - Enter a name for your bot (e.g., "Smart Car Assistant")
   - Enter a username (must end in "bot", e.g., "my_smart_car_bot")
4. Copy the API token → `TELEGRAM_BOT_TOKEN`

### 2. Configure Bot Settings (Optional)

Send these commands to @BotFather:

```
/setdescription - Set bot description
/setabouttext - Set about text
/setuserpic - Set bot profile picture
/setcommands - Set command menu
```

For `/setcommands`, use:
```
start - Welcome message
connect - Connect a vehicle
vehicles - List your vehicles
status - Get vehicle status
help - Show help
```

## Smartcar Setup

### 1. Create Developer Account

1. Go to [dashboard.smartcar.com](https://dashboard.smartcar.com)
2. Sign up for a developer account
3. Verify your email

### 2. Create an Application

1. Click "Create Application"
2. Enter application name
3. Set the following:
   - **Redirect URI**: Your callback URL (see below)
   - For development: `http://localhost:8000/callback`
   - For production: `https://your-app.railway.app/callback`

### 3. Get Credentials

From your application dashboard:
- **Client ID** → `SMARTCAR_CLIENT_ID`
- **Client Secret** → `SMARTCAR_CLIENT_SECRET`

### 4. Configure Permissions

In your application settings, enable these scopes:
- `read_vehicle_info`
- `read_location`
- `read_odometer`
- `read_fuel`
- `read_battery`
- `read_tires`
- `control_security`

## Railway Deployment

### 1. Prepare Repository

1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

### 2. Deploy to Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will detect the Python project automatically

### 3. Configure Environment Variables

In Railway dashboard:

1. Go to your project
2. Click on the service
3. Go to **Variables** tab
4. Add all required environment variables:

```env
TELEGRAM_BOT_TOKEN=your_token
SMARTCAR_CLIENT_ID=your_client_id
SMARTCAR_CLIENT_SECRET=your_client_secret
SMARTCAR_REDIRECT_URI=https://your-app.railway.app/callback
SMARTCAR_MODE=simulated
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=generate-a-random-string
```

### 4. Get Your Domain

1. Go to **Settings** > **Networking**
2. Click "Generate Domain"
3. Copy your domain (e.g., `your-app.railway.app`)

### 5. Update Smartcar Redirect URI

1. Go to Smartcar dashboard
2. Update Redirect URI to: `https://your-app.railway.app/callback`
3. Update `SMARTCAR_REDIRECT_URI` in Railway

### 6. Deploy

Railway will automatically deploy when you push to main. You can also:
- Click "Deploy" to trigger a manual deployment
- View logs in the "Deployments" tab

## Alternative Deployments

### Heroku

1. Create a Heroku app
2. Add Python buildpack
3. Set environment variables
4. Deploy via Git or GitHub

### Docker

Build and run with Docker:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t smart-car-va .
docker run -p 8000:8000 --env-file .env smart-car-va
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

Use ngrok for local OAuth callback testing:
```bash
ngrok http 8000
# Use the ngrok URL as your SMARTCAR_REDIRECT_URI
```

## Post-Deployment

### 1. Verify Deployment

1. Check health endpoint: `https://your-app.railway.app/health`
2. Should return: `{"status": "healthy", "bot_running": true, ...}`

### 2. Test the Bot

1. Open Telegram
2. Find your bot by username
3. Send `/start`
4. Try `/connect` to link a vehicle

### 3. Switch to Live Mode

Once testing is complete:

1. Update `SMARTCAR_MODE=live` in Railway
2. Redeploy
3. Connect real vehicles

### 4. Monitoring

- **Railway Logs**: View in Deployments > Logs
- **Supabase**: Monitor in Dashboard > Logs
- **Custom Logging**: Adjust `LOG_LEVEL` as needed

## Troubleshooting

### Bot Not Responding

1. Check Railway logs for errors
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Ensure bot is not blocked or restricted

### OAuth Callback Fails

1. Verify `SMARTCAR_REDIRECT_URI` matches exactly in both places
2. Check that the redirect URI uses HTTPS in production
3. Review Railway logs for detailed errors

### Database Connection Issues

1. Verify Supabase credentials
2. Check that RLS policies are set up correctly
3. Ensure service key is used for backend operations

### Vehicle Data Not Available

1. Check vehicle permissions in Smartcar dashboard
2. Verify access token is valid (check logs)
3. Some data may not be available for all vehicles

## Security Checklist

- [ ] All secrets are in environment variables (not in code)
- [ ] `SECRET_KEY` is a strong random string
- [ ] `SUPABASE_SERVICE_KEY` is never exposed to clients
- [ ] HTTPS is used for all production URLs
- [ ] `.env` file is in `.gitignore`
- [ ] RLS policies are enabled in Supabase
