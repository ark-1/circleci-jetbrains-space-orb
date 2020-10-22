import unittest
from typing import Callable, Any

import scripts.notify as notify


branch_filters = ["master", "pr-[0-9]+"]


class MyTestCase(unittest.TestCase):
    def test_skip_message_on_no_event(self):
        with open('/tmp/JB_SPACE_JOB_STATUS', 'w') as f:
            f.write('success')
        print("Running notify")
        out = MyTestCase._capture_stdout(
            lambda: notify.notify(None, None, ['aaa'], [], b'', b'', 'localhost', 'fail', 'master', ['.+'])
        )
        print("Output:")
        print(out)
        self.assertIn("NO JB SPACE ALERT", out)

    def test_branch_filter_match_all_default(self):
        match = notify.branch_filter('xyz-123', ['.+'])
        self.assertTrue(match)

    def test_branch_filter_string(self):
        match = notify.branch_filter('master', branch_filters)
        self.assertTrue(match)

    def test_branch_filter_regex_numbers(self):
        match = notify.branch_filter('pr-123', branch_filters)
        self.assertTrue(match)

    def test_branch_filter_regex_non_match(self):
        match = notify.branch_filter('x', branch_filters)
        self.assertFalse(match)

    def test_branch_filter_regex_no_partial_match(self):
        match = notify.branch_filter('pr-', branch_filters)
        self.assertFalse(match)

    @staticmethod
    def _capture_stdout(action: Callable[[], Any]) -> str:
        from io import StringIO
        import sys
        backup = sys.stdout
        sys.stdout = StringIO()
        action()
        out = sys.stdout.getvalue()
        sys.stdout = backup
        return out


if __name__ == '__main__':
    unittest.main()
