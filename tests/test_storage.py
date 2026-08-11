import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import storage


class StorageTests(unittest.TestCase):
    def test_atomic_json_round_trip_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "state.json"
            value = {"schema_version": 1, "status": "active"}

            storage.write_json_atomic(target, value)

            self.assertEqual(storage.read_json(target), value)
            self.assertFalse(list(target.parent.glob("*.tmp")))
