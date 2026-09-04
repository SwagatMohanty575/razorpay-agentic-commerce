import razorpay
from backend.config import settings


class RazorpayAdapter:
    """Single integration boundary for Razorpay. No other file should
    import the razorpay SDK directly — this keeps credentials and API
    surface in one place, per the architecture principle."""

    def __init__(self):
        self.client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    def create_order(self, amount_inr: float, receipt: str) -> dict:
        amount_paise = int(round(amount_inr * 100))  # Razorpay uses paise
        return self.client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        })

    def verify_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def fetch_payment(self, payment_id: str) -> dict:
        return self.client.payment.fetch(payment_id)