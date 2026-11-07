import io

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app import create_app
from app.entity.db import db as _db


def png_bytes(size=(4, 4)):
    out = io.BytesIO()
    Image.new("RGB", size, "white").save(out, "PNG")
    return out.getvalue()


def png_upload(filename="background.png"):
    """A small valid PNG as an uploaded file (e.g. a category background, PM-03)."""
    return FileStorage(io.BytesIO(png_bytes()), filename=filename, content_type="image/png")


def png_field(filename="background.png"):
    """The same PNG as a test-client form field: data={"photo": png_field()}."""
    return (io.BytesIO(png_bytes()), filename)


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
