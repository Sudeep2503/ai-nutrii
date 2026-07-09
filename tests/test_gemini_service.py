import unittest

from ai.gemini_service import GeminiService


class GeminiServiceFallbackTests(unittest.TestCase):
    def test_fallback_recommendation_uses_prediction_context(self):
        service = GeminiService(api_key=None)
        context = {
            "predicted_deficiency": "Iron Deficiency",
            "symptoms": ["Fatigue", "Pale skin"],
            "confidence_score": 87,
        }

        result = service.get_recommendation(context)

        self.assertTrue(result["available"])
        self.assertIn("iron", " ".join(result["foods_to_eat"]).lower())
        self.assertTrue(result["lifestyle_recommendations"])


if __name__ == "__main__":
    unittest.main()
