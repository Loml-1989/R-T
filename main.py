import os
import secrets
import httpx
from fastapi import FastAPI, Depends, HTTPException, Security, Request, Query
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from openai import AsyncOpenAI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from database import init_db, create_user, verify_user, log_interaction, get_history

