import unittest
from unittest.mock import patch, MagicMock
from celery.exceptions import NotRegistered
from src.tasks.task_manager import TaskManager


class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.manager = TaskManager()

    @patch("src.tasks.task_manager.AsyncResult")
    def test_get_task_status_not_registered(self, mock_async_result):
        # Simulate AsyncResult returning NotRegistered for result
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.failed.return_value = False
        mock_result.status = "FAILURE"
        mock_result.result = NotRegistered()
        mock_result.traceback = None
        mock_result.info = None
        mock_async_result.return_value = mock_result

        # Patch is_celery_available to True
        self.manager.is_celery_available = MagicMock(return_value=True)

        status = self.manager.get_task_status("fake_id")
        self.assertIn("task_id", status)
        self.assertEqual(status["task_id"], "fake_id")
        self.assertEqual(status["status"], "FAILURE")
        # Should not raise serialization error, should be string or handled
        self.assertTrue(isinstance(status["result"], str) or status["result"] is None)


if __name__ == "__main__":
    unittest.main()
