from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import re
from typing import TypedDict, List, Optional
from pydantic import BaseModel, ValidationError
from langchain_core.prompts import PromptTemplate

# Google GenAI SDK
try:
    from google import genai
except Exception as e:
    raise ImportError("google-genai SDK not installed. Run: pip install google-genai") from e

# ----------------------------
# Load variables.json relative to this file
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAR_PATH = os.path.join(os.path.dirname(__file__), "variables.json")

if not os.path.exists(VAR_PATH):
    sys.exit(f"ERROR: variables.json not found at {VAR_PATH}. Place variables.json next to reddit_agent.py")

with open(VAR_PATH, "r") as f:
    variables = json.load(f)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY missing! Add GOOGLE_API_KEY to server/.env.\n"
        "Example:\nGOOGLE_API_KEY=AIza...yourkey"
    )

# ALWAYS use API key (you're not using Vertex AI)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

## ----------------------------
# Utility: call model and extract text (minimal-arg compat for your SDK)
# ----------------------------
def call_model(prompt: str, temperature: float = 0.2, max_output_tokens: int = 512) -> str:
    """
    Minimal-arg calls to google-genai methods for SDK shapes that do not accept 'temperature'/
    'max_output_tokens' as kwargs. This tries safe, small signatures and extracts text.
    """
    def _extract_text(resp) -> str:
        if resp is None:
            return ""
        # common convenience property
        if hasattr(resp, "output_text") and resp.output_text:
            return resp.output_text
        # common structured output
        outputs = getattr(resp, "output", None) or getattr(resp, "outputs", None)
        if outputs:
            parts = []
            try:
                for out in outputs:
                    content = out.get("content") if isinstance(out, dict) else getattr(out, "content", None)
                    if content:
                        for c in content:
                            if isinstance(c, dict):
                                t = c.get("text") or c.get("output_text") or c.get("content")
                            else:
                                t = getattr(c, "text", None) or getattr(c, "output_text", None)
                            if t:
                                parts.append(t)
            except Exception:
                pass
            if parts:
                return "".join(parts)
        # chats style: check candidates or nested content
        try:
            # often resp has .candidates or .output[0].content
            cand = getattr(resp, "candidates", None)
            if cand:
                parts = []
                for c in cand:
                    if isinstance(c, dict):
                        t = c.get("content") or c.get("text")
                        if t:
                            parts.append(t)
                    else:
                        parts.append(str(c))
                if parts:
                    return "".join(parts)
        except Exception:
            pass
        # fallback: iterate if iterable
        try:
            parts = []
            for item in resp:
                if isinstance(item, dict):
                    t = item.get("text") or item.get("output_text")
                else:
                    t = getattr(item, "text", None) or getattr(item, "output_text", None)
                if t:
                    parts.append(t)
            if parts:
                return "".join(parts)
        except Exception:
            pass
        # last resort: stringify
        try:
            return str(resp)
        except Exception:
            return ""

    attempts = []
    last_err = None

    # 1) Try models.generate_content with minimal args
    try:
        if hasattr(genai_client, "models") and hasattr(genai_client.models, "generate_content"):
            # minimal call: model + contents
            resp = genai_client.models.generate_content(
                model=GOOGLE_MODEL,
                contents=[prompt],
            )
            out = _extract_text(resp)
            if out:
                return out.strip()
    except Exception as e:
        attempts.append(("models.generate_content(minimal)", repr(e)))
        last_err = e

    # 2) Try models.generate with minimal args
    try:
        if hasattr(genai_client, "models") and hasattr(genai_client.models, "generate"):
            # some SDKs accept input (string) without extra kwargs
            try:
                resp = genai_client.models.generate(
                    model=GOOGLE_MODEL,
                    input=prompt,
                )
            except TypeError:
                # some variants use 'prompt' instead of 'input'
                resp = genai_client.models.generate(
                    model=GOOGLE_MODEL,
                    prompt=prompt,
                )
            out = _extract_text(resp)
            if out:
                return out.strip()
    except Exception as e:
        attempts.append(("models.generate(minimal)", repr(e)))
        last_err = e

    # 3) Try chats.create with several minimal message shapes (no temperature/max_output_tokens)
    chat_variants = [
        {"messages": [{"role": "user", "content": prompt}]},
        {"messages": [{"role": "user", "text": prompt}]},
        {"input": prompt},
        {"prompt": prompt},
        {"content": [{"type": "text", "text": prompt}]},
        {"messages": [{"author": "user", "content": [{"type": "text", "text": prompt}]}]},
    ]

    for variant in chat_variants:
        try:
            if hasattr(genai_client, "chats") and hasattr(genai_client.chats, "create"):
                kwargs = {"model": GOOGLE_MODEL, **variant}
                resp = genai_client.chats.create(**kwargs)
                out = _extract_text(resp)
                if out:
                    return out.strip()
        except Exception as e:
            attempts.append((f"chats.create minimal {list(variant.keys())}", repr(e)))
            last_err = e

    # 4) Try top-level helpers with minimal args if available
    try:
        if hasattr(genai, "generate_content"):
            try:
                resp = genai.generate_content(model=GOOGLE_MODEL, contents=[prompt], api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None)
                out = _extract_text(resp)
                if out:
                    return out.strip()
            except Exception as e:
                attempts.append(("genai.generate_content", repr(e)))
                last_err = e
        if hasattr(genai, "generate"):
            try:
                resp = genai.generate(model=GOOGLE_MODEL, prompt=prompt, api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None)
                out = _extract_text(resp)
                if out:
                    return out.strip()
            except Exception as e:
                attempts.append(("genai.generate", repr(e)))
                last_err = e
    except Exception as e:
        attempts.append(("top-level genai", repr(e)))
        last_err = e

    # Nothing worked — provide helpful debug info
    hint_lines = [
        "Could not call Google GenAI successfully with minimal signatures.",
        "Attempts (name, exception):",
    ]
    for name, err in attempts:
        hint_lines.append(f"- {name}: {err}")
    hint_lines.append("Ensure your google-genai SDK version is compatible, or ask me to use a REST fallback.")
    if last_err:
        hint_lines.append(f"Last internal error repr: {repr(last_err)}")
    raise RuntimeError("\n".join(hint_lines))


