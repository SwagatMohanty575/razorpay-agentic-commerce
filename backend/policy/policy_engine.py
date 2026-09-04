from backend.config import settings
from backend.schemas.payment import Authorization, AuthorizationLevel


class PolicyEngine:
    """Deterministic authorization gate — no LLM involved. Thresholds are
    configurable via .env; every decision states exactly why."""

    def evaluate(self, cart_id: str, amount: float) -> Authorization:
        if amount <= settings.auto_approve_max_inr:
            return Authorization(
                cart_id=cart_id, amount=amount,
                level=AuthorizationLevel.AUTO_APPROVED, approved=True,
                reason=f"Amount ₹{amount:.0f} is within auto-approve limit of ₹{settings.auto_approve_max_inr}",
            )
        if amount <= settings.user_confirm_max_inr:
            return Authorization(
                cart_id=cart_id, amount=amount,
                level=AuthorizationLevel.USER_CONFIRMATION_REQUIRED, approved=False,
                reason=f"Amount ₹{amount:.0f} exceeds ₹{settings.auto_approve_max_inr}; user confirmation required",
            )
        return Authorization(
            cart_id=cart_id, amount=amount,
            level=AuthorizationLevel.EXPLICIT_AUTH_REQUIRED, approved=False,
            reason=f"Amount ₹{amount:.0f} exceeds ₹{settings.user_confirm_max_inr}; explicit authorization required before payment",
        )

    def confirm(self, cart_id: str, amount: float, user_confirmed: bool) -> Authorization:
        pending = self.evaluate(cart_id, amount)
        if pending.level == AuthorizationLevel.AUTO_APPROVED:
            return pending
        if user_confirmed:
            return Authorization(
                cart_id=cart_id, amount=amount, level=pending.level, approved=True,
                reason=f"{pending.reason}; user explicitly confirmed",
            )
        return Authorization(
            cart_id=cart_id, amount=amount, level=AuthorizationLevel.DENIED, approved=False,
            reason="User did not confirm — payment blocked",
        )