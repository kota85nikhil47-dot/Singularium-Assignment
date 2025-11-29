from django.test import TestCase
from .scoring import compute_scores, detect_cycles
from datetime import date, timedelta
from django.urls import reverse
from rest_framework.test import APIClient
import json

class ScoringAlgorithmTests(TestCase):
    def test_basic_scoring_order(self):
        today = date.today()
        tasks = [
            {"id":"t1", "title":"A", "due_date": (today + timedelta(days=2)).strftime("%Y-%m-%d"), "estimated_hours":5, "importance":5, "dependencies":[]},
            {"id":"t2", "title":"B", "due_date": (today + timedelta(days=1)).strftime("%Y-%m-%d"), "estimated_hours":8, "importance":6, "dependencies":[]},
            {"id":"t3", "title":"C", "due_date": None, "estimated_hours":1, "importance":3, "dependencies":[]},
        ]
        scored, meta = compute_scores(tasks, today=today)
        # Expect t2 (closest due) or t3 (quick win) to rank high depending on weights.
        self.assertEqual(len(scored), 3)
        # scores between 0 and 1
        for s in scored:
            self.assertTrue(0.0 <= s['score'] <= 1.0)

    def test_cycle_detection(self):
        tasks = [
            {"id":"a","title":"A","dependencies":["b"]},
            {"id":"b","title":"B","dependencies":["c"]},
            {"id":"c","title":"C","dependencies":["a"]},
        ]
        cycles = detect_cycles(tasks)
        self.assertTrue(len(cycles) >= 1)
        # expect cycle includes a,b,c
        found = False
        for cyc in cycles:
            if set(['a','b','c']).issubset(set(cyc)):
                found = True
        self.assertTrue(found)

    def test_api_analyze_endpoint(self):
        client = APIClient()
        url = '/api/tasks/analyze/'
        payload = {
            "tasks": [
                {"id":1,"title":"Fix bug","due_date": None,"estimated_hours":2,"importance":8,"dependencies":[]},
                {"id":2,"title":"Write docs","due_date": None,"estimated_hours":4,"importance":6,"dependencies":[1]},
            ]
        }
        resp = client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('tasks', data)
        self.assertIn('meta', data)
