"""Stripe service — Connect Express accounts + recurring Subscriptions + Transfers.
Uses the official `stripe` Python SDK (not the emergentintegrations helper).
Gift bundle one-time Checkout continues to use emergentintegrations.

Graceful fallback: if STRIPE_API_KEY is the emergentintegrations placeholder
(`sk_test_emergent`) or is missing, real_stripe_enabled() returns False and
callers should route via the existing emergentintegrations Checkout helper.
"""
import os
import logging
from typing import Optional, Dict, Any

import stripe

logger = logging.getLogger(__name__)

_RAW_KEY = os.environ.get("STRIPE_API_KEY", "").strip()
stripe.api_key = _RAW_KEY

_PRICE_CACHE: Dict[str, str] = {}  # sub_type -> stripe_price_id


def real_stripe_enabled() -> bool:
    """True when a real Stripe secret key (sk_test_xxx or sk_live_xxx of sufficient length) is configured.
    The `sk_test_emergent` placeholder returns False — caller should fall back to emergentintegrations helper."""
    if not _RAW_KEY:
        return False
    if _RAW_KEY == "sk_test_emergent":
        return False
    return _RAW_KEY.startswith(("sk_test_", "sk_live_")) and len(_RAW_KEY) > 20


# ---------------------------------------------------------------------------
# Recurring subscriptions — auto-create Product/Price once, then reuse
# ---------------------------------------------------------------------------
async def ensure_subscription_price(sub_type: str, amount_usd: float) -> str:
    """Create-or-reuse a recurring monthly Stripe Price for a subscription tier."""
    cache_key = f"{sub_type}:{amount_usd}"
    if cache_key in _PRICE_CACHE:
        return _PRICE_CACHE[cache_key]

    lookup = f"viewclip_{sub_type}_monthly_{int(amount_usd * 100)}"
    existing = stripe.Price.list(lookup_keys=[lookup], active=True, limit=1)
    if existing.data:
        price_id = existing.data[0].id
    else:
        product = stripe.Product.create(
            name=f"View/Clip {sub_type.capitalize()} Subscription",
            metadata={"tier": sub_type},
        )
        price = stripe.Price.create(
            product=product.id,
            currency="usd",
            unit_amount=int(round(amount_usd * 100)),
            recurring={"interval": "month"},
            lookup_key=lookup,
            metadata={"tier": sub_type},
        )
        price_id = price.id
        logger.info(f"Created Stripe recurring price {price_id} for {sub_type} @ ${amount_usd}/mo")

    _PRICE_CACHE[cache_key] = price_id
    return price_id


def create_subscription_checkout(
    *, price_id: str, customer_email: str, user_id: str, sub_type: str,
    success_url: str, cancel_url: str,
) -> Dict[str, Any]:
    """Create a Checkout Session in mode=subscription — auto-renewing monthly."""
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=customer_email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id, "sub_type": sub_type, "purpose": "subscription"},
        subscription_data={"metadata": {"user_id": user_id, "sub_type": sub_type}},
    )
    return {"url": session.url, "session_id": session.id}


def cancel_subscription(subscription_id: str, at_period_end: bool = True):
    """Cancel subscription. By default at period end (user keeps access until renewal date)."""
    if at_period_end:
        return stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    return stripe.Subscription.delete(subscription_id)


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


# ---------------------------------------------------------------------------
# Stripe Connect Express — real onboarding + transfers
# ---------------------------------------------------------------------------
def create_connect_account(email: str, country: str = "US") -> str:
    account = stripe.Account.create(
        type="express",
        country=country,
        email=email,
        capabilities={"transfers": {"requested": True}, "card_payments": {"requested": True}},
        business_type="individual",
    )
    return account.id


def create_onboarding_link(account_id: str, refresh_url: str, return_url: str) -> str:
    link = stripe.AccountLinks.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return link.url


def retrieve_account(account_id: str) -> Dict[str, Any]:
    acct = stripe.Account.retrieve(account_id)
    return {
        "id": acct.id,
        "charges_enabled": acct.charges_enabled,
        "payouts_enabled": acct.payouts_enabled,
        "details_submitted": acct.details_submitted,
        "requirements_due": list(getattr(acct.requirements, "currently_due", []) or []),
    }


def transfer_to_connect(account_id: str, amount_usd: float, description: str = "") -> Dict[str, Any]:
    tr = stripe.Transfer.create(
        amount=int(round(amount_usd * 100)),
        currency="usd",
        destination=account_id,
        description=description[:200] if description else None,
    )
    return {"id": tr.id, "amount": tr.amount / 100.0, "destination": tr.destination, "created": tr.created}


# ---------------------------------------------------------------------------
# Webhook signature verification (native stripe SDK)
# ---------------------------------------------------------------------------
def verify_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        return None
    try:
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as e:
        logger.warning(f"Stripe webhook verification failed: {e}")
        return None
