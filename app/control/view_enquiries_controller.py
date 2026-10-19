from app.entity.enquiry import Enquiry


class ViewEnquiriesController:
    """Control: handles the Interior Designer 'View enquiries' use case (ID-21).

    Customers send enquiries through SendEnquiryController (C-16); this is
    where they show up for the designer.
    """

    def view(self, designer_id):
        return Enquiry.for_designer(designer_id)

    def count(self, designer_id):
        return Enquiry.count_for_designer(designer_id)
