import logging
import os
import tempfile

import ffmpeg

from supa import download, rest, upload

log = logging.getLogger("story-worker")

# iOS AVPlayer cannot play the WebM that the Hearth browser records.
WEBM_ROWS = [("select", "id,original_path"), ("status", "eq.ready"), ("original_path", "like.*.webm"), ("limit", "10")]
failed = set()


def to_m4a(src, dest):
    stream = ffmpeg.output(ffmpeg.input(src), dest, acodec="aac", audio_bitrate="80k", vn=None, movflags="+faststart")
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg m4a failed: {e.stderr.decode()[-300:]}")
    return dest


def fix_webm():
    """Transcode ready WebM originals to m4a next to the original and point original_path at the m4a."""
    for row in rest("GET", WEBM_ROWS):
        if row["id"] in failed:
            continue
        webm = row["original_path"]
        m4a = webm[: -len(".webm")] + ".m4a"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = download("audio", webm, os.path.join(tmp, "in.webm"))
                upload(m4a, to_m4a(src, os.path.join(tmp, "out.m4a")), "audio/mp4", bucket="audio")
            rest("PATCH", [("id", "eq." + row["id"]), ("original_path", "eq." + webm)], {"original_path": m4a})
            log.info("[%s] original audio now %s", row["id"], m4a)
        except Exception as e:
            failed.add(row["id"])
            log.error("[%s] webm to m4a failed: %s", row["id"], e)
