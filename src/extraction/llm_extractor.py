import json
import logging
import os
import sys
import time
from typing import Literal

from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import (
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from src.extraction.schemas import BatterySpecification
from src.extraction.prompts import build_zero_shot_prompt, build_few_shot_prompt

logger = logging.getLogger(__name__)

def get_llm_client(model_name: str) -> OpenAI:
    if model_name.startswith("ollama/"):
        return OpenAI(
            api_key=OLLAMA_API_KEY,
            base_url=OLLAMA_BASE_URL,
        )

    if model_name.startswith("gemini"):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in .env")
        return OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in .env")
    return OpenAI(api_key=OPENAI_API_KEY)

def call_llm(messages: list, model: str = None, max_retries: int = 3) -> str:
    model = model or LLM_MODEL
    client = get_llm_client(model)
    request_model = model.split("/", 1)[1] if model.startswith("ollama/") else model

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=request_model,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content.strip()
            return content
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries:
                # Parse retryDelay from error message if available
                import re
                delay_match = re.search(r'retryDelay.*?(\d+)', error_str)
                wait = int(delay_match.group(1)) + 5 if delay_match else 30
                logger.warning(f"Rate limited, waiting {wait}s before retry {attempt+1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise

def parse_llm_response(response_text: str) -> dict:
    text = response_text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except Exception as e:
        logger.error(f"json parse error: {e}")
        raise ValueError("not valid json")

def extract_specifications(
    datasheet_text: str,
    strategy: Literal["zero_shot", "few_shot"] = "zero_shot",
    model: str = None,
) -> BatterySpecification:
    if strategy == "zero_shot":
        messages = build_zero_shot_prompt(datasheet_text)
    elif strategy == "few_shot":
        messages = build_few_shot_prompt(datasheet_text)
    else:
        raise ValueError("bad strategy")

    response_text = call_llm(messages, model=model)
    data = parse_llm_response(response_text)

    return BatterySpecification(**data)

def extract_all_datasheets(
    documents: list,
    strategy: Literal["zero_shot", "few_shot"] = "zero_shot",
    model: str = None,
) -> list:
    results = []
    for i, doc in enumerate(documents):
        if i > 0:
            time.sleep(5)  # Rate-limit delay for free-tier APIs
        logger.info(f"processing {doc.filename}")
        try:
            spec = extract_specifications(
                doc.cleaned_text,
                strategy=strategy,
                model=model,
            )
            results.append((doc.filename, spec))
        except Exception as e:
            logger.error(f"failed {doc.filename}: {e}")
            results.append((doc.filename, None))
    return results

def save_results(results: list, output_dir: str, strategy: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    output = {}
    for filename, spec in results:
        if spec:
            output[filename] = spec.model_dump()
        else:
            output[filename] = {"error": "failed"}

    path = os.path.join(output_dir, f"extraction_{strategy}.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    return path
