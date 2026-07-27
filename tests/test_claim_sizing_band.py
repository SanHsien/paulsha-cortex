"""#222（design #208 H.2）：五維 sizing 總分 → band 判定純函式。

claim.sizing_band() 是 claim.py／registry.py／completion.py 三處共用的門檻判定，
避免各自硬編碼 Green/Yellow/Red 門檻造成漂移。band 字串必須沿用
deck.schema.BAND_LEVELS，不得另立常數或大小寫變體。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator import claim
from paulsha_cortex.deck.schema import BAND_LEVELS


class SizingBandThresholdTests(unittest.TestCase):
    def test_green_band_covers_zero_to_three(self) -> None:
        for total in (0, 1, 2, 3):
            self.assertEqual(claim.sizing_band(total), "green")

    def test_yellow_band_covers_four_to_six(self) -> None:
        for total in (4, 5, 6):
            self.assertEqual(claim.sizing_band(total), "yellow")

    def test_red_band_covers_seven_to_ten(self) -> None:
        for total in (7, 8, 9, 10):
            self.assertEqual(claim.sizing_band(total), "red")

    def test_returned_band_is_a_deck_schema_band_level(self) -> None:
        for total in range(0, 11):
            self.assertIn(claim.sizing_band(total), BAND_LEVELS)

    def test_out_of_range_total_rejected(self) -> None:
        with self.assertRaises(ValueError):
            claim.sizing_band(-1)
        with self.assertRaises(ValueError):
            claim.sizing_band(11)

    def test_non_integer_total_rejected(self) -> None:
        with self.assertRaises(ValueError):
            claim.sizing_band(3.0)
        with self.assertRaises(ValueError):
            claim.sizing_band("3")
        with self.assertRaises(ValueError):
            claim.sizing_band(True)


if __name__ == "__main__":
    unittest.main()
