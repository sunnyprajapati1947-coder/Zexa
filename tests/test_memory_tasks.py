import tempfile
import unittest
from pathlib import Path

from zexa.memory import MemoryStore
from zexa.tasks import TaskStore


class MemoryTaskTests(unittest.TestCase):
    def test_memory_upsert_recall_and_forget(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "test.db")
            store.remember("language", "Hindi")
            store.remember("language", "Hinglish")
            self.assertEqual(store.recall("language")["value"], "Hinglish")
            self.assertTrue(store.forget("language"))
            self.assertIsNone(store.recall("language"))

    def test_task_status_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = TaskStore(Path(folder) / "test.db")
            task_id = store.create("Build Zexa memory")
            self.assertTrue(store.update_status(task_id, "completed"))
            self.assertEqual(store.list_tasks()[0]["status"], "completed")
            with self.assertRaises(ValueError):
                store.update_status(task_id, "unknown")

    def test_memory_rejects_empty_values(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "test.db")
            with self.assertRaises(ValueError):
                store.remember(" ", "value")


if __name__ == "__main__":
    unittest.main()
