"""Extract embedded raster images from a PDF (PyMuPDF), normalised to PNG.

Returns the images that are actually stored *inside* the PDF (photos, logos, raster
figures/charts) — not page screenshots. Vector-drawn graphics/tables are not image objects
and won't appear here. Each image is converted to PNG (so the browser can always render it),
deduplicated by content hash, and tagged with the page it appears on.
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    page_number: int  # 1-based
    image_index: int
    data: bytes       # PNG bytes
    ext: str          # always "png"
    width: int
    height: int
    sha256: str


def extract_embedded_images(pdf_path: str, min_dimension: int = 64) -> list[ExtractedImage]:
    import fitz  # PyMuPDF
    from PIL import Image

    images: list[ExtractedImage] = []
    seen: set[str] = set()

    with fitz.open(pdf_path) as doc:
        for page_index in range(len(doc)):
            page = doc[page_index]
            for image_index, info in enumerate(page.get_images(full=True)):
                xref = info[0]
                try:
                    base = doc.extract_image(xref)
                    pil = Image.open(io.BytesIO(base["image"]))
                    pil.load()
                except Exception:  # noqa: BLE001 - skip anything PyMuPDF/PIL can't decode
                    continue

                width, height = pil.size
                if width < min_dimension or height < min_dimension:
                    continue

                if pil.mode not in ("RGB", "L"):
                    pil = pil.convert("RGB")
                buffer = io.BytesIO()
                pil.save(buffer, format="PNG")
                data = buffer.getvalue()

                digest = hashlib.sha256(data).hexdigest()
                if digest in seen:  # same logo repeated across pages -> keep one
                    continue
                seen.add(digest)

                images.append(
                    ExtractedImage(
                        page_number=page_index + 1,
                        image_index=image_index,
                        data=data,
                        ext="png",
                        width=width,
                        height=height,
                        sha256=digest,
                    )
                )

    return images
