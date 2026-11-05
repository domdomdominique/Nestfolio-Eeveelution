"""Short, friendly times for the Enquiries inbox: '2h', '3d', 'Today', '10:12 am'."""
from datetime import datetime, timedelta


def ago(when, now=None):
    """How long ago, as in the inbox list: 'now', '5m', '2h', '3d', '1w', or a date."""
    if when is None:
        return ""
    seconds = ((now or datetime.now()) - when).total_seconds()
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    if seconds < 7 * 86400:
        return f"{int(seconds // 86400)}d"
    if seconds < 5 * 7 * 86400:
        return f"{int(seconds // (7 * 86400))}w"
    return f"{when.day} {when:%b %Y}"


def clock(when):
    """'10:12 am'."""
    return f"{when.hour % 12 or 12}:{when:%M} {'am' if when.hour < 12 else 'pm'}"


def day_label(when, today=None):
    """Divider above each day's messages: 'Today', 'Yesterday' or 'Mon 3 Nov 2026'."""
    today = today or datetime.now().date()
    if when.date() == today:
        return "Today"
    if when.date() == today - timedelta(days=1):
        return "Yesterday"
    return f"{when:%a} {when.day} {when:%b %Y}"


def initials(name):
    words = [w for w in (name or "?").replace("&", " ").split() if w[:1].isalnum()]
    return "".join(w[0] for w in words[:2]).upper() or "?"
