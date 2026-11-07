from io import BytesIO
from pathlib import PurePath
import warnings

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


MAX_PHOTO_BYTES = 5 * 1024 * 1024        # company profile picture and background
IDP_MAX_PHOTO_BYTES = 10 * 1024 * 1024   # IDP photos and IDP category backgrounds
MAX_PHOTOS = 10


def safe_upload_name(filename):
    """(safe file name, lower-case extension). The extension is read from the name the user chose:
    secure_filename drops non-ASCII letters, so "报告.pdf" would otherwise lose its ".pdf"."""
    path = PurePath((filename or "").strip())
    extension = path.suffix.lower()
    return ((secure_filename(path.stem)[:240] or "file") + extension)[:255], extension


# ID-19 Photo rules: JPG or PNG, at most max_bytes each (10 MB for IDP photos), at most 10,
# checked as real images.
def validated_photos(files, existing=0, max_bytes=MAX_PHOTO_BYTES):
    files = [
        upload for upload in files
        if upload and upload.filename
    ]

    if existing + len(files) > MAX_PHOTOS:
        raise ValueError(
            "A project can have at most 10 photos."
        )

    photos = []

    for upload in files:
        filename, extension = safe_upload_name(upload.filename)

        if extension not in (".jpg", ".jpeg", ".png"):
            raise ValueError("Only JPG and PNG photos are accepted.")

        data = upload.stream.read(max_bytes + 1)

        if len(data) > max_bytes:
            raise ValueError(
                f"Each photo must be {max_bytes // (1024 * 1024)} MB or smaller."
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error",
                    Image.DecompressionBombWarning,
                )

                with Image.open(BytesIO(data)) as image:
                    kind = image.format

                    if kind not in ("JPEG", "PNG"):
                        raise ValueError(
                            "Only JPG and PNG photos are accepted."
                        )

                    if image.width * image.height > 20_000_000:
                        raise ValueError(
                            "Photos must be 20 megapixels or smaller."
                        )

                    if (kind == "PNG") != (extension == ".png"):
                        raise ValueError(
                            "The photo must match its file extension."
                        )

                    image.verify()

                with Image.open(BytesIO(data)) as image:
                    image.load()

        except (
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise ValueError(
                "One of the files is not a valid JPG or PNG photo."
            )

        photos.append({
            "filename": filename,
            "content_type": (
                "image/png" if kind == "PNG" else "image/jpeg"
            ),
            "data": data,
        })

    return photos
