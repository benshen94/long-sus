from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from long_sus.api import create_app


class HttpApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_population_pyramid_returns_csv_by_default(self) -> None:
        response = self.client.get(
            "/population-pyramid",
            params={
                "country": "World",
                "scheme_id": "threshold_age_60_all_eligible",
                "target": "Xc",
                "factor": 1.2,
                "branch": "analytic_arm",
                "year": 2050,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("population_count", response.text.splitlines()[0])

    def test_population_pyramid_can_return_json_rows(self) -> None:
        response = self.client.get(
            "/population-pyramid",
            params={
                "country": "World",
                "scheme_id": "threshold_age_60_all_eligible",
                "target": "Xc",
                "factor": 1.2,
                "branch": "analytic_arm",
                "year": 2050,
                "format": "json",
            },
        )

        self.assertEqual(response.status_code, 200)

        rows = response.json()
        self.assertTrue(rows)

        first_row = rows[0]
        self.assertEqual(first_row["country"], "World")
        self.assertEqual(first_row["year"], 2050)
        self.assertIn(first_row["sex"], {"male", "female"})
        self.assertIn("age", first_row)
        self.assertIn("population_count", first_row)
        self.assertIn("treated_population_count", first_row)
        self.assertIn("untreated_population_count", first_row)

    def test_population_pyramid_can_return_csv(self) -> None:
        response = self.client.get(
            "/population-pyramid",
            params={
                "country": "World",
                "scheme_id": "threshold_age_60_all_eligible",
                "target": "Xc",
                "factor": 1.2,
                "branch": "analytic_arm",
                "year": 2050,
                "format": "csv",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("population_count", response.text.splitlines()[0])

    def test_invalid_query_returns_400_with_message(self) -> None:
        response = self.client.get(
            "/population-size",
            params={
                "country": "World",
                "scheme_id": "threshold_age_60_all_eligible",
                "target": "none",
                "factor": 1.0,
                "branch": "analytic_arm",
                "year": 2050,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("target='none'", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
