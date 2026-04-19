#!/bin/bash
if [ "$SERVICE" = "bot" ]; then
    python -m bot.main
else
    python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
fi
