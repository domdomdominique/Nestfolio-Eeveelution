import pytest

from app import create_app
from app.entity.user_account import UserAccount


@pytest.mark.parametrize("days", [7, 30])
def test_trends_shows_no_data_message(days):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    with app.app_context():
        UserAccount.create(
            "trends-test@example.com",
            "password123",
            "designer",
            name="Trends Test Designer",
        )

        client = app.test_client()

        login = client.post("/login", data={
            "email": "trends-test@example.com",
            "password": "password123",
            "role": "designer",
        })
        assert login.status_code == 302

        response = client.get(
            f"/designer/trends?days={days}"
        )

        assert response.status_code == 200
        assert (
            f"No trend data for the last {days} days yet."
            in response.get_data(as_text=True)
        )