from app.control.signup_validation import (
    check_password, clean_about, clean_email, clean_experience, clean_phone, clean_portfolio_url, clean_uen,
)
from app.control.phone_check import ensure_phone_free
from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


# ID-15 Register as an interior designer: creates a Pending application for the User Admin (UA-14, UA-15).
class ApplyDesignerController:
    """Control: handles the Interior Designer 'Apply for account' use case."""

    def apply(self, company_name, email, phone, password, confirm_password,
              uen, experience_years="0", portfolio_url="", description=""):
        """A designer account is a company account, so the company name is also the account name."""
        email = clean_email(email)
        phone = clean_phone(phone)
        check_password(password, confirm_password)
        company_name = (company_name or "").strip()
        if not company_name:
            raise ValueError("Please enter your company name.")
        uen = clean_uen(uen)
        experience_years = clean_experience(experience_years)
        portfolio_url = clean_portfolio_url(portfolio_url)
        description = clean_about(description)

        if UserAccount.email_exists(email):
            raise ValueError("Email already registered.")
        if DesignerApplication.has_pending(email):
            raise ValueError("You already have an application waiting for review.")
        ensure_phone_free(phone)
        if DesignerApplication.uen_in_use(uen):
            raise ValueError("This UEN is already registered or waiting for review.")

        return DesignerApplication.submit(
            company_name, email, phone, password, company_name, uen,
            portfolio_url=portfolio_url,
            experience_years=experience_years,
            description=description,
        )
