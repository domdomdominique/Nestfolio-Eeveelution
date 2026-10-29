from app.entity.announcement import Announcement

MAX_TITLE_LENGTH = 150


class SendAnnouncementController:
    """Control: handles the User Admin 'Send announcements' use case (UA-18).

    Announcements are shown to every user on their home page after logging
    in (latest()), and the User Admin can see past ones (history()).
    """

    def send(self, admin_id, title, message):
        title, message = (title or "").strip(), (message or "").strip()
        if not title or not message:
            raise ValueError("Please enter both a title and a message.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
        return Announcement.send(admin_id, title, message)

    def history(self):
        return Announcement.latest()

    def latest(self, limit=3):
        return Announcement.latest(limit)
