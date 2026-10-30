from app.control.portfolio_validation import validated_photos
from app.control.signup_validation import clean_email, clean_phone
from app.entity.designer_company import DesignerCompany
from app.entity.user_account import UserAccount


# ID-05 Update company information: same checks as ID-03, own record only.
class UpdateCompanyController:
    def update(self, account_id, form, photo=None):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        name = (form.get("company_name") or "").strip()
        description = (form.get("description") or "").strip()
        address = (form.get("address") or "").strip()
        phone = (form.get("phone") or "").strip()
        email = (form.get("email") or "").strip()

        if not name or len(name) > 150:
            raise ValueError(
                "Company name is required and must be "
                "150 characters or fewer."
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

        remove_photo = (
            form.get("remove_profile_photo") == "1"
        )

        if remove_photo and photo is not None and photo.filename:
            raise ValueError(
                "Choose either a new picture or remove the "
                "current picture, then save again."
            )

        photos = validated_photos(
            [photo] if photo is not None and photo.filename else []
        )

        return DesignerCompany.save(
            account,
            {
                "company_name": name,
                "description": description,
                "address": address,
                "phone": phone,
                "email": email,
            },
            photo=photos[0] if photos else None,
            remove_photo=remove_photo,
        )

    def view_photo(self, account_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        company = DesignerCompany.for_account(account_id)

        if company is None or company.profile_photo is None:
            raise LookupError("Company picture not found.")

        return company.profile_photo