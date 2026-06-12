import json
import time
from pathlib import Path
from telegram import Update
from rag.embedder import is_already_indexed, store_reel
from rag.downloader import download_reel
from rag.video_analyzer import analyze_video
from rag.config import RATE_LIMIT_DELAY


def extract_urls(json_path: Path) -> list[str]:
    """
    Parse the Instagram saved_posts.json export and extract all reel URLs.

    Structure: top-level array of saved posts. Each post has a label_values
    list — we find the entry where label == "URL" and pull its value.

    Non-Instagram URLs are filtered out — the export sometimes contains
    YouTube or Facebook links from owner profiles mixed in.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f);

    urls = []
    for post in data:
        for item in post.get("label_values", []):
            if item.get("label") == "URL":
                url = item.get("value", "").strip()
                # Only keep Instagram reel URLs — skip owner profile links etc.
                if "instagram.com/reel" in url:
                    urls.append(url)
                break          # each post only has one URL entry — stop after finding it
    
    return urls

async def handle_bulk_onboarding(json_path: Path, update: Update) -> None:
    """
    Run the full ingest pipeline for every reel URL in the export file.

    Flow:
    1. Parse JSON → extract URLs
    2. For each URL:
       a. Skip if already indexed
       b. Download → analyze → store
       c. Sleep RATE_LIMIT_DELAY seconds to respect Gemini's RPM limit
       d. Send progress update every 10 reels
    3. Send a final summary
    """

    await update.message.reply_text("Parsing export file...")

    urls = extract_urls(json_path)
    total = len(urls)

    if total == 0:
        await update.message.reply_text(
            "No Instagram reel URLs found in the export file."
        )
        return
    
    await update.message.reply_text(
        f"Found {total} reels. Starting onboarding...\n"
        f"This will take a while — I'll update you every 10 reels."
    )

    processed = 0
    skipped = 0
    failed = 0

    for i, url in enumerate(urls, start=1):

        # Duplicate check — skip reels already in ChromaDB
        if is_already_indexed(url):
            skipped += 1
            continue

        try:
            video_path = download_reel(url)
            summary = analyze_video(video_path)
            store_reel(url, summary)

            # Clean up temp file immediately after storing
            video_path.unlink(missing_ok=True)
            video_path.parent.rmdir()

            processed += 1

            # Respect Gemini's RPM limit between calls
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"Failed to process {url}: {e}")
            failed += 1

        
        # Progress update every 10 reels
        if i % 10 == 0:
            await update.message.reply_text(
                f"Progress: {i} of {total} checked"
                f"\n{processed} indexed, {skipped} skipped, {failed} failed..."
            )

    # Final Summary
    await update.message.reply_text(
        f"Onboarding complete!\n\n"
        f"Total reels in export: {total}\n"
        f"Newly indexed: {processed}\n"
        f"Already indexed (skipped): {skipped}\n"
        f"Failed: {failed}"
    )
