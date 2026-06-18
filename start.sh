#!/bin/sh
# Start web UI in background
uvicorn app.web:app --host 0.0.0.0 --port 8080 &
# Start watch process in foreground
python -m app.main watch --interval 60 --stable-seconds 120 --apply
