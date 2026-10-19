from app.entity.favourite import Favourite
from app.entity.idp import IDP


class SaveFavouriteController:
    """Control: handles the Customer 'Favourite IDPs' use case (C-07)."""

    def save(self, customer_id, idp_id):
        """Returns (idp, added); added is False if the IDP was already in the list."""
        idp = IDP.get(idp_id)
        if idp is None or not idp.is_visible:
            raise LookupError("Project not found.")
        return idp, Favourite.add(customer_id, idp)
