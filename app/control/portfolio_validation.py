from io import BytesIO
from pathlib import PurePath
import warnings

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTOS = 10


# ID-19 Photo rules: JPG or PNG, 5 MB each, at most 10, checked as real images.
def validated_photos(files, existing=0):
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
        filename = secure_filename(upload.filename)[:255]
        extension = PurePath(filename).suffix.lower()

        if extension not in (".jpg", ".jpeg", ".png"):
            raise ValueError("Only JPG and PNG photos are accepted.")

        data = upload.stream.read(MAX_PHOTO_BYTES + 1)

        if len(data) > MAX_PHOTO_BYTES:
            raise ValueError("Each photo must be 5 MB or smaller.")

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
