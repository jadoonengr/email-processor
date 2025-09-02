import base64

def decode_base64(data_b64: str) -> bytes:
    """Decode base64, padding being optional.

    :param data_b64: Base64 data as an ASCII byte string
    :returns: The decoded byte string.
    """

    missing_padding = len(data_b64) % 4
    if missing_padding:
        data_b64 += '=' * (4 - missing_padding)

    # Decode the base64 email data
    raw_data = base64.urlsafe_b64decode(data_b64).decode('utf-8')

    return raw_data


        