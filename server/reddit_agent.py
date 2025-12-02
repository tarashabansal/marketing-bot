# server/reddit_agent.py
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
from typing import TypedDict, List, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# ----------------------------
# Load variables.json relative to this file
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAR_PATH = os.path.join(BASE_DIR, "variables.json")

if not os.path.exists(VAR_PATH):
    sys.exit(f"ERROR: variables.json not found at {VAR_PATH}. Place variables.json next to reddit_agent.py")

with open(VAR_PATH, "r") as f:
    variables = json.load(f)

# ----------------------------
# Validate OPENROUTER key
# ----------------------------
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    sys.exit("ERROR: OPENROUTER_API_KEY not set. Add it to server/.env or export it in your shell.")

# ----------------------------
# Initialize LLM client
# ----------------------------
llm = ChatOpenAI(
    temperature=0.2,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_KEY,
    model="openai/gpt-4o-mini",
)

# ----------------------------
# Types and structured outputs
# ----------------------------
class PolishOutput(BaseModel):
    original_prompt: str
    polished_prompt: str

class FinalPost(BaseModel):
    post_text: str
    post_title: str
    post_hashtags: List[str]

class PostState(TypedDict):
    prompt: str
    image_urls: List[str]

# ----------------------------
# Polishing function
# ----------------------------
def polish_prompt(state: PostState, tone: Optional[str] = None, audience: Optional[str] = None, platform_override: Optional[str] = None) -> PostState:
    """
    Polishes the user's casual prompt for a particular platform and optional tone/audience.
    Uses variables.json for general context unless platform_override is provided.
    """
    platform = platform_override or variables.get("platform", "LinkedIn")
    about_herth = variables.get("about_herth", "")

    template = """
The user is using an automated agent to post on {platform} about their platform Herth.
About Herth:
{about_herth}

Tone (user preference): {tone}
Target audience: {audience}

The user provided a casual prompt. Your job is to tailor and polish this prompt for {platform} so the posting agent can create a professional final post.

User's original prompt:
{prompt}
    """

    prompt_template = PromptTemplate.from_template(template)
    llm_structured = llm.with_structured_output(PolishOutput)

    prompt_value = prompt_template.invoke({
        "platform": platform,
        "about_herth": about_herth,
        "tone": tone or "",
        "audience": audience or "",
        "prompt": state["prompt"],
    })

    response = llm_structured.invoke(prompt_value)
    # response is a Pydantic model with polished_prompt
    state["prompt"] = response.polished_prompt
    return state

# ----------------------------
# Final generation function
# ----------------------------
def final_generation(polished_prompt: str, platform: str) -> FinalPost:
    """
    Generate final post text, title, and hashtags using the polished prompt.
    """
    template = """
You are an expert social media content generator.

Produce:
- A short catchy title (<= 8 words) as "post_title".
- A professional post body suitable for {platform} as "post_text".
- A list of 3–6 relevant hashtags as "post_hashtags".

Polished prompt:
{polished_prompt}

Return JSON with keys: post_title, post_text, post_hashtags.
    """

    gen_prompt = PromptTemplate.from_template(template)
    llm_structured = llm.with_structured_output(FinalPost)

    prompt_value = gen_prompt.invoke({
        "platform": platform,
        "polished_prompt": polished_prompt,
    })

    result = llm_structured.invoke(prompt_value)
    return result

# ----------------------------
# Public generate_post (backwards-compatible signature)
# ----------------------------
def generate_post(
    user_prompt: str,
    tone: Optional[str] = None,
    audience: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    image_urls: Optional[List[str]] = None,
) -> dict:
    """
    Backwards-compatible public function.
    - user_prompt: required
    - tone, audience, platforms, image_urls: optional
    If platforms is provided, the first platform is used for polishing/generation; otherwise variables.json platform is used.
    """

    # normalize inputs
    platforms = platforms if platforms is not None else []
    image_urls = image_urls or []
    tone = tone or ""
    audience = audience or ""

    # choose platform (if provided, use first; else fallback to variables.json)
    platform_to_use = platforms[0] if len(platforms) > 0 else variables.get("platform", "LinkedIn")

    # prepare state
    state: PostState = {"prompt": user_prompt, "image_urls": image_urls}

    # step 1: polish prompt (uses variables.json internally)
    state = polish_prompt(state, tone=tone, audience=audience, platform_override=platform_to_use)

    # step 2: final generation
    final = final_generation(state["prompt"], platform=platform_to_use)

    return {
        "success": True,
        "platform": platform_to_use,
        "polished_prompt": state["prompt"],
        "post_title": final.post_title,
        "post_text": final.post_text,
        "post_hashtags": final.post_hashtags,
    }

# quick local test
if __name__ == "__main__":
    sample = generate_post(
        user_prompt="Announce our new posting feature in one short paragraph",
        tone="professional",
        audience="Fashion bloggers",
        platforms=["Reddit"]
    )
    import pprint
    pprint.pprint(sample)
