import base64
import os
from email.utils import parsedate_to_datetime
from datetime import datetime


def decode_base64(data_b64: str) -> bytes:
    """Decode base64, padding being optional.

    :param data_b64: Base64 data as an ASCII byte string
    :returns: The decoded byte string.
    """

    missing_padding = len(data_b64) % 4
    if missing_padding:
        data_b64 += "=" * (4 - missing_padding)

    # Decode the base64 email data
    raw_data = base64.urlsafe_b64decode(data_b64).decode("utf-8")

    return raw_data


def sanitize_filename(filename):
    """Sanitize filename to be safe for file system."""
    if not filename:
        return "unnamed_attachment"

    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")

    # Limit filename length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[: 200 - len(ext)] + ext

    return filename


def parse_email_date(date_str: str) -> str:
    """Parse email date string to ISO format."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        return datetime.utcnow().isoformat()
