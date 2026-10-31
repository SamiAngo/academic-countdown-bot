#!/usr/bin/env python3
"""
🎓 Academic Countdown Bot
Runs on GitHub Actions every hour. No server, no hosting, no cost.

Every run it:
  1. Reads new private messages sent to the bot and handles commands (admin only).
  2. Removes events whose date has already passed.
  3. Posts the countdown to the channel once a day, at the first run after POST_HOUR.
  4. Saves everything to data/events.json (the workflow commits it back to GitHub).

Only Python's standard library is used, so there is nothing to install.
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ─── Settings you can change ──────────────────────────────────────────────
POST_HOUR = 8                              # Daily post goes out after this hour (local time)
LOCAL_TZ = timezone(timedelta(hours=3))    # Ethiopia (Africa/Addis_Ababa): UTC+3, no daylight saving
MAX_EVENTS_IN_POST = 15                    # Keeps the channel message readable

CATEGORY_EMOJI = {
    "exam": "📝",
    "quiz": "❓",
    "assignment": "📚",
    "project": "💻",
    "presentation": "🎤",
    "other": "📌",
}

# Used to guess the category when you don't type one (checked in this order)
CATEGORY_KEYWORDS = [
    ("quiz", ["quiz"]),
    ("project", ["project"]),
    ("assignment", ["assignment", "homework", "hw", "lab", "report", "worksheet"]),
    ("presentation", ["presentation", "seminar", "defense", "defence", "pitch"]),
    ("exam", ["exam", "midterm", "mid", "final", "test"]),
]

QUOTES = [
    "Small progress every day adds up to big results.",
    "You don't have to be extreme, just consistent.",
    "Future you is watching. Make them proud.",
    "One focused hour beats five distracted ones.",
    "Discipline is choosing what you want most over what you want now.",
    "Start before you feel ready.",
    "The best time to study was yesterday. The next best time is today.",
    "Done is better than perfect. Start, then improve.",
    "Every page you read today is a page you won't panic over later.",
    "Hard work compounds. Keep stacking days.",
    "Your only competition is who you were yesterday.",
    "Exams test what you practiced, not what you planned to practice.",
    "Rest if you must, but don't quit.",
    "Make today count. Tomorrow will thank you.",
]

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# ─── Secrets (GitHub → Settings → Secrets and variables → Actions) ────────
missing = [name for name in ("BOT_TOKEN", "CHANNEL_ID", "ADMIN_ID") if not os.environ.get(name)]
if missing:
    sys.exit(f"❌ Missing secret(s): {', '.join(missing)}. See the README, step 5.")

BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHANNEL_ID = os.environ["CHANNEL_ID"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"].strip())
FORCE_POST = os.environ.get("FORCE_POST", "false").lower() == "true"

DATA_FILE = Path(__file__).resolve().parent / "data" / "events.json"
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"


# ─── Telegram ─────────────────────────────────────────────────────────────
def tg(method, **params):
    """Call a Telegram Bot API method and return the JSON response."""
    request = urllib.request.Request(
        API + method,
        data=json.dumps(params).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Telegram {method} failed: {error.read().decode()}") from None


def send(chat_id, text):
    tg(
        "sendMessage",
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        link_preview_options={"is_disabled": True},
    )


def reply(chat_id, text):
    """Reply to the admin without crashing the whole run if it fails."""
    try:
        send(chat_id, text)
    except Exception as error:
        print(f"⚠️ Could not reply: {error}")


# ─── Database (data/events.json) ──────────────────────────────────────────
def load_db():
    db = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {}
    db.setdefault("last_update_id", 0)
    db.setdefault("last_post_date", "")
    db.setdefault("next_id", 1)
    db.setdefault("events", [])
    return db


def save_db(db):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_event(db, event_id):
    return next((e for e in db["events"] if e["id"] == event_id), None)


# ─── Small helpers ────────────────────────────────────────────────────────
def esc(text):
    return html.escape(text, quote=False)


def days_left(event, today):
    return (date.fromisoformat(event["date"]) - today).days


def in_days(days):
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def pretty_date(d, short=False):
    return f"{d:%a}, {d.day} {d:%b}" if short else f"{d:%A}, {d.day} {d:%B %Y}"


def event_title(event):
    star = " ⭐" if event.get("important") else ""
    return f"{CATEGORY_EMOJI.get(event['category'], '📌')} <b>{esc(event['name'])}</b>{star}"


def guess_category(name):
    words = re.findall(r"[a-z]+", name.lower())
    for category, keywords in CATEGORY_KEYWORDS:
        if any(word in keywords for word in words):
            return category
    return "other"


def parse_date(text, today):
    """Understands: 2026-11-15, 15/11/2026, Nov 15, 15 November, 15th Nov,
    today, tomorrow, in 10 days, in 2 weeks, friday, next friday."""
    t = " ".join(text.replace(",", " ").split()).lower()
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", t)

    if t == "today":
        return today
    if t == "tomorrow":
        return today + timedelta(days=1)

    match = re.fullmatch(r"in (\d+) (days?|weeks?)", t)
    if match:
        amount = int(match.group(1))
        return today + timedelta(days=amount * 7 if match.group(2).startswith("week") else amount)

    match = re.fullmatch(r"(?:next |this )?(" + "|".join(WEEKDAYS) + ")", t)
    if match:
        ahead = (WEEKDAYS.index(match.group(1)) - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            pass

    # No year typed: pick the next time that date comes around
    for fmt in ("%B %d", "%b %d", "%d %B", "%d %b", "%d/%m"):
        for year in (today.year, today.year + 1):
            try:
                d = datetime.strptime(f"{t} {year}", f"{fmt} %Y").date()
            except ValueError:
                break
            if d >= today:
                return d
    return None


# ─── Admin commands ───────────────────────────────────────────────────────
HELP_TEXT = """🤖 <b>Academic Countdown Bot</b>

