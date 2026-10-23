from app.entity.favourite import Favourite
from app.entity.idp import IDP


class ViewIDPController:
    def view(
        self,
        idp_id,
        customer_id=None,
        viewer_role=None,
        record=True,
    ):
        idp = IDP.get(idp_id)

        if idp is None or not idp.is_visible:
            raise LookupError("Project not found.")

        # Count customers and signed-out visitors.
        # Designer and staff previews do not count.
        if record and viewer_role in (None, "customer"):
            idp.record_view()

        saved_ids = (
            Favourite.saved_idp_ids(customer_id)
            if customer_id
            else set()
        )

        return {
            "idp": idp,
            "designer": idp.designer,
            "project_count": IDP.count_for_designer(
                idp.designer_id
            ),
            "more": IDP.more_by_designer(
                idp.designer_id,
                idp.id,
            ),
            "saved": idp.id in saved_ids,
            "saved_ids": saved_ids,
        }