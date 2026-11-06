from app.control.update_company_controller import company_image
from app.control.signup_validation import clean_email, clean_phone
from app.entity.designer_company import DesignerCompany
from app.entity.user_account import UserAccount


# ID-03 Add company information: name required, one record per designer.
class AddCompanyController:
    def has_company(self, account_id):
        account = UserAccount.get(account_id)
        return bool(account and account.company)

    def add(self, account_id, form, photo=None, cover=None):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise ValueError("Please log in as an active designer.")

        if account.company:
            raise ValueError(
                "You already have company information. "
                "Please update it instead."
            )

        company_name = (form.get("company_name") or "").strip()
        description = (form.get("description") or "").strip()
        address = (form.get("address") or "").strip()
        phone = (form.get("phone") or "").strip()
        email = (form.get("email") or "").strip()

        if not company_name:
            raise ValueError("Please enter your company name.")

        if len(company_name) > 150:
            raise ValueError(
                "Company name must be 150 characters or fewer."
            )

        if len(description) > 5000:
            raise ValueError(
                "Description must be 5000 characters or fewer."
            )

        if len(address) > 255:
            raise ValueError(
                "Address must be 255 characters or fewer."
            )

        if phone:
            phone = clean_phone(phone)

        if email:
            email = clean_email(email)

            if len(email) > 120:
                raise ValueError(
                    "Email must be 120 characters or fewer."
                )

        if account.name != company_name:  # the account is named after the company
            account.update_details(company_name, account.email, account.phone)

        return DesignerCompany.create(
            account_id=account.id,
            company_name=company_name,
            description=description,
            address=address,
            phone=phone,
            email=email,
            photo=company_image(photo),
            cover=company_image(cover),
        )