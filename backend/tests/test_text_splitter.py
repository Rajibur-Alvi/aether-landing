import unittest

from utils.text_splitter import split_text


class TextSplitterTest(unittest.TestCase):
    def test_long_unpunctuated_text_is_capped_to_chunk_size(self):
        text = "Near limit phrase VIOLET HARBOR. " + ("data pattern " * 3900)

        chunks = split_text(text, chunk_size=1200, chunk_overlap=200)

        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(max(len(chunk) for chunk in chunks), 1200)
        self.assertIn("VIOLET HARBOR", chunks[0])


if __name__ == "__main__":
    unittest.main()