<b>➕ Add an event</b>
<code>/add Name | Date</code>
<code>/add Name | Date | category | important</code>

<b>Examples</b>
<code>/add Numerical Analysis Midterm | Nov 15</code>
<code>/add Database Project | 2026-12-01 | project | important</code>
<code>/add Statistics Quiz | next friday</code>

<b>📅 Dates I understand</b>
2026-11-15 · 15/11/2026 · Nov 15 · 15 November · tomorrow · in 10 days · next friday

<b>🏷 Categories</b>
exam · quiz · assignment · project · presentation · other
If you leave it out, I'll guess from the name.

<b>⚙️ Other commands</b>
/list – all events with their numbers
/done 3 – mark event #3 as finished
/delete 3 – remove event #3
/post – post the countdown to the channel now
/help – show this message

⏱ I wake up once an hour, so my replies can take up to an hour."""


def cmd_help(db, args, today):
    return HELP_TEXT


def cmd_add(db, args, today):
    parts = [p.strip() for p in args.split("|") if p.strip()]
    if len(parts) < 2:
        return ("⚠️ Use this format:\n<code>/add Name | Date</code>\n\n"
                "Example:\n<code>/add Numerical Analysis Midterm | Nov 15</code>")

    name, date_text, extras = parts[0], parts[1], [p.lower() for p in parts[2:]]
    event_date = parse_date(date_text, today)
    if event_date is None:
        return (f"🤔 I couldn't understand the date “{esc(date_text)}”.\n"
                "Try <code>2026-11-15</code>, <code>15/11/2026</code>, <code>Nov 15</code>, "
                "<code>tomorrow</code> or <code>in 10 days</code>.")
    if event_date < today:
        return f"⏪ {pretty_date(event_date)} is already in the past."

    category, important = None, False
    for extra in extras:
        if extra in CATEGORY_EMOJI:
            category = extra
        elif extra in ("important", "!", "⭐", "star"):
            important = True
        else:
            return (f"🤔 I don't know “{esc(extra)}”.\n"
                    f"Categories: {', '.join(CATEGORY_EMOJI)}. Or write <code>important</code>.")

    event = {
        "id": db["next_id"],
        "name": name,
        "date": event_date.isoformat(),
        "category": category or guess_category(name),
        "important": important,
        "completed": False,
        "added": today.isoformat(),
    }
    db["events"].append(event)
    db["next_id"] += 1

    days = days_left(event, today)
    return (f"✅ <b>Event added!</b>  <code>#{event['id']}</code>\n\n"
            f"{event_title(event)}\n"
            f"📅 {pretty_date(event_date)}\n"
            f"⏳ {in_days(days).capitalize()}\n\n"
            "It'll show up in the channel countdown.")


def cmd_list(db, args, today):
    if not db["events"]:
        return ("📭 No events yet.\n\nAdd one with:\n"
                "<code>/add Statistics Final | Dec 20</code>")

    lines = ["📋 <b>Your events</b>", ""]
    for event in sorted(db["events"], key=lambda e: e["date"]):
        number = f"<code>#{event['id']}</code>"
        if event["completed"]:
            lines.append(f"{number} ✅ <s>{esc(event['name'])}</s>")
        else:
            when = pretty_date(date.fromisoformat(event["date"]), short=True)
            lines.append(f"{number} {event_title(event)}\n        {when} · {in_days(days_left(event, today))}")
    lines += ["", "Use the # number with /done or /delete."]
    return "\n".join(lines)


def _change_events(db, args, action):
    ids = [int(x) for x in re.findall(r"\d+", args)]
    if not ids:
        return None, None
    changed, missing_ids = [], []
    for event_id in ids:
        event = find_event(db, event_id)
        if event is None:
            missing_ids.append(f"#{event_id}")
            continue
        action(event)
        changed.append(esc(event["name"]))
    return changed, missing_ids


def cmd_done(db, args, today):
    changed, missing_ids = _change_events(db, args, lambda e: e.update(completed=True))
    if changed is None:
        return "⚠️ Which one? For example <code>/done 3</code>\nSee the numbers with /list."
    text = ""
    if changed:
        text += "🎉 <b>Great work!</b> Marked as done:\n" + "\n".join(f"• {n}" for n in changed)
        text += "\n\nIt won't appear in the countdown anymore."
    if missing_ids:
        text += f"\n\n🤷 Not found: {', '.join(missing_ids)}"
    return text.strip()


def cmd_delete(db, args, today):
    changed, missing_ids = _change_events(db, args, lambda e: db["events"].remove(e))
    if changed is None:
        return "⚠️ Which one? For example <code>/delete 3</code>\nSee the numbers with /list."
    text = ""
    if changed:
        text += "🗑 Deleted:\n" + "\n".join(f"• {n}" for n in changed)
    if missing_ids:
        text += f"\n\n🤷 Not found: {', '.join(missing_ids)}"
    return text.strip()


def cmd_post(db, args, today):
    return "📣 Posting the countdown to the channel now."


COMMANDS = {
    "/start": cmd_help,
    "/help": cmd_help,
    "/add": cmd_add,
    "/list": cmd_list,
    "/done": cmd_done,
    "/delete": cmd_delete,
    "/post": cmd_post,
}


def process_commands(db, today):
    """Handle new private messages. Returns True if the admin asked for /post."""
    try:
        updates = tg("getUpdates", offset=db["last_update_id"] + 1, timeout=0)["result"]
    except Exception as error:
        print(f"⚠️ Could not read messages: {error}")
        return False

    post_requested = False
    for update in updates:
        db["last_update_id"] = update["update_id"]
        message = update.get("message")
        if not message or not message.get("text") or message["chat"]["type"] != "private":
            continue  # ignore channel posts, groups, stickers, photos...

        chat_id = message["chat"]["id"]
        if message.get("from", {}).get("id") != ADMIN_ID:
            reply(chat_id, "⛔ Sorry, this is a private bot.")
            continue

        text = message["text"].strip()
        command, _, args = text.partition(" ")
        command = command.split("@")[0].lower()
        handler = COMMANDS.get(command)

        if handler is None:
            reply(chat_id, "🤷 I don't know that one. Send /help to see what I can do.")
            continue
        if command == "/post":
            post_requested = True
        reply(chat_id, handler(db, args.strip(), today))

    print(f"Processed {len(updates)} message(s).")
    return post_requested


# ─── The daily channel post ───────────────────────────────────────────────
def progress_bar(event, today, width=10):
    start = date.fromisoformat(event.get("added", event["date"]))
    total = (date.fromisoformat(event["date"]) - start).days
    ratio = 1.0 if total <= 0 else min(max((today - start).days / total, 0.0), 1.0)
    filled = round(ratio * width)
    return f"<code>{'▰' * filled}{'▱' * (width - filled)}</code> {round(ratio * 100)}% of prep time used"


def event_block(event, today):
    days = days_left(event, today)
    when = date.fromisoformat(event["date"])
    if days == 0:
        return [event_title(event), "🚨 <b>TODAY!</b> Give it everything you've got 🔥"]
    if days == 1:
        return [event_title(event), "⏰ <b>TOMORROW</b> · final review time"]
    dot = "🔴" if days <= 3 else "🟠" if days <= 7 else "🟡" if days <= 14 else "🟢"
    return [
        event_title(event),
        f"{dot} <b>{days} days left</b> · {pretty_date(when, short=True)}",
        progress_bar(event, today),
    ]


def build_countdown(db, today):
    upcoming = sorted(
        (e for e in db["events"] if not e["completed"] and days_left(e, today) >= 0),
        key=lambda e: (e["date"], not e.get("important")),
    )
    line = "━━━━━━━━━━━━━━━━━━"
    lines = ["🎓 <b>ACADEMIC COUNTDOWN</b>", f"🗓 {pretty_date(today)}", line]

    if not upcoming:
        lines += ["", "🌴 <b>No upcoming deadlines!</b>",
                  "Enjoy the free time, or get ahead while it's quiet 😎"]
    else:
        for event in upcoming[:MAX_EVENTS_IN_POST]:
            lines += [""] + event_block(event, today)
        extra = len(upcoming) - MAX_EVENTS_IN_POST
        if extra > 0:
            lines += ["", f"➕ …and {extra} more"]
        this_week = sum(1 for e in upcoming if days_left(e, today) <= 7)
        total = f"{len(upcoming)} deadline{'s' if len(upcoming) != 1 else ''}"
        lines += ["", line, f"📊 {total} ahead · {this_week} within 7 days"]

    lines += ["", f"💬 <i>{QUOTES[today.toordinal() % len(QUOTES)]}</i>"]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    now = datetime.now(LOCAL_TZ)
    today = now.date()
    db = load_db()

    post_requested = process_commands(db, today)

    # Auto-cleanup: forget events whose date has passed
    before = len(db["events"])
    db["events"] = [e for e in db["events"] if days_left(e, today) >= 0]
    if len(db["events"]) < before:
        print(f"Removed {before - len(db['events'])} past event(s).")

    save_db(db)  # save first, so new events are kept even if posting fails

    daily_due = now.hour >= POST_HOUR and db["last_post_date"] != today.isoformat()
    if FORCE_POST or post_requested or daily_due:
        send(CHANNEL_ID, build_countdown(db, today))
        db["last_post_date"] = today.isoformat()
        save_db(db)
        print("📣 Countdown posted to the channel.")
    else:
        print("No post needed this run.")


if __name__ == "__main__":
    main()
