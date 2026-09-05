"""Standalone QR code generator for the patient-scheduler booking page.

Run directly to (re)generate the QR image:

    python generate_qr.py

The image is written to static/qr_code.png. It is intentionally not committed
to the repository (see .gitignore) because it should be regenerated for each
deployment with the correct public URL.
"""

import os

import qrcode

from config import BASE_URL

# The booking page URL encoded in the QR code. Derived from the shared
# BASE_URL constant so the app and the QR generator can never drift apart.
BOOKING_URL = f"{BASE_URL}/book"

# Where the generated image lives, resolved relative to this file so it works
# regardless of the current working directory.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
QR_PATH = os.path.join(STATIC_DIR, "qr_code.png")


def generate_qr(url=BOOKING_URL, path=QR_PATH):
    """Generate a QR code encoding ``url`` and save it as a PNG at ``path``."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image = qrcode.make(url)
    image.save(path)
    return path


if __name__ == "__main__":
    output_path = generate_qr()
    print(f"QR code for {BOOKING_URL} written to {output_path}")
