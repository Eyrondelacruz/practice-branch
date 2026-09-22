# Smart School ID Attendance Scanner

A real-time QR-based attendance system with rotating 15-second tokens, webcam scanning, and automated notifications.

## Architecture

```
attendance checker/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── .env                       # Configuration (copy & fill in)
├── supabase_migration.sql     # Run in Supabase SQL Editor
├── setup.bat                  # Windows one-click setup
├── app/
│   ├── database.py            # Supabase + SQLite dual backend
│   ├── tokens.py              # 15-second HMAC rotating tokens
│   ├── notifications.py       # Twilio SMS + Gmail SMTP
│   ├── ws_manager.py          # WebSocket broadcast manager
│   └── routers/
│       ├── scan.py            # POST /api/scan, WS /ws/scan
│       ├── qr.py              # GET /api/qr/{id}, /api/qr-payload/{id}
│       ├── camera.py          # MJPEG stream + OpenCV QR detection
│       └── users.py           # User CRUD
├── static/
│   └── index.html             # Full dashboard UI
└── uploads/                   # Student/teacher profile photos
```

## Quick Start

### 1. Install dependencies

```bash
# Windows
setup.bat

# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Windows note:** `pyzbar` requires the ZBar DLL.  
> Download `zbar-x64.zip` from https://github.com/NaturalHistoryMuseum/pyzbar/releases  
> and place `libzbar-64.dll` in your PATH or project root.

### 2. Configure `.env`

```env
# Minimum required for SQLite mode (no Supabase needed):
MASTER_SECRET=your_random_32_char_secret

# Optional — Supabase (replaces SQLite):
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_role_key

# Optional — Notifications:
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_FROM_NUMBER=+1234567890
GMAIL_USER=school@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 3. Run

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000**

## Database

### SQLite (default — zero config)
- Auto-created as `attendance.db` on first run
- Demo users seeded automatically: `STU001`, `STU002`, `TCH001`

### Supabase
1. Run `supabase_migration.sql` in Supabase SQL Editor
2. Generate secret keys for each user:
   ```bash
   python -c "
   import hmac, hashlib, base64, os
   master = 'your_MASTER_SECRET'
   for cid in ['STU001','STU002','TCH001']:
       key = base64.b32encode(hmac.new(master.encode(), cid.encode(), hashlib.sha256).digest()).decode()
       print(f'{cid}: {key}')
   "
   ```
3. Update the `secret_key` values in the migration INSERT statements

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scan` | Validate QR payload, log attendance |
| GET | `/api/logs/today` | Today's attendance records |
| WS | `/ws/scan` | Real-time scan event stream |
| GET | `/api/qr/{id}` | Generate QR code PNG |
| GET | `/api/qr-payload/{id}` | Get current token payload (testing) |
| GET | `/api/token-info` | Seconds remaining in token window |
| GET | `/api/camera/stream` | MJPEG webcam stream |
| POST | `/api/camera/start` | Start webcam capture |
| POST | `/api/camera/stop` | Stop webcam capture |
| GET | `/api/users` | List all users |
| POST | `/api/users` | Create user |

## Token Security

- Each user has a unique `secret_key` derived from `MASTER_SECRET + custom_id`
- Token = `HMAC-SHA256(secret_key, floor(unix_time / 15))`
- Valid window: current ± 1 step (covers ±15s clock drift)
- Duplicate scan guard: 2-minute cooldown per user

## Notifications

Notifications fire asynchronously via `BackgroundTasks` — the scanner never waits.

Template: `"Notice: [Name] has successfully registered [TIME IN/OUT] at [HH:MM AM/PM] on [Month DD, YYYY]."`

Sent to `parent_phone` (SMS) and `parent_email` (email) if configured.
