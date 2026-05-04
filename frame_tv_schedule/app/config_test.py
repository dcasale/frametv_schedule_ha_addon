from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .config import AddonConfig, load_config


class ConfigTest(unittest.TestCase):
    def test_simple_fields_populate_internal_calendar_and_windows(self) -> None:
        config = AddonConfig(
            calendar_entity="calendar.granny",
            additional_calendar_entity_1="calendar.family",
            morning_window_start="06:15",
            morning_window_end="08:15",
            afternoon_window_start="14:45",
            afternoon_window_end="16:45",
        )

        self.assertEqual(config.calendar_entities, ["calendar.granny", "calendar.family"])
        self.assertEqual(config.display_windows[0].start, "06:15")
        self.assertEqual(config.display_windows[0].end, "08:15")
        self.assertEqual(config.display_windows[1].start, "14:45")
        self.assertEqual(config.display_windows[1].end, "16:45")

    def test_calendar_friendly_names_are_normalized_to_entity_ids(self) -> None:
        config = AddonConfig(
            calendar_entity="Granny",
            additional_calendar_entity_1="Family Calendar",
        )

        self.assertEqual(config.calendar_entities, ["calendar.granny", "calendar.family_calendar"])

    def test_existing_list_options_still_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "options.json"
            path.write_text(
                """
                {
                  "calendar_entities": ["calendar.granny"],
                  "display_windows": [{"start": "07:00", "end": "08:00"}]
                }
                """
            )

            config = load_config(path)

        self.assertEqual(config.calendar_entities, ["calendar.granny"])
        self.assertEqual(len(config.display_windows), 1)
        self.assertEqual(config.display_windows[0].start, "07:00")


if __name__ == "__main__":
    unittest.main()
