from __future__ import annotations

import re

import pandas as pd


MESSAGE_HEADER = re.compile(
    r"^(?:\[)?"
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?)"
    r"(?:\]\s*|\s+-\s+)"
    r"(?P<content>.*)$"
)

MEDIA_MARKERS = (
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "document omitted",
    "sticker omitted",
)


def parse_whatsapp_chat(chat_text: str, dayfirst: bool = True) -> pd.DataFrame:
    """
    Convert WhatsApp export text into a structured Pandas DataFrame.

    Expected output columns:
    timestamp, sender, message, is_system, has_media
    """
    records = []
    current_record = None

    for line in chat_text.splitlines():
        match = MESSAGE_HEADER.match(line)

        if match:
            content = match.group("content").strip()
            timestamp_text = f"{match.group('date')} {match.group('time')}"

            if ": " in content:
                sender, message = content.split(": ", maxsplit=1)
                is_system = False
            else:
                sender = None
                message = content
                is_system = True

            current_record = {
                "timestamp": timestamp_text,
                "sender": sender.strip() if sender else None,
                "message": message.strip(),
                "is_system": is_system,
            }
            records.append(current_record)

        elif current_record is not None:
            # WhatsApp messages can continue on multiple lines.
            current_record["message"] += f"\n{line}"

    df = pd.DataFrame(records)

    if df.empty:
        return pd.DataFrame(
            columns=["timestamp", "sender", "message", "is_system", "has_media"]
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        dayfirst=dayfirst,
        errors="coerce",
    )

    df["has_media"] = df["message"].str.lower().apply(
        lambda message: any(marker in message for marker in MEDIA_MARKERS)
    )

    return df