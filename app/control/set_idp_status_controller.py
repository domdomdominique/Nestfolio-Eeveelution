from app.control.idp_validation import clean_status
from app.entity.idp import IDP


class SetIDPStatusController:
    """Control: handles the Interior Designer 'Set IDP Status' use case (ID-11)."""

    def set(self, designer_id, idp_id, status):
        status = clean_status(status)
        idp = IDP.get_owned(idp_id, designer_id)
        if idp is None:
            raise LookupError("Project not found.")
        idp.set_current(status == "current")
        return idp
