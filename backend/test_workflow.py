import asyncio
import unittest

from backend.main import analyze, app
from backend.worker import _parse_render_indices


class WorkflowSelfCheck(unittest.TestCase):
    def test_render_indices_are_validated(self):
        self.assertEqual(_parse_render_indices("1,3", 4), [1, 3])
        for value in ("", "1,1", "0", "5", "nope"):
            with self.assertRaises(ValueError):
                _parse_render_indices(value, 4)

    def test_workflow_routes_exist(self):
        routes = {
            (route.path, tuple(sorted(route.methods or [])))
            for route in app.routes
            if hasattr(route, "methods")
        }
        self.assertIn(("/api/analyze", ("GET",)), routes)
        self.assertIn(("/api/render-selected", ("POST",)), routes)

    def test_analyze_rejects_empty_source(self):
        response = asyncio.run(analyze(source=""))
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
