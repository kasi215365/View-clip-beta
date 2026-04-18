# View/Clip — Test Credentials

## Admin
- Email: `admin@viewclip.com`
- Password: `Admin123!`
- Role: admin (created during smoke test on 2026-02)

## Creating test users
Register via the /auth page (Sign Up tab) — pick "Viewer" or "Streamer" role.
Streamers must subscribe ($50 via Stripe Checkout — pod has `sk_test_emergent`)
to create live streams.

## Stripe Test Cards (for checkout flows)
- Success: `4242 4242 4242 4242`, any future date, any CVC, any ZIP
- 3D Secure: `4000 0025 0000 3155`
- Declined: `4000 0000 0000 0002`

## Preview URL
Check `REACT_APP_BACKEND_URL` in `/app/frontend/.env`.
