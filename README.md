# Roast & Toast API

A simple API that gets a given user's public GitHub info (bio, repo count, recent languages, and project names) and uses AI to generate a short, custom roast or motivational toast.

Features built-in are :
1. API key management
2. local SQLite persistence
3. pagination for tracking logs
4. IP-based rate limiting to protect AI upstream.

## Quick Start

### 1. Requirements & Setup
Clone the files locally and install the dependencies:
```pip install fastapi uvicorn httpx slowapi pydantic``` OR ```pip install -r requirements.txt```
Set ur hack club ai key. (Only works w it.)
```set -x HACKCLUB_AI_KEY "your_actual_key_here"```
Start the server.
```uvicorn main:app --reload```