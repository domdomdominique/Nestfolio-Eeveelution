"""The +65 field accepts a pasted full number, and an email cannot be absurdly long."""
import re

import pytest

from app.control.signup_validation import clean_email, clean_phone


def test_phone_field_has_no_length_cap_and_accepts_a_pasted_plus_65(client):
    page = client.get("/register").get_data(as_text=True)
    tag = re.search(r'<input name="phone"[^>]*>', page, re.S).group(0)
    assert "maxlength" not in tag
    pattern = re.compile("^(?:" + re.search(r'pattern="([^"]+)"', tag).group(1) + ")$")
    for ok in ("9123 4567", "91234567", "+65 9123 4567", "+6591234567", "9123-4567"):
        assert pattern.match(ok), ok
        assert clean_phone(ok) == "+65 91234567"  # the server agrees with the browser
    for bad in ("5123 4567", "9123 456", "+65 5123 4567"):
        assert not pattern.match(bad), bad


def test_email_longer_than_120_characters_is_rejected():
    assert clean_email("a" * 100 + "@b.com")
    with pytest.raises(ValueError):
        clean_email("a" * 120 + "@b.com")
