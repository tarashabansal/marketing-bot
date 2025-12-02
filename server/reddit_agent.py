# reddit_agent.py

import os
import json
from typing import TypedDict, List, Annotated
from pydantic import BaseModel
from typing_extensions import Annotated as TE_Annotated
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import os, json

os.environ["OPENROUTER_API_KEY"] = "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"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
VAR_PATH = os.path.join(BASE_DIR, "variables.json")

with open(VAR_PATH, "r") as file:
    content = file.read()
variables = json.loads(content)
# variables["about_herth"], variables["platform"], etc. now available globally

# -----------------------------------------
# LangChain LLM client (OpenRouter)
# -----------------------------------------
llm = ChatOpenAI(
    temperature=0.2,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    model="openai/gpt-4o-mini",
)

# -----------------------------------------
# Structured output format for polishing
# -----------------------------------------
class PolishOutput(BaseModel):
    original_prompt: str
    polished_prompt: str


class PostState(TypedDict):
    prompt: str
    image_urls: List[str]


# -----------------------------------------
# POLISH USER PROMPT (uses variables.json)
# -----------------------------------------
def polish_prompt(state: PostState) -> PostState:
    prompt_template = PromptTemplate.from_template(
        """
The user is using an automated agent to post on {platform} about their platform herth.
About herth:
{about_herth}

The user has written a very casual prompt.
Your job: polish & tailor this prompt for {platform} so the posting agent can produce a professional final post.

User's original prompt:
{prompt}
"""
    )

    llm_structured = llm.with_structured_output(PolishOutput)

    prompt_value = prompt_template.invoke(
        {
            "about_herth": variables["about_herth"],
            "platform": variables["platform"],
            "prompt": state["prompt"],
        }
    )

    response = llm_structured.invoke(prompt_value)

    state["prompt"] = response.polished_prompt
    return state


# -----------------------------------------
# FINAL GENERATION STEP (simple example)
# -----------------------------------------
class FinalPost(BaseModel):
    post_text: str
    post_title: str
    post_hashtags: List[str]


def final_generation(polished_prompt: str) -> FinalPost:
    final_template = PromptTemplate.from_template(
        """
You are an expert social media content generator.

Write a final polished post based on the refined prompt below.
Add:
- A short title (catchy, <8 words)
- A professional post body
- A list of 3–6 hashtags

Refined prompt:
{prompt}

Return JSON with:
- post_text
- post_title
- post_hashtags
"""
    )

    llm_structured = llm.with_structured_output(FinalPost)

    rendered = final_template.invoke({"prompt": polished_prompt})
    result = llm_structured.invoke(rendered)
    return result


# -----------------------------------------
# PUBLIC FUNCTION CALLED BY YOUR API
# -----------------------------------------
def generate_post(user_prompt: str, image_urls=None) -> dict:
    """
    This is what the API endpoint will call.
    """
    state: PostState = {
        "prompt": user_prompt,
        "image_urls": image_urls or [],
    }

    # step 1: polish using variables.json
    state = polish_prompt(state)

    # step 2: final post generation
    final = final_generation(state["prompt"])

    return {
        "success": True,
        "platform": variables["platform"],
        "polished_prompt": state["prompt"],
        "post_title": final.post_title,
        "post_text": final.post_text,
        "post_hashtags": final.post_hashtags,
    }


# Manual test:
if __name__ == "__main__":
    out = generate_post("post something about our new feature pls")
    import pprint
    pprint.pprint(out)
