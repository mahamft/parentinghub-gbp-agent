# 🍼 ParentingHub - Automated Google Business Profile (GBP) Social Media Agent

A lightweight, **zero-cost** automated background agent in Python for **[ParentingHub](https://parentinghub.pk/)** (`parentinghub.pk`) that generates and publishes weekly updates to Google Business Profile.

---

## 🌟 Brand Guidelines & Strategy

- **Brand Name**: ParentingHub ([parentinghub.pk](https://parentinghub.pk/))
- **Taglines**:
  - *"Parenting is easier when you don’t do it alone."*
  - *"Discover • Connect • Grow"*
- **Target Audience**: Pakistani expectant & first-time mothers, and modern organized parents looking for trusted guidance and authentic baby care products.
- **Tone of Voice**: Reassuring, welcoming, empathetic, practical, written in an engaging clean Roman Urdu & English blend.
- **Core Content Pillars (Rotated Weekly)**:
  1. 📘 **Learn**: Practical newborn & toddler routines, sleep tips, and child-care guidance.
  2. 🛍️ **Shop**: Highlighting authentic, verified baby essentials (such as Philips Avent & Tommee Tippee anti-colic feeding gear).
  3. 📊 **Track**: Child milestones, feeding, and growth tracking tools.
  4. 🤍 **Connect**: Community discussions and peer support for parents across Pakistan.

---

## 🏗️ Technical Architecture

```
parentinghub-gbp-agent/
├── .env.example          # Environment variables template
├── .env                  # Local secrets (API keys & OAuth credentials)
├── .gitignore            # Git exclusion rules
├── requirements.txt      # Frozen Python dependencies
├── config.py             # Configuration loader, brand metadata & validators
├── generator.py          # Google Gemini AI content engine, pillar rotation & GBP sanitization
├── publisher.py          # GBP OAuth2 refresh token exchange & localPosts API client
├── scheduler.py          # APScheduler weekly automated cron job
├── main.py               # CLI interface & test_run() function
├── tests/
│   └── test_agent.py     # Unit tests for sanitizer, pillars, and payloads
└── data/
    └── post_history.json # Local persistent state for pillar rotation & published logs
```

### Key Technical Rules:
1. **Brain (Content Generation)**: Powered by Google Gemini API (`gemini-1.5-flash`) at temperature `0.7`.
2. **GBP Plain-Text Rule**: Google Business Profile does **NOT** support markdown formatting. The agent includes a dedicated sanitization pipeline that strips markdown asterisks (`**`, `*`), headers (`#`), backticks, and markdown links, replacing them with clean unicode bullets (`•`) and emojis.
3. **Execution (Publisher)**: Uses Google OAuth2 token refresh flow and standard Google My Business API v4 `localPosts` endpoint.
   - **Target Location ID**: `locations/17062544117938448005`
   - **Call To Action**: `LEARN_MORE` pointing to `https://parentinghub.pk/`
4. **Zero-Cost Operation**: Utilizes Google AI Studio's free tier for Gemini API and Google Cloud's free OAuth2 API quotas.

---

## 🚀 Quick Start Guide

### 1. Installation

Clone or open the repository, then set up the virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# Google Gemini API Key (Get for free at https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TEMPERATURE=0.7

# Google Business Profile OAuth2 Credentials
CLIENT_ID=your_client_id.apps.googleusercontent.com
CLIENT_SECRET=your_client_secret
REFRESH_TOKEN=1//04...

# Google Business Profile Target Location
LOCATION_ID=locations/17062544117938448005

# Call To Action Button
CTA_ACTION=LEARN_MORE
CTA_URL=https://parentinghub.pk/

# Weekly Schedule
SCHEDULE_DAY=monday
SCHEDULE_TIME=10:00
```

---

## 🔑 How to Obtain Google API Credentials (Zero Cost)

### A. Google Gemini API Key (Free)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Get API key** -> **Create API key in new project**.
3. Copy the key and paste into `GEMINI_API_KEY` in `.env`.

### B. Google Business Profile OAuth2 Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Go to **APIs & Services** -> **Library**, and enable **Google My Business API** / **Business Profile API**.
4. Go to **APIs & Services** -> **OAuth consent screen**:
   - Select **External**, fill in app name (*ParentingHub Social Agent*), and add your Google account as a test user.
5. Go to **APIs & Services** -> **Credentials**:
   - Click **Create Credentials** -> **OAuth client ID**.
   - Application type: **Web application** or **Desktop application**.
   - Add redirect URI: `https://developers.google.com/oauthplayground` (if using OAuth Playground).
   - Copy `CLIENT_ID` and `CLIENT_SECRET` into `.env`.
6. Generate `REFRESH_TOKEN`:
   - Open [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
   - Click the gear icon (top right) -> Check **"Use your own OAuth credentials"** and enter your `CLIENT_ID` and `CLIENT_SECRET`.
   - In Step 1, enter scope: `https://www.googleapis.com/auth/business.manage` and click **Authorize APIs**.
   - Sign in with the Google Account that manages the ParentingHub GBP listing.
   - In Step 2, click **Exchange authorization code for tokens**.
   - Copy the `refresh_token` and paste it into `REFRESH_TOKEN` in `.env`.

---

## 💻 Usage & CLI Commands

### 🧪 1. Test Mode (`test_run`)
Generates a sample post for the next pillar, sanitizes the formatting, checks GBP compliance, and prints the post and API payload to the console **without publishing**:

```bash
python main.py --test
```

#### Test a specific pillar:
```bash
# Learn pillar (Sleep & Routines)
python main.py --test --pillar learn

# Shop pillar (Authentic Philips Avent & Tommee Tippee Gear)
python main.py --test --pillar shop

# Track pillar (Milestones & Growth)
python main.py --test --pillar track

# Connect pillar (Community & Peer Support)
python main.py --test --pillar connect
```

#### Test a custom topic:
```bash
python main.py --test --pillar shop --topic "Why authentic BPA-free feeding bottles prevent colic"
```

---

### 🚀 2. Immediate Publish
Generates a fresh post and publishes it immediately to Google Business Profile:

```bash
python main.py --publish
```

---

### ⏰ 3. Weekly Background Scheduler Daemon
Runs the agent in the background. It will execute once a week at the exact day and time specified in `.env` (default: **Every Monday at 10:00 AM**):

```bash
python main.py --schedule
# or
python scheduler.py
```

---

### 📊 4. View History & Rotation Status
Inspect the next upcoming content pillar and past post logs:

```bash
python main.py --history
```

---

## 🧪 Running Unit Tests

Run the test suite to verify sanitizer logic, pillar rotation, and payload builder:

```bash
python -m unittest tests/test_agent.py
```

---

## ☁️ Zero-Cost 24/7 Hosting Options

To run this agent completely free in the cloud without keeping your local computer on:

### Option A: GitHub Actions (Recommended)
You can schedule the agent to run weekly via GitHub Actions cron at zero cost:
Create `.github/workflows/weekly_post.yml`:
```yaml
name: Weekly GBP Post
on:
  schedule:
    # Runs every Monday at 05:00 UTC (10:00 AM PKT)
    - cron: '0 5 * * 1'
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py --publish
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          CLIENT_ID: ${{ secrets.CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
          REFRESH_TOKEN: ${{ secrets.REFRESH_TOKEN }}
          LOCATION_ID: ${{ secrets.LOCATION_ID }}
```

### Option B: PythonAnywhere / Render / VPS
- Add a scheduled weekly task in PythonAnywhere free tier pointing to `python main.py --publish`.

---

## 📄 License
MIT License. Built for ParentingHub ([parentinghub.pk](https://parentinghub.pk/)).
