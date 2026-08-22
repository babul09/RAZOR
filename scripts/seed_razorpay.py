"""Seed the Razorpay test account with realistic Orders and Payment Links.

Razorpay's API can't fabricate a *failed payment* server-side — payments are
produced by the checkout flow. What it *can* create via API are Orders and
Payment Links, which are the real recovery artifacts the demo drives off.

Run (uses RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET from .env):

    python scripts/seed_razorpay.py            # 10 orders + 10 payment links
    python scripts/seed_razorpay.py --n 5
    python scripts/seed_razorpay.py --links-only
    python scripts/seed_razorpay.py --orders-only
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations import razorpay


def _amounts(n: int) -> list[int]:
    """A few realistic INR test amounts (in paise)."""
    base = [99900, 120000, 249900, 50000, 499900, 150000, 79900, 345000, 60000, 210000]
    out = []
    for i in range(n):
        out.append(base[i % len(base)] + i * 137)
    return out


def seed_orders(n: int) -> list[dict]:
    created = []
    for i, amount in enumerate(_amounts(n)):
        order = razorpay.create_order(
            amount,
            receipt=f"razor_seed_{int(time.time())}_{i}",
            notes={"source": "razor-seed", "idx": i, "strategy": "PAYMENT_LINK"},
        )
        created.append(order)
    return created


def seed_links(n: int) -> list[dict]:
    created = []
    for i, amount in enumerate(_amounts(n)):
        link = razorpay.create_payment_link(
            amount,
            description=f"RAZOR recovery #{i + 1} — failed payment",
            email=f"customer{i}@example.com",
            contact=f"+919900000{i % 100:02d}",
            notes={"source": "razor-seed", "idx": i},
        )
        created.append(link)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="count per type (default 10)")
    parser.add_argument("--orders-only", action="store_true")
    parser.add_argument("--links-only", action="store_true")
    args = parser.parse_args()

    if not razorpay.is_configured():
        print("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set — nothing to seed.")
        return

    do_orders = not args.links_only
    do_links = not args.orders_only

    if do_orders:
        print(f"Creating {args.n} orders…")
        orders = seed_orders(args.n)
        for o in orders:
            print(f"  order {o.get('id')}  ₹{int(o.get('amount', 0)) / 100:,.0f}  {o.get('status')}")

    if do_links:
        print(f"Creating {args.n} payment links…")
        links = seed_links(args.n)
        for l in links:
            print(f"  link  {l.get('id')}  ₹{int(l.get('amount', 0)) / 100:,.0f}  {l.get('short_url')}")

    print("\nDone. Refresh the Razorpay tab — Orders/Links are now live on the test API.")


if __name__ == "__main__":
    main()
