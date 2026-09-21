import unittest

from services.ttr_statistics import calculate_ttr_statistics


class TTRStatisticsTest(unittest.TestCase):
    def test_counts_tokens_case_insensitively(self):
        result = calculate_ttr_statistics("Мир, мир! Война и мир.")
        self.assertEqual(result.text_length, 5)
        self.assertEqual(result.unique_token_count, 3)
        self.assertAlmostEqual(result.ratio, 0.6)

    def test_empty_text_has_zero_ratio(self):
        result = calculate_ttr_statistics("   ")
        self.assertEqual(result.text_length, 0)
        self.assertEqual(result.unique_token_count, 0)
        self.assertEqual(result.ratio, 0)


if __name__ == "__main__":
    unittest.main()
