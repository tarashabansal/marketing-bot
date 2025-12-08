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
    import pathlib
    env_path = pathlib.Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
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
        "https://marketing-bot-two.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
LINKEDIN_TOKEN = os.getenv("LINKEDIN_OAUTH_TOKEN")    
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_ACCOUNT_URN") 

# OAuth Config
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
# Default to frontend dev server; user must match this in LinkedIn App settings
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:5173")

class LinkedInPostRequest(BaseModel):
    text: str
    access_token: Optional[str] = None
    person_urn: Optional[str] = None

@app.get("/api/auth/linkedin/url")
def linkedin_auth_url():
    """
    Returns the LinkedIn OAuth authorization URL.
    """
    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(500, "LINKEDIN_CLIENT_ID not set on server")
    
    # Updated Scopes for modern LinkedIn Apps:
    # openid: for ID token
    # profile: for name/photo
    # email: for email (optional)
    # w_member_social: for posting
    scopes = "openid profile w_member_social email"
    state = "random_string_for_csrf" 
    
    url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        f"&state={state}"
        f"&scope={scopes}"
    )
    return {"url": url}

class AuthCallbackRequest(BaseModel):
    code: str

@app.post("/api/auth/linkedin/callback")
def linkedin_callback(req: AuthCallbackRequest):
    """
    Exchanges auth code for access token and fetches user URN via OpenID.
    """
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        raise HTTPException(500, "LinkedIn Client ID/Secret not set")

    # 1. Exchange code for token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": req.code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    r = requests.post(token_url, data=data)
    if not r.ok:
        raise HTTPException(400, f"Failed to get token: {r.text}")
    
    token_data = r.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(400, "No access token in response")

    # 2. Get User Profile via OpenID userinfo endpoint
    # This replaces the old 'me' endpoint which required r_liteprofile
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    r_profile = requests.get(userinfo_url, headers=headers)
    
    urn = None
    name = "LinkedIn User"
    
    if r_profile.ok:
        u_data = r_profile.json()
        # 'sub' is the unique user ID for this app
        user_sub = u_data.get("sub")
        if user_sub:
            urn = f"urn:li:person:{user_sub}"
        
        # 'name' is usually provided directly
        name = u_data.get("name") or f"{u_data.get('given_name', '')} {u_data.get('family_name', '')}".strip()
    else:
        log.error(f"Failed to fetch userinfo: {r_profile.text}")
        raise HTTPException(400, f"Failed to fetch user profile: {r_profile.text}")

    return {
        "access_token": access_token,
        "urn": urn,
        "name": name,
        "expires_in": token_data.get("expires_in")
    }

@app.post("/api/linkedin_post")
def linkedin_post(req: LinkedInPostRequest):
    """
    Post to LinkedIn using provided token/URN or fallback to env vars.
    """
    token = req.access_token or LINKEDIN_TOKEN
    urn = req.person_urn or LINKEDIN_PERSON_URN

    if not token or not urn:
        raise HTTPException(400, "Missing LinkedIn credentials (token/urn). Connect account first.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    payload = {
        "author": urn,
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
