import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .config import VIDEO_ANALYSIS_MODEL

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY_VIDEO_ANALYZER"))

# The prompt that shapes the quality of every future search result.
# Gemini will watch the video and answer this — the richer the output,
# the better ChromaDB can match it against natural language queries later.
_SUMMARY_PROMPT = """
Watch this video carefully and generate a rich semantic summary.

Include:
- The main topic or skill being demonstrated or discussed
- Key concepts, tools, techniques, or products mentioned
- The mood and style (tutorial, motivational, funny, aesthetic, etc.)
- Any specific details a person might use to search for this later
  (e.g. "morning routine", "React hooks", "sourdough bread", "chest workout")

Write in plain prose. Be specific and descriptive.
Do not say "this video" — just describe the content directly.
"""


def analyze_video(video_path: Path) -> str:
    """
    Upload a video to Gemini File API, wait for processing,
    then generate and return a rich semantic summary.

    This summary is what gets embedded into ChromaDB —
    its quality directly determines search result quality.
    """
    # Step 1: Upload
    # Upload the video file to Google's servers.
    # mime_type tells the API what kind of file this is.
    # The returned object contains a .name handle (e.g. "files/abc123")
    # that we'll reference in the prompt.
    print(f"Uploading {video_path.name} to Gemini File API...")

    uploaded_file = _client.files.upload(
        file=video_path,
        config=types.UploadFileConfig(mime_type="video/mp4")
    )

    # ── Step 2: Wait for ACTIVE state
    # Google processes the file asynchronously after upload.
    # State starts as PROCESSING and becomes ACTIVE when ready.
    # Prompting before ACTIVE raises an error, so we poll until it's ready.
    print("Waiting for Gemini to process the video...")

    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        # Re-fetch the file object to get the latest state
        uploaded_file = _client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name != "ACTIVE":
        raise RuntimeError(
            f"File processing failed. Final state: {uploaded_file.state.name}"
        )
    
    # ── Step 3: Generate summary
    # Pass the file reference and our prompt together as a list.
    # Gemini receives both, watches the video, and generates the summary.
    # This is the multimodal part — content is [file_reference, text_prompt].
    print("Generating semantic summary...")

    response = _client.models.generate_content(
        model=VIDEO_ANALYSIS_MODEL,
        contents=[uploaded_file, _SUMMARY_PROMPT]
    )

    summary = response.text.strip()

    # ── Step 4: Clean up 
    # Delete the file from Google's servers after we're done.
    # Files are auto-deleted after 48 hours anyway, but explicit cleanup
    # is good practice — same reason you close file handles in DocIQ.
    _client.files.delete(name=uploaded_file.name)
    print("File deleted from Gemini servers.")

    return summary
    