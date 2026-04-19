# View/Clip — Dependency Audit

Last updated: 2026-02-18 · App version 1.4.0

**Methodology:** every entry in `backend/requirements.txt` and `frontend/package.json` was checked against three criteria — (1) open-source with public PyPI/npm distribution, (2) installable without a custom index/registry, (3) replaceable by a well-known alternative. Any package failing (1) or (2) is flagged as proprietary.

---

## Summary

| Stack | Total | Portable | **Proprietary** | Notes |
|---|---:|---:|---:|---|
| Backend (pip) | 69 | 68 | **1** | `emergentintegrations` |
| Frontend (npm) | ~40 | ~40 | 0 | — |

One proprietary package. Drop-in replacement documented below. No blockers for migration.

---

## 🔴 Proprietary packages

### `emergentintegrations==0.1.1`

- **Installed from:** `https://d33sy5i8bnduwe.cloudfront.net/simple/` (Emergent private index)
- **Used in:** `backend/server.py` — `StripeCheckout`, `CheckoutSessionRequest`, `CheckoutStatusResponse` for one-time Stripe Checkout sessions (gift bundles, fallback subscription checkout).
- **Why it's a blocker:** not on public PyPI; `pip install emergentintegrations` fails on any vanilla Python environment.
- **What it actually wraps:** the exact same calls you'd make to the official `stripe` Python SDK. No AI magic, no secret sauce — it's a thin wrapper.

#### Drop-in replacement (already shipped — `backend/stripe_service.py`)

The `stripe_service.create_subscription_checkout()` function uses the official `stripe` SDK for real recurring subscriptions. To replace `emergentintegrations` for **gift bundles and legacy one-time checkouts**, add this tiny helper and swap two call sites:

```python
# backend/stripe_native.py  (new file)
import stripe, os
stripe.api_key = os.environ["STRIPE_API_KEY"]

def create_checkout(amount_usd: float, success_url: str, cancel_url: str,
                    metadata: dict | None = None):
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": metadata.get("label", "View/Clip")},
                "unit_amount": int(round(amount_usd * 100)),
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata or {},
    )
    return session.id, session.url

def retrieve_session(session_id: str):
    return stripe.checkout.Session.retrieve(session_id)
```

Then in `server.py`, replace the two `StripeCheckout(...).create_checkout_session(...)` calls (gift bundles + mock-mode subscription fallback) with `create_checkout(...)` above. Remove `from emergentintegrations.payments.stripe.checkout import …` and drop the line from `requirements.txt`.

The file `stripe_native.py` is **optional**: if you never leave Emergent, the current code keeps working. If you migrate, uncomment/apply that swap and you're done.

---

## 🟢 Portable packages (highlights)

| Package | Version | Role |
|---|---|---|
| `fastapi` | 0.110.1 | REST API framework |
| `motor` / `pymongo` | 3.3.1 / 4.5.0 | Async MongoDB driver |
| `cryptography` | 46.0.3 | Fernet (AES-128-CBC + HMAC-SHA256) vault encryption |
| `pyotp` + `qrcode` | latest | Admin TOTP 2FA |
| `stripe` | latest (via `stripe_service.py`) | Real Stripe Connect + Subscriptions |
| `google-cloud-video-live-stream` | latest (via `live_stream_service.py`) | Real GCP HLS pipeline |
| `bcrypt`, `PyJWT` | 4.1.3 / 2.10.1 | Password hashing + JWT |
| `uvicorn` | 0.25.0 | ASGI server |

Frontend — every entry in `package.json` is public npm:
- React 19, TailwindCSS, Shadcn UI (self-vendored in `components/ui/`), Lucide icons, Axios, hls.js, Sonner, Motion.

---

## 🧪 How to re-run this audit

```bash
bash scripts/audit_deps.sh
```

Fails CI (exit 1) if any new dependency is installed from a non-PyPI / non-npm registry, or if any backend import starts with `emergent` after the drop-in replacement is applied.
