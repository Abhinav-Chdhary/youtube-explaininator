import re
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",  # bare video ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def fetch_transcript(video_id: str) -> list[dict]:
    """Fetch transcript entries from YouTube.

    Returns list of {'text': str, 'start': float, 'duration': float}.
    Tries manual captions first, then falls back to auto-generated.
    """
    ytt = YouTubeTranscriptApi()

    # Try fetching directly (prefers manual captions)
    try:
        transcript = ytt.fetch(video_id)
        return [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in transcript
        ]
    except Exception:
        pass

    # Fallback: list all transcripts and pick the first available
    try:
        transcript_list = ytt.list(video_id)
        for t in transcript_list:
            fetched = t.fetch()
            return [
                {"text": s.text, "start": s.start, "duration": s.duration}
                for s in fetched
            ]
    except Exception:
        pass

    raise ValueError(f"No transcript available for video: {video_id}")


def clean_text(text: str) -> str:
    """Remove noise markers and normalize whitespace."""
    text = re.sub(r"\[.*?\]", "", text)      # [Music], [Applause]
    text = re.sub(r"\(.*?\)", "", text)       # (music playing)
    text = re.sub(r"♪.*?♪", "", text)         # ♪ music notes ♪
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_transcript(
    transcript: list[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Split transcript into overlapping chunks, preserving sentence boundaries.

    Returns list of {'text': str, 'start_time': float, 'end_time': float}.
    """
    if not transcript:
        return []

    # Build list of cleaned sentences with their timestamps
    segments: list[dict] = []
    for entry in transcript:
        cleaned = clean_text(entry["text"])
        if cleaned:
            segments.append({
                "text": cleaned,
                "start": entry["start"],
                "end": entry["start"] + entry.get("duration", 0),
            })

    # Group segments into chunks respecting size limits
    chunks: list[dict] = []
    current_texts: list[str] = []
    current_start: float = segments[0]["start"] if segments else 0
    current_end: float = 0
    current_len: int = 0

    for seg in segments:
        seg_len = len(seg["text"])

        if current_len + seg_len > chunk_size and current_texts:
            # Emit current chunk
            chunks.append({
                "text": " ".join(current_texts),
                "start_time": current_start,
                "end_time": current_end,
            })

            # Keep tail segments for overlap
            overlap_texts: list[str] = []
            overlap_len = 0
            for t in reversed(current_texts):
                if overlap_len + len(t) > chunk_overlap:
                    break
                overlap_texts.insert(0, t)
                overlap_len += len(t)

            current_texts = overlap_texts
            current_start = seg["start"]
            current_len = overlap_len

        current_texts.append(seg["text"])
        current_end = seg["end"]
        current_len += seg_len

    # Final chunk
    if current_texts:
        chunks.append({
            "text": " ".join(current_texts),
            "start_time": current_start,
            "end_time": current_end,
        })

    return chunks


def get_video_metadata(video_id: str) -> dict:
    """Return basic metadata dict for a video."""
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }
