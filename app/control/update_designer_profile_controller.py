from app.control.phone_check import ensure_phone_free
from app.control.signup_validation import (
    clean_about, clean_email, clean_experience, clean_phone, clean_portfolio_url,
)
from app.entity.designer_application import DesignerApplication
from app.entity.designer_company import DesignerCompany
from app.entity.user_account import UserAccount


class UpdateDesignerProfileController:
    """Control: handles the Interior Designer 'Edit ID Profile' use case (ID-18).

    A designer account is a company account, so the profile holds the company information
    given at sign-up (ID-15). Needs the current password, the same as the customer profile (C-12).
    """

    def update(self, account_id, company_name, email, phone, current_password,
               experience_years=None, portfolio_url=None, description=None):
        account = UserAccount.get(account_id)
        if account is None or account.role != "designer":
            raise LookupError("Account not found.")
        if not account.check_password(current_password):
            raise ValueError("Your current password is incorrect.")
        company_name = (company_name or "").strip()
        if not company_name:
            raise ValueError("Please enter your company name.")
        if len(company_name) > 150:
            raise ValueError("Company name must be 150 characters or fewer.")
        email = clean_email(email)
        phone = clean_phone(phone)
        details = {"company_name": company_name}
        if experience_years is not None:
            details["experience_years"] = clean_experience(experience_years)
        if portfolio_url is not None:
            details["portfolio_url"] = clean_portfolio_url(portfolio_url)
        if description is not None:
            details["description"] = clean_about(description)
        if email != account.email and (UserAccount.email_exists(email)
                                       or DesignerApplication.has_pending(email)):
            raise ValueError("That email is already used by another account.")
        ensure_phone_free(phone, account_id=account.id)

        account.update_details(company_name, email, phone)
        # Keep the public company record (ID-03 to ID-05) in step with the account.
        DesignerCompany.save(account, details)
        return account

    def company_information(self, account):
        """What the Company information form shows: the company record, or the sign-up answers."""
        source = account.company or account.designer_application
        return {
            "company_name": account.name,
            "email": account.email,
            "phone": account.phone or "",
            "uen": getattr(source, "uen", "") or "",
            "experience_years": getattr(source, "experience_years", 0) or 0,
            "portfolio_url": getattr(source, "portfolio_url", "") or "",
            "description": getattr(source, "description", "") or "",
        }
