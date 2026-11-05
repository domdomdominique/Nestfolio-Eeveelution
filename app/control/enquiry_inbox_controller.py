from app.control.enquiry_notification_controller import EnquiryNotificationController


class EnquiryInboxController:
    """Control: the two-pane Enquiries inbox (ID-21).

    Takes the enquiries a designer or customer can see and works out what the
    page shows: the All / Unread / Replied tabs, the search box, which
    conversation is open, and which ones have new messages. Opening a
    conversation marks only that one as seen, so the others keep their dot.
    """

    FILTERS = ("all", "unread", "replied")

    def open(self, user_id, enquiries, selected_id=None, show="all", search=""):
        notifications = EnquiryNotificationController()
        unread = notifications.unread_by_enquiry(user_id, enquiries)
        search = (search or "").strip()[:100]
        if search:
            enquiries = [e for e in enquiries if e.mentions(search)]
        enquiries = sorted(enquiries, key=lambda e: (e.last_activity, e.id), reverse=True)

        counts = {
            "all": len(enquiries),
            "unread": sum(1 for e in enquiries if unread.get(e.id)),
            "replied": sum(1 for e in enquiries if e.last_message_from_designer),
        }
        show = show if show in self.FILTERS else "all"
        if show == "unread":
            enquiries = [e for e in enquiries if unread.get(e.id)]
        elif show == "replied":
            enquiries = [e for e in enquiries if e.last_message_from_designer]

        selected = next((e for e in enquiries if e.id == selected_id), enquiries[0] if enquiries else None)
        if selected is not None:
            notifications.mark_seen(user_id, [selected])
        return {"enquiries": enquiries, "selected": selected, "unread": unread,
                "counts": counts, "show": show, "search": search}
