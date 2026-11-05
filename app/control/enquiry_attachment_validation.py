from app.control.portfolio_validation import safe_upload_name, validated_photos

MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
ACCEPT = ".jpg,.jpeg,.png,.pdf"  # for the file input's accept attribute


# C-16 Enquiry attachments: up to 5 JPG, PNG or PDF files, 5 MB each, checked by content.
def validated_attachments(files):
    """Return [{filename, content_type, size, data}] or raise ValueError with a message for the customer."""
    files = [upload for upload in files if upload and upload.filename]
    if len(files) > MAX_ATTACHMENTS:
        raise ValueError(f"You can attach at most {MAX_ATTACHMENTS} files.")

    attachments = []
    for upload in files:
        extension = safe_upload_name(upload.filename)[1]
        if extension == ".pdf":
            attachments.append(_pdf(upload))
        elif extension in (".jpg", ".jpeg", ".png"):
            # Same checks as project photos: a real image, the right type, not oversized
            try:
                photo = validated_photos([upload])[0]
            except ValueError:
                raise ValueError(f"“{upload.filename}” is not a valid JPG or PNG image under 5 MB.") from None
            attachments.append({**photo, "size": len(photo["data"])})
        else:
            raise ValueError("Only JPG, PNG and PDF files can be attached.")
    return attachments


def _pdf(upload):
    filename = safe_upload_name(upload.filename)[0]
    data = upload.stream.read(MAX_ATTACHMENT_BYTES + 1)
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("Each file must be 5 MB or smaller.")
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"“{upload.filename}” is not a valid PDF file.")
    return {"filename": filename, "content_type": "application/pdf", "size": len(data), "data": data}
