# server/app.py
import os
import logging
from typing import List, Optional
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# load .env for local dev (python-dotenv should be installed)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


log = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Content Generation API",
    description="Wraps reddit_agent.generate_post to produce social media posts",
    version="0.1.0",
)

# CORS - allow your frontend dev origins (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # CRA default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
LINKEDIN_TOKEN = os.getenv("LINKEDIN_OAUTH_TOKEN")    
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_ACCOUNT_URN") 

class LinkedInPostRequest(BaseModel):
    text: str



@app.post("/api/linkedin_post")
def linkedin_post(req: LinkedInPostRequest):
    """
    Very simple LinkedIn post using env-stored token + person URN.
    """
    if not LINKEDIN_TOKEN or not LINKEDIN_PERSON_URN:
        raise HTTPException(500, "LinkedIn env vars not set")

    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": req.text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload)

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {"success": True, "linkedin_response": r.text}

class GenerateRequest(BaseModel):
    prompt: str
    tone: Optional[str] = None
    audience: Optional[str] = None
    platforms: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    success: bool
    platform: Optional[str] = None
    polished_prompt: Optional[str] = None
    post_title: Optional[str] = None
    post_text: Optional[str] = None
    post_hashtags: Optional[List[str]] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """
    Generate a post using reddit_agent.generate_post(user_prompt, tone=None, audience=None, platforms=None, image_urls=None).
    """
    import reddit_agent

    log.info(f"Received generate request: prompt={req.prompt!r}, tone={req.tone!r}, audience={req.audience!r}, platforms={req.platforms!r}")
    try:
        result = reddit_agent.generate_post(
            user_prompt=req.prompt,
            tone=req.tone,
            audience=req.audience,
            platforms=req.platforms or [],
            image_urls=req.image_urls or [],
        )
    except Exception as exc:
        log.exception("Generation failed")
        raise HTTPException(status_code=500, detail="Generation failed. Check server logs.")

    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Generator returned unexpected format.")

    return {
        "success": result.get("success", True),
        "platform": result.get("platform"),
        "polished_prompt": result.get("polished_prompt"),
        "post_title": result.get("post_title"),
        "post_text": result.get("post_text"),
        "post_hashtags": result.get("post_hashtags"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
