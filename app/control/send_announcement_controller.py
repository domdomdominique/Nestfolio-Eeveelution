from app.entity.announcement import Announcement
from app.entity.user_profile import UserProfile

MAX_TITLE_LENGTH = 150


class SendAnnouncementController:
    """Control: handles the User Admin 'Send announcements' use case (UA-18).

    An announcement goes to every user, or only to the roles (user profiles) the
    User Admin picks. Each user sees the ones meant for them on their home page
    (latest()), and the User Admin can see past ones (history()).
    """

    def send(self, admin_id, title, message, roles=None):
        """roles=None (or empty) sends to everyone; otherwise a list of profile keys."""
        title, message = (title or "").strip(), (message or "").strip()
        if not title or not message:
            raise ValueError("Please enter both a title and a message.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
        return Announcement.send(admin_id, title, message, self._clean_roles(roles))

    @staticmethod
    def _clean_roles(roles):
        if roles is None:
            return []
        chosen = list(dict.fromkeys(r for r in roles if r))  # unique, in order
        if not chosen:
            raise ValueError("Please choose at least one role to send this announcement to.")
        known = [p.key for p in UserProfile.active()]
        if any(role not in known for role in chosen):
            raise ValueError("Please choose roles from the list.")
        # Every role ticked is the same as everyone (and also covers roles added later)
        return [] if set(chosen) == set(known) else [r for r in known if r in chosen]

    def role_choices(self):
        """[(key, name)] of the active profiles an announcement can be pushed to."""
        return [(p.key, p.name) for p in UserProfile.active()]

    @staticmethod
    def role_names():
        """{key: name} for every profile, to label who past announcements went to."""
        return {p.key: p.name for p in UserProfile.list_all()}

    def remove(self, announcement_id):
        """Take an announcement off every home page."""
        if not Announcement.delete_by_id(announcement_id):
            raise ValueError("Announcement not found.")

    def history(self):
        return Announcement.latest()

    def latest(self, limit=3, role=None):
        """The newest announcements this role should see (all of them when role is None)."""
        return Announcement.latest(limit, role)
