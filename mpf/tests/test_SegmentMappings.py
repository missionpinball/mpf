import unittest

from mpf.core.segment_mappings import TextToSegmentMapper, bcd_segments


class TestSegmentDisplay(unittest.TestCase):

    def test_text_to_mapping(self):
        mapping = TextToSegmentMapper.map_text_to_segments("1337.23", 10, bcd_segments, embed_dots=True)
        self.assertEqual(
            [bcd_segments[None], bcd_segments[None], bcd_segments[None], bcd_segments[None],
             bcd_segments[ord("1")], bcd_segments[ord("3")], bcd_segments[ord("3")],
             bcd_segments[ord("7")].copy_with_dp_on(), bcd_segments[ord("2")], bcd_segments[ord("3")],],
            mapping
        )

        mapping = TextToSegmentMapper.map_text_to_segments("1337.23", 4, bcd_segments, embed_dots=True)
        self.assertEqual(
            [bcd_segments[ord("3")], bcd_segments[ord("7")].copy_with_dp_on(),
             bcd_segments[ord("2")], bcd_segments[ord("3")],],
            mapping
        )
