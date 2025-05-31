import unittest
import tempfile
import os
import json
from datetime import datetime
from step_history import StepHistory, Step, OperationType

class TestStepHistory(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "steps.json")
        self.history = StepHistory(self.storage_path)

    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)

    def test_add_step(self):
        # Test adding a step
        self.history.add_step(OperationType.FETCH, "Test fetch")
        self.assertEqual(len(self.history.steps), 1)
        self.assertEqual(self.history.steps[0].operation, OperationType.FETCH)
        self.assertEqual(self.history.steps[0].details, "Test fetch")

    def test_invalid_operation(self):
        # Test adding step with invalid operation
        with self.assertRaises(ValueError):
            self.history.add_step("invalid", "Test")

    def test_clear_steps(self):
        # Test clearing steps
        self.history.add_step(OperationType.FETCH, "Test fetch")
        self.history.clear_steps()
        self.assertEqual(len(self.history.steps), 0)

    def test_persistence(self):
        # Test that steps are persisted to storage
        self.history.add_step(OperationType.FETCH, "Test fetch")
        
        # Create new history instance with same storage path
        new_history = StepHistory(self.storage_path)
        self.assertEqual(len(new_history.steps), 1)
        self.assertEqual(new_history.steps[0].operation, OperationType.FETCH)

    def test_get_steps_filtering(self):
        # Test filtering steps
        self.history.add_step(OperationType.FETCH, "Fetch 1")
        self.history.add_step(OperationType.PARSE, "Parse 1")
        self.history.add_step(OperationType.FETCH, "Fetch 2")

        # Test filtering by operation
        fetch_steps = self.history.get_steps(operation_type=OperationType.FETCH)
        self.assertEqual(len(fetch_steps), 2)

        # Test filtering by time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history.add_step(OperationType.FETCH, "Fetch 3")
        recent_steps = self.history.get_steps(start_time=now)
        self.assertEqual(len(recent_steps), 1)

    def test_metadata(self):
        # Test adding step with metadata
        metadata = {"table_id": 1, "rows": 100}
        self.history.add_step(OperationType.PARSE, "Parse table", metadata=metadata)
        
        step = self.history.get_last_step()
        self.assertEqual(step.metadata, metadata)

    def test_step_count(self):
        # Test step counting
        self.history.add_step(OperationType.FETCH, "Fetch 1")
        self.history.add_step(OperationType.PARSE, "Parse 1")
        self.history.add_step(OperationType.FETCH, "Fetch 2")

        self.assertEqual(self.history.get_step_count(), 3)
        self.assertEqual(self.history.get_operation_count(OperationType.FETCH), 2)
        self.assertEqual(self.history.get_operation_count(OperationType.PARSE), 1)

if __name__ == '__main__':
    unittest.main() 