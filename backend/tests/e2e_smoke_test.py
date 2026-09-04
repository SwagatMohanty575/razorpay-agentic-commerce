"""
End-to-end smoke test — exercises phases 1-8 in one run against the live
server. Stops before the actual Razorpay checkout modal (needs a browser),
but proves everything up to that point is wired correctly. Run this after
any change instead of manually clicking through /docs.

Requires the server running first:
    python -m uvicorn backend.main:app --reload

Run from project root:
    python -m backend.tests.e2e_smoke_test
"""
import asyncio
import httpx

BASE = "http://localhost:8000"


async def run():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("1. Parsing intent...")
        r = await client.post(f"{BASE}/buyer/intent", json={"query": "I need a heavy-duty laptop under ₹70,000"})
        r.raise_for_status()
        intent = r.json()
        session_id = intent["session_id"]
        print(f"   session_id={session_id}, budget_max={intent['constraints']['budget_max']}")
        assert intent["constraints"]["budget_max"] == 70000

        print("2. Getting merchant offers...")
        r = await client.post(f"{BASE}/merchant/offers", json={
            "constraints": intent["constraints"], "session_id": session_id,
        })
        r.raise_for_status()
        data = r.json()
        offers = data["offers"]
        assert len(offers) > 0, "No offers returned"
        top_offer = offers[0]
        print(f"   {len(offers)} offers, top pick: {top_offer['product']['name']} (₹{top_offer['base_price']})")

        print("3. Evaluating offer as buyer agent...")
        r = await client.post(f"{BASE}/buyer/evaluate-offer", json={
            "offer": top_offer, "constraints": intent["constraints"], "session_id": session_id,
        })
        r.raise_for_status()
        evaluation = r.json()
        print(f"   base_within_budget={evaluation['base_product_within_budget']}, accepted_addons={len(evaluation['accepted_addons'])}")

        print("4. Creating cart...")
        r = await client.post(f"{BASE}/checkout/cart", json={
            "offer_id": top_offer["offer_id"], "session_id": session_id,
            "selected_addon_ids": [a["product_id"] for a in evaluation["accepted_addons"]],
            "shipping_address": {
                "name": "Test Buyer", "address_line": "123 Test St",
                "city": "Bhiwani", "state": "Haryana", "pincode": "127021",
            },
        })
        r.raise_for_status()
        cart = r.json()
        cart_id = cart["cart_id"]
        print(f"   cart_id={cart_id}, items={len(cart['items'])}")

        print("5. Validating cart...")
        r = await client.post(f"{BASE}/checkout/validate/{cart_id}")
        r.raise_for_status()
        validation = r.json()
        assert validation["valid"], f"Cart should be valid: {validation}"
        print(f"   valid={validation['valid']}")

        print("6. Requesting authorization...")
        r = await client.post(f"{BASE}/checkout/authorize", json={"cart_id": cart_id})
        r.raise_for_status()
        auth = r.json()
        print(f"   level={auth['level']}, approved={auth['approved']}")

        if not auth["approved"]:
            print("7. Confirming (simulating user approval)...")
            r = await client.post(f"{BASE}/checkout/confirm", json={"cart_id": cart_id, "user_confirmed": True})
            r.raise_for_status()
            auth = r.json()
            assert auth["approved"], f"Confirmation should approve: {auth}"
            print(f"   approved={auth['approved']}")

        print("8. Initiating payment (Razorpay order)...")
        r = await client.post(f"{BASE}/checkout/initiate-payment", json={"cart_id": cart_id})
        r.raise_for_status()
        payment_init = r.json()
        assert "razorpay_order_id" in payment_init, payment_init
        print(f"   razorpay_order_id={payment_init['razorpay_order_id']}, amount=₹{payment_init['amount']}")

        print("9. Checking audit trail...")
        r = await client.get(f"{BASE}/audit/trail/{session_id}")
        r.raise_for_status()
        trail = r.json()
        print(f"   {trail['event_count']} audit events logged")
        for e in trail["events"]:
            print(f"     [{e['action']}] {e['decision']} — {e['reason']}")

        print("\nALL PHASES WIRED CORRECTLY (stopped before live Razorpay checkout).")
        print(f"To finish this manually: open test_checkout.html, use cart_id={cart_id}")


if __name__ == "__main__":
    asyncio.run(run())