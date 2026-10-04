import unittest

from services.author_texts_statistics import calculate_author_texts_statistics


class AuthorTextsStatisticsTest(unittest.TestCase):
    def test_counts_tokens_case_insensitively(self):
        result = calculate_author_texts_statistics("Мир, мир! Война и мир.")
        self.assertEqual(result.text_length, 5)
        self.assertEqual(result.unique_token_count, 3)
        self.assertAlmostEqual(result.ratio, 0.6)

    def test_empty_text_has_zero_ratio(self):
        result = calculate_author_texts_statistics("   ")
        self.assertEqual(result.text_length, 0)
        self.assertEqual(result.unique_token_count, 0)
        self.assertEqual(result.ratio, 0)


if __name__ == "__main__":
    unittest.main()
