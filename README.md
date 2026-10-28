# whatsapp-export-insights

Turn an exported WhatsApp chat text file into statistics, fully locally.
No network access, no account, no upload. Your chat never leaves your machine.

## What it does

Point it at the text file WhatsApp gives you from Export chat (without
media) and it prints:

- total messages, first and last message dates
- top talkers, busiest hours and weekdays, messages per day
- media messages and links shared
- median reply time overall and per sender (replies within 12 hours)
- top words, with common stopwords removed

It handles day-first dates (`12/03/2026, 09:15`), ISO dates
(`2026-03-12, 09:15`), seconds, multi-line messages, and system lines
(encryption notices and similar lines are counted, not treated as messages).

## Usage

```sh
python3 whatsapp_export_insights.py examples/chat.txt
python3 whatsapp_export_insights.py chat.txt --json
python3 whatsapp_export_insights.py chat.txt --top 5
python3 whatsapp_export_insights.py chat.txt --check
```

## Real example

Running it on `examples/chat.txt` (a small made-up chat) gives:

```
WhatsApp chat insights
=====================
Messages: 8
Period: 2026-03-12T09:15:00 to 2026-03-13T09:03:00
System lines: 0

Top talkers:
  Ayesha: 4
  Bilal: 4

Busiest hours:
  08:00: 1
  09:00: 5
  10:00: 1
  18:00: 1

Messages per day:
  2026-03-12: 5
  2026-03-13: 3

Media messages: 1
Links shared: 1
Median reply time: 5.5 minutes

Top words:
  report: 3
  morning: 2
  team: 1
  weekly: 1
  ready: 1
  great: 1
  review: 1
  before: 1
  lunch: 1
  shared: 1
```

With `--json` the same statistics come out as JSON, with senders, busiest
weekdays, messages per day, and median reply times per sender included.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

12 tests pass, covering parsing (day-first, ISO, continuation lines,
system lines, invalid dates), statistics (counts, top word, reply median),
and the CLI (human output, JSON output, `--check`, missing file).

## Why it can spread

WhatsApp exports are a common dead end: you get a big text file and no
built-in summary. Chat analyzer sites ask you to upload a private
conversation; this one runs offline in one file with zero dependencies,
which is exactly the pitch people search for before trusting a tool with
their chats.
