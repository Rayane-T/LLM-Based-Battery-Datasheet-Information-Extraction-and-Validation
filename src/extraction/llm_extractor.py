"""
LLM-based battery specification extractor.

Uses OpenAI-compatible API to extract structured battery specifications
from datasheet text using zero-shot or few-shot prompting strategies.
"""

import json
import logging
import os
import sys
from typing import Literal

from openai import OpenAI

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from src.extraction.schemas import BatterySpecification
from src.extraction.prompts import build_zero_shot_prompt, build_few_shot_prompt

logger = logging.getLogger(__name__)


def get_llm_client() -> OpenAI:
    """
    Create and return an OpenAI client.
    
    Raises:
        ValueError: If the API key is not configured.
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. Please set it in your .env file or environment variables."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def call_llm(messages: list, model: str = None) -> str:
    """
    Send messages to the LLM and return the response text.
    
    Args:
        messages: List of message dicts for the chat API.
        model: Model name to use (defaults to config LLM_MODEL).
    
    Returns:
        Raw response text from the LLM.
    """
    client = get_llm_client()
    model = model or LLM_MODEL

    logger.info(f"Calling LLM ({model}) with {len(messages)} messages...")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )

    content = response.choices[0].message.content.strip()
    logger.info(f"LLM response received ({len(content)} chars)")
    return content


def parse_llm_response(response_text: str) -> dict:
    """
    Parse the LLM response text as JSON.
    Handles common issues like markdown code fences.
    
    Args:
        response_text: Raw text response from the LLM.
    
    Returns:
        Parsed JSON dictionary.
    
    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response text: {text[:500]}")
        raise ValueError(f"LLM response is not valid JSON: {e}") from e


def extract_specifications(
    datasheet_text: str,
    strategy: Literal["zero_shot", "few_shot"] = "zero_shot",
    model: str = None,
) -> BatterySpecification:
    """
    Extract battery specifications from datasheet text using an LLM.
    
    Args:
        datasheet_text: Cleaned text extracted from a battery datasheet PDF.
        strategy: Prompting strategy - "zero_shot" or "few_shot".
        model: LLM model name to use (defaults to config).
    
    Returns:
        BatterySpecification object with extracted values.
    
    Raises:
        ValueError: If the LLM response cannot be parsed.
    """
    # Build prompt based on strategy
    if strategy == "zero_shot":
        messages = build_zero_shot_prompt(datasheet_text)
    elif strategy == "few_shot":
        messages = build_few_shot_prompt(datasheet_text)
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'zero_shot' or 'few_shot'.")

    # Call LLM
    response_text = call_llm(messages, model=model)

    # Parse response
    data = parse_llm_response(response_text)

    # Validate and create Pydantic model
    spec = BatterySpecification(**data)

    logger.info(
        f"Extracted {spec.filled_fields_count()}/{spec.total_fields_count()} fields "
        f"using {strategy} strategy"
    )

    return spec


def extract_all_datasheets(
    documents: list,
    strategy: Literal["zero_shot", "few_shot"] = "zero_shot",
    model: str = None,
) -> list:
    """
    Extract specifications from multiple datasheets.
    
    Args:
        documents: List of DocumentText objects from pdf_parser.
        strategy: Prompting strategy to use.
        model: LLM model name to use.
    
    Returns:
        List of (filename, BatterySpecification) tuples.
    """
    results = []

    for doc in documents:
        logger.info(f"Processing: {doc.filename} ({strategy})")
        try:
            spec = extract_specifications(
                doc.cleaned_text,
                strategy=strategy,
                model=model,
            )
            results.append((doc.filename, spec))
            logger.info(f"  → Extracted {spec.filled_fields_count()} fields")
        except Exception as e:
            logger.error(f"  → Failed to extract from {doc.filename}: {e}")
            results.append((doc.filename, None))

    return results


def save_results(results: list, output_dir: str, strategy: str) -> str:
    """
    Save extraction results to a JSON file.
    
    Args:
        results: List of (filename, BatterySpecification) tuples.
        output_dir: Directory to save the output file.
        strategy: Strategy name for the filename.
    
    Returns:
        Path to the saved JSON file.
    """
    os.makedirs(output_dir, exist_ok=True)

    output = {}
    for filename, spec in results:
        if spec is not None:
            output[filename] = spec.model_dump()
        else:
            output[filename] = {"error": "Extraction failed"}

    output_path = os.path.join(output_dir, f"extraction_{strategy}.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Results saved to: {output_path}")
    return output_path
