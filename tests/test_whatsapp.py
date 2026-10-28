import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatsapp_export_insights import analyse, parse  # noqa: E402

SAMPLE = """12/03/2026, 09:15 - Ayesha: Morning team, the weekly report is ready
12/03/2026, 09:16 - Bilal: Great, I will review it before lunch
12/03/2026, 09:20 - Ayesha: Thanks, I shared the summary at example.com/report
12/03/2026, 10:05 - Bilal: <Media omitted>
12/03/2026, 18:40 - Ayesha: Done for today
13/03/2026, 08:55 - Bilal: Morning, one question about the report
13/03/2026, 09:02 - Ayesha: Sure, ask away
13/03/2026, 09:03 - Bilal: All clear now
"""


class TestParse(unittest.TestCase):
    def test_message_count_and_senders(self):
        messages, system, skipped = parse(SAMPLE)
        self.assertEqual(len(messages), 8)
        self.assertEqual(system, 0)
        self.assertEqual(messages[0].sender, "Ayesha")
        self.assertEqual(messages[0].when.day, 12)

    def test_continuation_lines_join_previous(self):
        messages, _, _ = parse(
            "12/03/2026, 09:15 - Ayesha: first line\nsecond line\n")
        self.assertEqual(messages[0].text, "first line\nsecond line")

    def test_system_line_not_a_message(self):
        messages, system, _ = parse(
            "12/03/2026, 09:15 - Messages are end-to-end encrypted\n"
            "12/03/2026, 09:16 - Ayesha: Hi\n")
        self.assertEqual(len(messages), 1)
        self.assertEqual(system, 1)

    def test_iso_date_accepted(self):
        messages, _, _ = parse("2026-03-12, 09:15 - Ayesha: Hi\n")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].when.month, 3)

    def test_invalid_date_skipped(self):
        messages, _, skipped = parse("32/13/2026, 09:15 - Ayesha: Hi\n")
        self.assertEqual(len(messages), 0)
        self.assertEqual(skipped, 1)


class TestAnalyse(unittest.TestCase):
    def test_counts(self):
        messages, _, _ = parse(SAMPLE)
        stats = analyse(messages)
        self.assertEqual(stats["total_messages"], 8)
        self.assertEqual(stats["senders"], {"Ayesha": 4, "Bilal": 4})
        self.assertEqual(stats["media_messages"], 1)
        self.assertEqual(stats["messages_per_day"],
                         {"2026-03-12": 5, "2026-03-13": 3})

    def test_top_word_is_report(self):
        messages, _, _ = parse(SAMPLE)
        stats = analyse(messages)
        self.assertEqual(stats["top_words"][0], ("report", 3))

    def test_reply_median(self):
        messages, _, _ = parse(SAMPLE)
        stats = analyse(messages)
        # Replies within 12 hours: 1, 4, 45, 455, 7, 1 minutes.
        # The 855 minute overnight gap is excluded by the 12 hour cap.
        self.assertEqual(stats["median_reply_minutes_overall"], 5.5)


class TestCli(unittest.TestCase):
    def run_cli(self, text, *args):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.txt"
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "whatsapp_export_insights.py"),
                 str(path), *args],
                capture_output=True, text=True)
            return result

    def test_human_output(self):
        result = self.run_cli(SAMPLE)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Messages: 8", result.stdout)
        self.assertIn("Ayesha: 4", result.stdout)

    def test_json_output(self):
        result = self.run_cli(SAMPLE, "--json")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["total_messages"], 8)

    def test_check_passes_and_fails(self):
        self.assertEqual(self.run_cli(SAMPLE, "--check").returncode, 0)
        self.assertEqual(self.run_cli("nothing here\n", "--check").returncode, 1)

    def test_missing_file_fails(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "whatsapp_export_insights.py"),
             "/nonexistent/chat.txt"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
