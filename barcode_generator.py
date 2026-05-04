"""Barcode utilities for product labels.

This module keeps barcode support optional. If python-barcode or Pillow are not
installed yet, callers get a clear error instead of crashing at import time.
"""

from io import BytesIO


def generate_barcode_image(code, writer_options=None):
    """Return a Pillow image for a Code128 barcode."""
    try:
        import barcode
        from barcode.writer import ImageWriter
    except Exception as exc:
        raise RuntimeError("python-barcode and Pillow are required for barcode generation") from exc

    value = str(code or "").strip()
    if not value:
        value = "AUTO"

    options = {
        "module_height": 12,
        "font_size": 10,
        "text_distance": 2,
        "quiet_zone": 3,
        "write_text": True,
    }
    if writer_options:
        options.update(writer_options)

    barcode_cls = barcode.get_barcode_class("code128")
    output = BytesIO()
    barcode_cls(value, writer=ImageWriter()).write(output, options)
    output.seek(0)

    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Pillow is required for barcode preview") from exc

    return Image.open(output)
