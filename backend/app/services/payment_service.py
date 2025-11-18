"""Payment service for Stripe integration"""
import stripe
from typing import Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling payments via Stripe"""

    # Pricing tiers (in cents)
    TIERS = {
        "starter": {
            "name": "Starter",
            "price": 160000,  # $1,600
            "api_calls": 10000,
            "features": ["Email support", "Basic analytics"]
        },
        "professional": {
            "name": "Professional",
            "price": 800000,  # $8,000
            "api_calls": 50000,
            "features": [
                "Priority processing",
                "Priority support (24hr response)",
                "Advanced analytics",
                "Custom schemas (up to 5)"
            ]
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 0,  # Custom pricing
            "api_calls": 200000,
            "features": [
                "Dedicated infrastructure",
                "Custom integrations",
                "Phone support",
                "On-premise option",
                "SLA guarantees"
            ]
        }
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize payment service

        Args:
            api_key: Stripe API key (defaults to settings)
        """
        # In production, set this from environment variable
        # stripe.api_key = api_key or settings.STRIPE_API_KEY

        # For MVP, we'll use test mode
        self.test_mode = True
        logger.info(f"Payment service initialized (test_mode={self.test_mode})")

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe payment intent

        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            customer_email: Customer email for receipt
            metadata: Additional metadata

        Returns:
            Payment intent object
        """
        try:
            if self.test_mode:
                # Mock payment intent for testing
                return {
                    "id": f"pi_test_{hash(amount)}",
                    "amount": amount,
                    "currency": currency,
                    "status": "requires_payment_method",
                    "client_secret": f"secret_test_{hash(amount)}",
                    "metadata": metadata or {}
                }

            # Real Stripe integration
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                receipt_email=customer_email,
                metadata=metadata or {}
            )

            return {
                "id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status,
                "client_secret": intent.client_secret,
                "metadata": intent.metadata
            }

        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            raise

    def create_checkout_session(
        self,
        tier: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for a tier purchase

        Args:
            tier: Tier name (starter, professional, enterprise)
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            customer_email: Customer email
            user_id: User ID for metadata

        Returns:
            Checkout session object
        """
        try:
            if tier not in self.TIERS:
                raise ValueError(f"Invalid tier: {tier}")

            tier_info = self.TIERS[tier]

            if tier_info["price"] == 0:
                raise ValueError("Enterprise tier requires custom pricing. Contact sales.")

            if self.test_mode:
                # Mock checkout session
                return {
                    "id": f"cs_test_{hash(tier)}",
                    "url": f"https://checkout.stripe.com/test/{tier}",
                    "amount_total": tier_info["price"],
                    "metadata": {
                        "tier": tier,
                        "user_id": str(user_id) if user_id else None,
                        "api_calls": tier_info["api_calls"]
                    }
                }

            # Real Stripe checkout
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{tier_info['name']} Package",
                            "description": f"{tier_info['api_calls']:,} API calls"
                        },
                        "unit_amount": tier_info["price"]
                    },
                    "quantity": 1
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    "tier": tier,
                    "user_id": str(user_id) if user_id else None,
                    "api_calls": tier_info["api_calls"]
                }
            )

            return {
                "id": session.id,
                "url": session.url,
                "amount_total": session.amount_total,
                "metadata": session.metadata
            }

        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    def confirm_payment(self, payment_intent_id: str) -> bool:
        """
        Confirm a payment intent

        Args:
            payment_intent_id: Payment intent ID

        Returns:
            True if payment successful
        """
        try:
            if self.test_mode:
                # Mock confirmation
                return True

            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent.status == "succeeded"

        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            return False

    def refund_payment(self, payment_intent_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Refund a payment

        Args:
            payment_intent_id: Payment intent ID
            amount: Amount to refund in cents (None for full refund)

        Returns:
            Refund object
        """
        try:
            if self.test_mode:
                return {
                    "id": f"re_test_{hash(payment_intent_id)}",
                    "amount": amount or 0,
                    "status": "succeeded"
                }

            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount
            )

            return {
                "id": refund.id,
                "amount": refund.amount,
                "status": refund.status
            }

        except Exception as e:
            logger.error(f"Error creating refund: {e}")
            raise

    def get_tier_info(self, tier: str) -> Dict[str, Any]:
        """Get information about a pricing tier"""
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        return self.TIERS[tier].copy()

    def get_all_tiers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all pricing tiers"""
        return {
            tier: self.get_tier_info(tier)
            for tier in self.TIERS.keys()
        }

    def calculate_usage_cost(self, api_calls: int, tier: str = "professional") -> float:
        """
        Calculate cost per API call for a tier

        Args:
            api_calls: Number of API calls
            tier: Tier name

        Returns:
            Cost per call in dollars
        """
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        tier_info = self.TIERS[tier]
        if tier_info["price"] == 0:
            return 0.0  # Custom pricing

        # Cost in dollars
        total_cost = tier_info["price"] / 100  # Convert cents to dollars
        included_calls = tier_info["api_calls"]

        cost_per_call = total_cost / included_calls
        return cost_per_call


# Singleton instance
_payment_service_instance = None


def get_payment_service() -> PaymentService:
    """Get or create payment service singleton"""
    global _payment_service_instance
    if _payment_service_instance is None:
        _payment_service_instance = PaymentService()
    return _payment_service_instance
