import os
import secrets
import httpx
from fastapi import FastAPI, Depends, HTTPException, Security, Request, Query
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import database

HC_AI_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

user_scheme = APIKeyHeader(name="X-API-Key")
admin_scheme = APIKeyHeader(name="X-Admin-Key")

class Registration(BaseModel):
    api_key: str
    message: str

class GenerationPayload(BaseModel):
    github_username: str
    interaction_type: str 

class GenerationResult(BaseModel):
    target: str
    type: str
    result: str

async def verify_user(api_key: str = Security(user_scheme)) -> str:
    if not database.is_valid_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

async def verify_admin(admin_key: str = Security(admin_scheme)) -> str:
    expected_key = os.environ.get("ADMIN_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="Server missing ADMIN_API_KEY environment configuration")
    
    if not secrets.compare_digest(admin_key, expected_key):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Admin Key")
    return admin_key

@app.post("/register", response_model=Registration)
@limiter.limit("5/minute")
async def register(request: Request):
    key = secrets.token_hex(16)
    database.create_api_key(key)
    return {"api_key": key, "message": "Keep this safe and use X-API-Key header"}

@app.post("/generate", response_model=GenerationResult)
@limiter.limit("10/minute")
async def generate(request: Request, payload: GenerationPayload, api_key: str = Depends(verify_user)):
    if payload.interaction_type not in ["roast", "toast"]:
        raise HTTPException(status_code=400, detail="Type must be roast or toast")
        
    ai_key = os.environ.get("HACKCLUB_AI_KEY")
    if not ai_key:
        raise HTTPException(status_code=500, detail="Server missing AI credentials")

    headers = {"User-Agent": "FastAPI-App"}

    async with httpx.AsyncClient() as client:
        gh_user = await client.get(f"https://api.github.com/users/{payload.github_username}", headers=headers)
        if gh_user.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        
        gh_data = gh_user.json()
        gh_repos = await client.get(f"https://api.github.com/users/{payload.github_username}/repos?sort=updated&per_page=5", headers=headers)
        repo_data = gh_repos.json() if gh_repos.status_code == 200 else []

        repo_names = [r.get("name") for r in repo_data]
        
        prompt = f"Write a 2-sentence {payload.interaction_type} for GitHub user {payload.github_username}. "
        prompt += f"Bio: {gh_data.get('bio', 'None')}. Repos: {len(repo_data)}. "
        prompt += f"Recent work: {', '.join(repo_names)}."

        active_model = os.environ.get("HACKCLUB_AI_MODEL", "meta-llama/llama-3-8b-instruct")

        ai_payload = {
            "model": active_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        ai_req = await client.post(
            HC_AI_URL,
            headers={"Authorization": f"Bearer {ai_key}", "Content-Type": "application/json"},
            json=ai_payload,
            timeout=15.0
        )

        if ai_req.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Hack Club AI Error: {ai_req.text}")

        output_text = ai_req.json()["choices"][0]["message"]["content"]

    database.save_interaction(api_key, payload.github_username, payload.interaction_type, output_text)
    
    return {"target": payload.github_username, "type": payload.interaction_type, "result": output_text}

@app.get("/history")
@limiter.limit("20/minute")
async def history(request: Request, api_key: str = Depends(verify_user), limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0)):
    records = database.get_user_history(api_key, limit, offset)
    return {"data": records, "limit": limit, "offset": offset}

@app.get("/admin/users")
@limiter.limit("30/minute")
async def admin_get_users(request: Request, admin_key: str = Depends(verify_admin)):
    return {"users": database.get_all_users()}

@app.get("/admin/history")
@limiter.limit("30/minute")
async def admin_get_history(request: Request, admin_key: str = Depends(verify_admin), limit: int = Query(50), offset: int = Query(0)):
    return {"history": database.get_all_history(limit, offset)}

@app.get("/admin/model")
@limiter.limit("30/minute")
async def admin_view_model(request: Request, admin_key: str = Depends(verify_admin)):
    current_model = os.environ.get("HACKCLUB_AI_MODEL", "meta-llama/llama-3-8b-instruct")
    return {
        "current_active_model": current_model
    }