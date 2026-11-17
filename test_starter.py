import asyncio
import unittest
from decimal import Decimal as D

from starter import recommend_price, sample_fetch_offers


def offers(*items, status="success"):
    async def fetch():
        return {
            "status": status,
            "offers": [
                {"seller": s, "price": D(p), "delivery_days": d} for s, p, d in items
            ],
        }
    return fetch


class RecommendPriceTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_calculation(self):
        r = await recommend_price(sample_fetch_offers, D("4900.00"), D("4500.00"))
        self.assertEqual(r["price"], D("4728.00"))
        self.assertEqual(r["decision"], "APPLY")

    async def test_rounds_down_to_kopeck(self):
        r = await recommend_price(offers(("A", "100.10", 1)), D("100.00"), D("1.00"))
        self.assertEqual(r["price"], D("98.59"))  # 98.5985 -> 98.59

    async def test_filters_own_shop_slow_and_unknown_delivery(self):
        f = offers(("MyShop", "10.00", 1), ("S", "20.00", 7),
                   ("N", "30.00", None), ("OK", "400.00", 6))
        r = await recommend_price(f, D("400.00"), D("1.00"))
        self.assertEqual(r["price"], D("394.00"))

    async def test_min_price_floor(self):
        r = await recommend_price(offers(("A", "100.00", 1)), D("120.00"), D("110.00"))
        self.assertEqual((r["price"], r["decision"]), (D("110.00"), "APPLY"))

    async def test_no_suitable_offers_hold_even_below_min(self):
        r = await recommend_price(offers(("myshop", "5.00", 1)), D("50.00"), D("100.00"))
        self.assertEqual((r["price"], r["decision"]), (D("50.00"), "HOLD"))

    async def test_exactly_30_percent_is_apply_over_is_review(self):
        f = offers(("A", "100.00", 1))
        r = await recommend_price(f, D("1000.00"), D("700.00"))
        self.assertEqual((r["price"], r["decision"]), (D("700.00"), "APPLY"))
        r = await recommend_price(f, D("1000.00"), D("699.99"))
        self.assertEqual((r["price"], r["decision"]), (D("699.99"), "REVIEW"))
        r = await recommend_price(f, D("1000.00"), D("1300.00"))
        self.assertEqual(r["decision"], "APPLY")
        r = await recommend_price(f, D("1000.00"), D("1300.01"))
        self.assertEqual(r["decision"], "REVIEW")

    async def test_timeout_returns_hold(self):
        async def slow():
            await asyncio.sleep(10)
        r = await recommend_price(slow, D("100.00"), D("50.00"), timeout_s=0.05)
        self.assertEqual((r["price"], r["decision"]), (D("100.00"), "HOLD"))

    async def test_source_exception_and_bad_status_return_hold(self):
        async def boom():
            raise RuntimeError("down")
        r = await recommend_price(boom, D("100.00"), D("50.00"))
        self.assertEqual(r["decision"], "HOLD")
        r = await recommend_price(offers(("A", "10.00", 1), status="partial"),
                                  D("100.00"), D("50.00"))
        self.assertEqual((r["price"], r["decision"]), (D("100.00"), "HOLD"))


if __name__ == "__main__":
    unittest.main()
