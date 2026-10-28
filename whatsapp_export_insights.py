#!/usr/bin/env python3
"""Turn an exported WhatsApp chat text file into local statistics.

Reads the plain text export you get from WhatsApp (Export chat, without
media) and prints who talked most, busiest hours and weekdays, daily
counts, top words, media and link counts, and median reply times.

Everything runs locally. No network access, no account, no upload.

Supported line formats (day first, the usual WhatsApp export):

    12/03/2026, 09:15 - Ayesha: Morning team
    12/03/2026, 09:15:30 - Ayesha: Morning team

ISO dates are also accepted:

    2026-03-12, 09:15 - Ayesha: Morning team

Lines that do not start with a date are treated as continuations of the
previous message. Lines with no sender (system lines such as encryption
notices) are counted as system lines, not as messages.
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

VERSION = "1.0.0"

DATE_PATTERNS = [
    # Day first: 12/03/2026, 09:15
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4}), (\d{1,2}):(\d{2})(?::(\d{2}))? - "),
     lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)),
                int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))),
    # ISO: 2026-03-12, 09:15
    (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2}), (\d{1,2}):(\d{2})(?::(\d{2}))? - "),
     lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))),
]

MEDIA_MARKERS = ("<Media omitted>", "<media omitted>")
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "is", "are",
    "was", "were", "be", "been", "i", "you", "he", "she", "we", "they",
    "it", "this", "that", "to", "of", "in", "on", "for", "with", "at",
    "by", "from", "as", "am", "do", "does", "did", "will", "would",
    "thanks", "thank", "hi", "hello", "hey", "ok", "okay", "yes", "no",
    "please", "just", "now", "today", "tomorrow", "me", "my", "our",
}
WORD_RE = re.compile(r"[a-z][a-z\-']+")
LINK_RE = re.compile(r"https?://\S+|www\.\S+")


class Message:
    def __init__(self, when, sender, text):
        self.when = when
        self.sender = sender
        self.text = text


def parse(text):
    """Parse export text into (messages, system_lines, skipped_lines)."""
    messages = []
    system_lines = 0
    skipped = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        matched = False
        for pattern, build in DATE_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            matched = True
            try:
                when = datetime(*build(match))
            except ValueError:
                skipped += 1
                break
            rest = line[match.end():]
            if ": " in rest:
                sender, body = rest.split(": ", 1)
                messages.append(Message(when, sender.strip(), body))
            else:
                system_lines += 1
            break
        if not matched:
            if messages:
                messages[-1].text += "\n" + line
            else:
                skipped += 1
    return messages, system_lines, skipped


def median_minutes(values):
    if not values:
        return None
    return round(statistics.median(values), 1)


def analyse(messages, top_n=10):
    """Compute statistics from a list of Message objects."""
    senders = Counter(m.sender for m in messages)
    hours = Counter(m.when.hour for m in messages)
    weekdays = Counter(m.when.strftime("%A") for m in messages)
    days = Counter(m.when.date().isoformat() for m in messages)
    media = sum(1 for m in messages if m.text.strip() in MEDIA_MARKERS)
    links = sum(len(LINK_RE.findall(m.text)) for m in messages)
    words = Counter()
    for m in messages:
        if m.text.strip() in MEDIA_MARKERS:
            continue
        for word in WORD_RE.findall(m.text.lower()):
            if word not in STOPWORDS and len(word) > 1:
                words[word] += 1
    reply_minutes = defaultdict(list)
    for prev, cur in zip(messages, messages[1:]):
        if cur.sender != prev.sender:
            delta = (cur.when - prev.when).total_seconds() / 60.0
            if 0 <= delta <= 12 * 60:
                reply_minutes[cur.sender].append(delta)
    reply_medians = {s: median_minutes(v) for s, v in reply_minutes.items()}
    all_replies = [d for v in reply_minutes.values() for d in v]
    return {
        "total_messages": len(messages),
        "senders": dict(senders.most_common()),
        "top_talkers": senders.most_common(top_n),
        "busiest_hours": dict(sorted(hours.items())),
        "busiest_weekdays": dict(weekdays.most_common()),
        "messages_per_day": dict(sorted(days.items())),
        "first_message": messages[0].when.isoformat() if messages else None,
        "last_message": messages[-1].when.isoformat() if messages else None,
        "media_messages": media,
        "links_shared": links,
        "top_words": words.most_common(top_n),
        "median_reply_minutes_overall": median_minutes(all_replies),
        "median_reply_minutes_by_sender": reply_medians,
    }


def render(stats, system_lines, skipped):
    lines = []
    lines.append("WhatsApp chat insights")
    lines.append("=====================")
    lines.append(f"Messages: {stats['total_messages']}")
    if stats["first_message"]:
        lines.append(f"Period: {stats['first_message']} to {stats['last_message']}")
    lines.append(f"System lines: {system_lines}")
    if skipped:
        lines.append(f"Skipped lines: {skipped}")
    lines.append("")
    lines.append("Top talkers:")
    for sender, count in stats["top_talkers"]:
        lines.append(f"  {sender}: {count}")
    lines.append("")
    lines.append("Busiest hours:")
    for hour, count in stats["busiest_hours"].items():
        lines.append(f"  {hour:02d}:00: {count}")
    lines.append("")
    lines.append("Messages per day:")
    for day, count in stats["messages_per_day"].items():
        lines.append(f"  {day}: {count}")
    lines.append("")
    lines.append(f"Media messages: {stats['media_messages']}")
    lines.append(f"Links shared: {stats['links_shared']}")
    lines.append(f"Median reply time: {stats['median_reply_minutes_overall']} minutes")
    lines.append("")
    lines.append("Top words:")
    for word, count in stats["top_words"]:
        lines.append(f"  {word}: {count}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Statistics for an exported WhatsApp chat text file.")
    parser.add_argument("file", help="exported chat text file")
    parser.add_argument("--json", action="store_true",
                        help="print statistics as JSON")
    parser.add_argument("--top", type=int, default=10,
                        help="how many top talkers and words to show")
    parser.add_argument("--check", action="store_true",
                        help="validate the file parses, print nothing else")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    messages, system_lines, skipped = parse(text)
    if args.check:
        if not messages:
            print("error: no messages found", file=sys.stderr)
            return 1
        print(f"ok: {len(messages)} messages parsed")
        return 0
    if not messages:
        print("error: no messages found", file=sys.stderr)
        return 1
    stats = analyse(messages, top_n=args.top)
    if args.json:
        out = dict(stats)
        out["top_talkers"] = dict(stats["top_talkers"])
        out["top_words"] = dict(stats["top_words"])
        out["system_lines"] = system_lines
        out["skipped_lines"] = skipped
        print(json.dumps(out, indent=2))
    else:
        print(render(stats, system_lines, skipped), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
