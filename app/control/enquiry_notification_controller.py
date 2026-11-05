from app.entity.enquiry import Enquiry
from app.entity.reply import EnquirySeen


class EnquiryNotificationController:
    """Control: new-message notifications for enquiries (ID-21).

    - Designer: a new enquiry, or a customer answering back, counts as new.
    - Customer: a designer's reply counts as new.
    Opening the enquiries page marks them as seen, which clears the badge.
    """

    def unread_by_enquiry(self, user_id, enquiries):
        seen = EnquirySeen.last_seen([e.id for e in enquiries], user_id)
        return {e.id: e.new_messages_for(user_id, seen.get(e.id)) for e in enquiries}

    def unread_count(self, user_id):
        """Number of conversations with something new: the number on the badge."""
        unread = self.unread_by_enquiry(user_id, Enquiry.for_person(user_id))
        return sum(1 for n in unread.values() if n)

    def mark_seen(self, user_id, enquiries):
        EnquirySeen.mark([e.id for e in enquiries], user_id)
