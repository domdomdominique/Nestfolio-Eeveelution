from io import BytesIO
from pathlib import PurePath
import warnings

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from app.entity.idp import IDP


MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTOS = 10


def project_details(form):
    title = (form.get("title") or "").strip()
    description = (form.get("description") or "").strip()
    category = form.get("category")
    status = form.get("status")

    if not title or len(title) > 150:
        raise ValueError(
            "Title is required and must be 150 characters or fewer."
        )

    if len(description) > 5000:
        raise ValueError(
            "Description must be 5000 characters or fewer."
        )

    if category not in IDP.CATEGORIES:
        raise ValueError("Please select an existing category.")

    if status not in ("current", "past"):
        raise ValueError("Please select Current or Past.")

    return {
        "title": title,
        "description": description,
        "category": category,
        "is_current": status == "current",
    }


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