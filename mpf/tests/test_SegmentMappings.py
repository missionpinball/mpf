import unittest

from mpf.core.segment_mappings import TextToSegmentMapper, BCD_SEGMENTS


class TestSegmentDisplay(unittest.TestCase):

    def test_text_to_mapping(self):
        mapping = TextToSegmentMapper.map_text_to_segments("1337.23", 10, BCD_SEGMENTS, embed_dots=True)
        self.assertEqual(
            [BCD_SEGMENTS[None], BCD_SEGMENTS[None], BCD_SEGMENTS[None], BCD_SEGMENTS[None],
             BCD_SEGMENTS[ord("1")], BCD_SEGMENTS[ord("3")], BCD_SEGMENTS[ord("3")],
             BCD_SEGMENTS[ord("7")].copy_with_dp_on(), BCD_SEGMENTS[ord("2")], BCD_SEGMENTS[ord("3")], ],
            mapping
        )

        mapping = TextToSegmentMapper.map_text_to_segments("1337.23", 4, BCD_SEGMENTS, embed_dots=True)
        self.assertEqual(
            [BCD_SEGMENTS[ord("3")], BCD_SEGMENTS[ord("7")].copy_with_dp_on(),
             BCD_SEGMENTS[ord("2")], BCD_SEGMENTS[ord("3")], ],
            mapping
        )
