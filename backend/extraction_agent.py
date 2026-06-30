"""
Extraction Agent
----------------
Calls the Claude API with a strict JSON-only system prompt to convert raw
SEBI regulatory clause text into structured Obligation records.

This is the "agentic" core of RegSense: it reads unstructured regulatory
text and produces operational, machine-actionable compliance logic.
"""

import json
import os
from typing import List, Dict

import anthropic

SYSTEM_PROMPT = """You are a regulatory compliance extraction agent for the Indian \
securities market. You convert raw SEBI circular text into structured compliance \
obligations for a named intermediary category.

Respond with ONLY a JSON array, no preamble, no markdown fences, no commentary. \
Each element must follow this exact schema:

{
  "source_clause": "string - clause/section identifier or short locator from the text",
  "intermediary_category": "string - e.g. stockbroker",
  "requirement_summary": "string - one or two sentence plain-language summary of what must be done",
  "action_type": "string - one of: reporting, disclosure, process_control, record_keeping, kyc",
  "frequency": "string - one of: daily, weekly, monthly, quarterly, annual, one_time, continuous",
  "evidence_required": "string - what artefact/record proves this obligation was fulfilled"
}

Extract one object per distinct obligation. Do not merge unrelated obligations. \
Do not invent obligations not present in the text. If the text contains no \
obligations, return an empty array []."""


def extract_obligations(circular_text: str, intermediary_category: str, source_circular: str) -> List[Dict]:
    """Run the extraction agent over raw circular text and return structured obligations."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    user_prompt = (
        f"Intermediary category to extract obligations for: {intermediary_category}\n\n"
        f"Regulatory text:\n{circular_text}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        obligations = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Extraction agent returned non-JSON output: {raw_text[:300]}") from e

    for ob in obligations:
        ob["source_circular"] = source_circular

    return obligations
