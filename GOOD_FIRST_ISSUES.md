# Good first issues

Small, testable tasks for first-time contributors. No network access needed.

1. Add a `--sender` filter that limits statistics to one participant.
   Scope: add the flag, filter messages before analysis, add a CLI test.

2. Add a `--from` and `--to` date filter for the statistics window.
   Scope: parse the dates, filter messages, add tests for both flags.

3. Count emoji usage and report the top 5 emoji in the human output.
   Scope: count emoji characters in message text, add a unit test.

4. Support month-first dates (`03/12/2026`) behind a `--date-format` flag.
   Scope: add the flag and a parser variant, add tests, document it.
