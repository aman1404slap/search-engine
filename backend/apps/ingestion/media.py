"""Media helpers: duration string parsing and ffmpeg-based thumbnail generation."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def parse_duration_string(duration_str: str | None) -> float | None:
    """Parse a "H:MM:SS" or "M:SS" duration string into total seconds.

    Returns None on missing/unparseable input. Never raises.
    """
    if not duration_str or not isinstance(duration_str, str):
        return None

    parts = duration_str.strip().split(":")
    if not (2 <= len(parts) <= 3):
        return None

    try:
        parts_f = [float(p) for p in parts]
    except ValueError:
        return None

    try:
        if len(parts_f) == 3:
            hours, minutes, seconds = parts_f
        else:
            hours = 0.0
            minutes, seconds = parts_f
        return hours * 3600.0 + minutes * 60.0 + seconds
    except Exception:
        return None


def generate_thumbnail(source_url: str, output_path: str, at_seconds: float = 2.0, timeout: int = 30) -> bool:
    """Extract a single frame from source_url at at_seconds into output_path via ffmpeg.

    Returns True on success (file written and non-empty), False on any failure.
    Never raises -- errors are logged only, so this degrades gracefully when there's
    no network/AWS access at all.
    """
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(at_seconds),
            "-i", source_url,
            "-frames:v", "1",
            "-q:v", "3",
            output_path,
        ]
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
        )
        if result.returncode != 0:
            logger.error(
                "generate_thumbnail: ffmpeg exited %s for %s: %s",
                result.returncode,
                output_path,
                result.stderr.decode(errors="replace")[-2000:] if result.stderr else "",
            )
            return False

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            logger.error("generate_thumbnail: output file missing or empty: %s", output_path)
            return False

        return True
    except subprocess.TimeoutExpired:
        logger.error("generate_thumbnail: timed out after %ss for %s", timeout, output_path)
        return False
    except Exception as exc:
        logger.error("generate_thumbnail: unexpected error for %s: %s", output_path, exc)
        return False
