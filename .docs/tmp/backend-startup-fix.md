# Backend Startup Fix Investigation

## Issue
Backend failed to start with error:
```
ValueError: FIRECRAWL_WEBHOOK_SECRET is required in production mode. Set DEBUG=true to allow insecure webhooks in development.
```

## Root Cause Analysis

### Configuration Loading
- **Config file**: `/home/jmagar/code/graphrag/apps/api/app/core/config.py`
  - Line 26: `env_file=".env"` - loads from current directory
  - Line 185-192: `validate_webhook_config()` - requires `FIRECRAWL_WEBHOOK_SECRET` when `is_production=True`
  - Line 217: `DEBUG: bool = False` - defaults to production mode

### Environment File Discovery
Found **two** `.env` files:
1. `/home/jmagar/code/graphrag/.env` (root)
   - ✅ Contains 
   
2. `/home/jmagar/code/graphrag/apps/api/.env` (API directory)
   - ❌ Missing `FIRECRAWL_WEBHOOK_SECRET`
   - ❌ Missing `DEBUG` setting (defaults to `False`)

### Why It Failed
- Backend runs from `apps/api/` directory via `uv run python -m app.main`
- Pydantic Settings loads `.env` relative to execution directory
- Loaded `apps/api/.env` instead of root `.env`
- No `FIRECRAWL_WEBHOOK_SECRET` found → validation failed

## Solution Applied

Added to `/home/jmagar/code/graphrag/apps/api/.env`:

```env
# After FIRECRAWL_API_KEY (line 3):
FIRECRAWL_WEBHOOK_SECRET=your_dev_secret_here

# At end of file (line 28-30):
# Development Mode
DEBUG=true
```

## Verification

```bash
cd /home/jmagar/code/graphrag/apps/api
uv run python -m app.main
```

Result:
```
INFO:     Uvicorn running on http://0.0.0.0:4400 (Press CTRL+C to quit)
INFO:     Started server process [4038690]
INFO:     Application startup complete.
```

✅ Backend starts successfully
✅ No validation errors
✅ Ready for development

## Key Files
- Config: `/home/jmagar/code/graphrag/apps/api/app/core/config.py`
- Env (Root): `/home/jmagar/code/graphrag/.env`
- Env (API): `/home/jmagar/code/graphrag/apps/api/.env` ← Modified
