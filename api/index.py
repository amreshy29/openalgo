"""
Vercel serverless entry point for OpenAlgo.

Vercel automatically sets VERCEL=1 in all deployments. env_check.py reads
this to skip .env file operations; all configuration is supplied via the
Vercel dashboard instead.

Required environment variables (set in Vercel dashboard):
  APP_KEY           - Flask secret key: python -c "import secrets; print(secrets.token_hex(32))"
  API_KEY_PEPPER    - Argon2/Fernet pepper: same command as above
  FERNET_SALT       - Per-install Fernet salt: same command as above
  BROKER_API_KEY    - Your broker's API key
  BROKER_API_SECRET - Your broker's API secret
  REDIRECT_URL      - Broker OAuth callback, e.g. https://<your-app>.vercel.app/<broker>/callback

Limitations on Vercel serverless:
  - SQLite data in /tmp is ephemeral (lost between cold starts); use an
    external database in production.
  - The WebSocket market-data proxy and background schedulers are disabled
    (serverless functions do not support persistent connections or processes).
  - Broker tokens expire daily; each cold start re-authenticates.
"""

import os
import sys

# Add the project root to the Python path so app.py and all modules resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Serverless identity ───────────────────────────────────────────────────────
# Vercel sets this automatically; the default here makes local testing easier.
os.environ.setdefault("VERCEL", "1")

# Disable the WebSocket proxy and background workers — they require a persistent
# process which Vercel's serverless model does not provide.
os.environ.setdefault("APP_MODE", "standalone")

# ── Writable filesystem ───────────────────────────────────────────────────────
# Only /tmp is writable on Vercel. Point all databases and log output there.
# Override any of these in the Vercel dashboard to use an external DB URL.
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/openalgo.db")
os.environ.setdefault("LATENCY_DATABASE_URL", "sqlite:////tmp/latency.db")
os.environ.setdefault("LOGS_DATABASE_URL", "sqlite:////tmp/logs.db")
os.environ.setdefault("HEALTH_DATABASE_URL", "sqlite:////tmp/health.db")
os.environ.setdefault("SANDBOX_DATABASE_URL", "sqlite:////tmp/sandbox.db")
os.environ.setdefault("HISTORIFY_DATABASE_URL", "/tmp/historify.duckdb")
os.environ.setdefault("LOG_TO_FILE", "False")
os.environ.setdefault("LOG_DIR", "/tmp/log")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
os.environ.setdefault("LOG_RETENTION", "14")
os.environ.setdefault("LOG_COLORS", "False")

# ── Flask / network ───────────────────────────────────────────────────────────
os.environ.setdefault("FLASK_HOST_IP", "0.0.0.0")
os.environ.setdefault("FLASK_PORT", "5000")
os.environ.setdefault("FLASK_DEBUG", "False")
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("NGROK_ALLOW", "FALSE")

# ── Host server URL ───────────────────────────────────────────────────────────
# VERCEL_URL is the auto-assigned deployment hostname (no scheme).
# VERCEL_PROJECT_PRODUCTION_URL is the stable production domain (if configured).
# Use either to auto-populate HOST_SERVER; override in the dashboard if you have
# a custom domain.
if not os.environ.get("HOST_SERVER"):
    _prod_url = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
    _deploy_url = os.environ.get("VERCEL_URL")
    if _prod_url:
        os.environ["HOST_SERVER"] = f"https://{_prod_url}"
    elif _deploy_url:
        os.environ["HOST_SERVER"] = f"https://{_deploy_url}"
    else:
        os.environ["HOST_SERVER"] = "http://localhost:5000"

_host = os.environ["HOST_SERVER"]
_host_domain = _host.replace("https://", "").replace("http://", "")

# ── WebSocket (informational only — not functional on serverless) ─────────────
os.environ.setdefault("WEBSOCKET_HOST", "0.0.0.0")
os.environ.setdefault("WEBSOCKET_PORT", "8765")
os.environ.setdefault("WEBSOCKET_URL", f"wss://{_host_domain}/ws")

# ── Broker defaults ───────────────────────────────────────────────────────────
os.environ.setdefault(
    "VALID_BROKERS",
    "fivepaisa,fivepaisaxts,aliceblue,angel,arrow,compositedge,dhan,dhan_sandbox,"
    "definedge,deltaexchange,firstock,flattrade,fyers,groww,ibulls,iifl,iiflcapital,"
    "indmoney,jainamxts,kotak,motilal,mstock,nubra,paytm,pocketful,rmoney,samco,"
    "shoonya,tradejini,upstox,wisdom,zebu,zerodha",
)
os.environ.setdefault("REDIRECT_URL", f"{_host}/callback")

# ── Rate limits and session ───────────────────────────────────────────────────
os.environ.setdefault("LOGIN_RATE_LIMIT_MIN", "5 per minute")
os.environ.setdefault("LOGIN_RATE_LIMIT_HOUR", "25 per hour")
os.environ.setdefault("RESET_RATE_LIMIT", "15 per hour")
os.environ.setdefault("API_RATE_LIMIT", "50 per second")
os.environ.setdefault("ORDER_RATE_LIMIT", "10 per second")
os.environ.setdefault("SMART_ORDER_RATE_LIMIT", "10 per second")
os.environ.setdefault("WEBHOOK_RATE_LIMIT", "100 per minute")
os.environ.setdefault("STRATEGY_RATE_LIMIT", "200 per minute")
os.environ.setdefault("SESSION_EXPIRY_TIME", "03:00")

# ── Misc ──────────────────────────────────────────────────────────────────────
os.environ.setdefault("ENV_CONFIG_VERSION", "1.0.7")
os.environ.setdefault("NGROK_ALLOW", "FALSE")

# Import the Flask application.  This executes app.py at module level which
# calls create_app() and setup_environment().
from app import app  # noqa: E402
