import os
from dotenv import load_dotenv
from .retriever import RetrievedReel
from .config import ANSWER_FORMAT_MODEL
from google import genai

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY_SEARCH_RESULT_GENERATOR"))

def _get_prompt(query: str,  results_block: str) -> str:
    """
    Prompt for model containing results_block of reels summary and url and the user query for model to format answer based on.
    """
    return f"""
You are formatting search results for a Telegram bot called ReelMind.
The user searched for: "{query}"

Here are the matching reels:

{results_block}

Format these as a clean, readable Telegram message.
For each result show:
- A short title or topic (derived from the summary, not copied verbatim)
- The match percentage
- The URL on its own line so Telegram renders a preview
- One sentence describing why it matches the query

Keep the tone casual and helpful. No markdown headers. No bullet walls.
Separate each result with a blank line.
If the matching reels attached are not at all totally relevant just say "No such content in your collection...".
If there is only one result, still format it the same way.
"""


def format_results(query: str, results: list[RetrievedReel]) -> str:
    """
    Ask Gemini to format raw search results into a clean Telegram message.

    Gemini's job here is presentation only — not reasoning or synthesis.
    We already have the right answers from ChromaDB; we just want them formatted in a way that reads naturally in a Telegram chat.
    """
    if not results:
        return "No matching reels found. Try a different search."

    # Build a plain text block describing each result.
    # Gemini will use this as the raw material for formatting.
    results_block = ""
    for i, reel in enumerate(results, start=1):
        results_block += f"""
Result {i}:
URL: {reel.url}
Similarity: {round(reel.similarity * 100)}%
Indexed on: {reel.timestamp}
Summary: {reel.summary}
""".strip() + "\n\n"
        
    prompt = _get_prompt(query, results_block)

    response = _client.models.generate_content(
        model=ANSWER_FORMAT_MODEL,
        contents=prompt
    )

    return response.text.strip()