# ----------------------------
# JSON extraction helper
# ----------------------------
import re
from typing import Optional

def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Attempts to find a JSON object or array in text and return it as dict/list.
    Works even if the model wraps the JSON with backticks or explanatory text.
    """
    if not text:
        return None

    # Try direct json.loads first (if the whole text is JSON)
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove common code fences and surrounding markup
    cleaned = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()

    # Attempt to find the first top-level JSON object or array using regex (from first '{' to last '}' or '['..']')
    obj_match = re.search(r'(\{(?:.|\s)*\})', cleaned)
    arr_match = re.search(r'(\[(?:.|\s)*\])', cleaned)

    candidate = None
    if obj_match:
        candidate = obj_match.group(1)
    elif arr_match:
        candidate = arr_match.group(1)

    if candidate:
        try:
            return json.loads(candidate)
        except Exception:
            # last attempt: remove trailing commas commonly inserted by models
            candidate_fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(candidate_fixed)
            except Exception:
                return None

    return None

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

Return only valid JSON with keys:
- original_prompt (string)
- polished_prompt (string)

Example:
{{"original_prompt": "...", "polished_prompt": "..."}}
    """

    prompt_template = PromptTemplate.from_template(template)
    prompt_value = prompt_template.invoke({
        "platform": platform,
        "about_herth": about_herth,
        "tone": tone or "",
        "audience": audience or "",
        "prompt": state["prompt"],
    })

    # call Google GenAI
    raw = call_model(prompt_value, temperature=0.2, max_output_tokens=400)

    # attempt to extract JSON from model output
    parsed = extract_json_from_text(raw)
    if not parsed:
        # fallback: try to interpret the whole text as polished prompt only
        # Put the original into original_prompt and the raw text into polished_prompt
        parsed = {
            "original_prompt": state["prompt"],
            "polished_prompt": raw
        }

    # validate/construct Pydantic model
    try:
        polished = PolishOutput(**parsed)
    except ValidationError as e:
        # If validation fails, attempt to coerce fallback
        polished = PolishOutput(original_prompt=state["prompt"], polished_prompt=str(parsed.get("polished_prompt", raw)))

    state["prompt"] = polished.polished_prompt
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

Return only valid JSON with keys: post_title, post_text, post_hashtags.
Example:
{{"post_title": "Title here", "post_text": "Body here", "post_hashtags": ["#a","#b","#c"]}}
    """

    gen_prompt = PromptTemplate.from_template(template)
    prompt_value = gen_prompt.invoke({
        "platform": platform,
        "polished_prompt": polished_prompt,
    })

    raw = call_model(prompt_value, temperature=0.2, max_output_tokens=600)
    parsed = extract_json_from_text(raw)

    if not parsed:
        # Attempt heuristic parsing: fallback to putting entire output into post_text
        parsed = {
            "post_title": polished_prompt.split("\n", 1)[0][:60],  # naive short title fallback
            "post_text": raw,
            "post_hashtags": []
        }

    # Validate into FinalPost
    try:
        final = FinalPost(**parsed)
    except ValidationError:
        # Attempt to coerce fields if the model returned slightly different keys
        coerced = {
            "post_title": parsed.get("post_title") or parsed.get("title") or (polished_prompt.split("\n", 1)[0][:60]),
            "post_text": parsed.get("post_text") or parsed.get("text") or raw,
            "post_hashtags": parsed.get("post_hashtags") or parsed.get("hashtags") or [],
        }
        final = FinalPost(**coerced)

    return final

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
    Backwards-compatible public function with robust error surfacing.
    """
    import traceback, logging
    log = logging.getLogger("reddit_agent")

    try:
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

    except Exception as exc:
        # Log full traceback to stdout / uvicorn logs for easy debugging
        log.error("Exception inside generate_post: %s", exc, exc_info=True)
        # Re-raise so callers (and the debug script) get the full traceback
        raise
