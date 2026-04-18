# View/Clip — Product Requirements Document

## Product Vision
A hybrid VOD + Live Streaming platform (Hulu/ESPN meets Twitch/Bigo-Live) branded **View/Clip**, with the `/` as the central design element. Premium media feel for viewers, enterprise-grade controls for admins.

## Original Problem Statement (verbatim)
> I want a app that allows you to watch (movies, tv-shows, live sports) and you have the option to watch people who stream on the platform and interact with them through (chat comments, joining live, gifting) also streamers have the option to save their live stream and export the content to other platforms. The subscription to use the app is $7, and the subscription to be a live streamer is $100 [revised to $50] and streamers get paid $0.03 per view every 100,000 views [revised to $0.005 per qualified 30-min view] and $0.002 per gift.

## Core Requirements
1. **VOD** — Movies, TV shows, live sports catalog
2. **Live Streaming** — Streamers go live with chat, gift, and join interactions
3. **Subscriptions** — Viewer $7/mo · Streamer $50/mo
4. **Payouts** — $0.005 per qualified view (30-min watch threshold) + $0.002-$3.000 per gift unit (tier-based)
5. **Gift Tiers** — 8 bundles (500 units each), prices $10–$300, emojis 🪙🥃🥇🏆🏎🏚💎🌍
6. **Stream Tools** — Save stream, Export to YouTube/Twitch/X/custom
7. **Admin Command Center** — Editable rates, budget alert %, payout trigger, self-promotion engine, user management
8. **Security** — JWT auth, bcrypt passwords, role-based access (viewer/streamer/admin)
9. **Stripe Integration** — Checkout for subscriptions and gift bundles (via `emergentintegrations`)

## Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Lucide icons
- **Backend**: FastAPI, Motor (async MongoDB), emergentintegrations (Stripe), bcrypt, PyJWT
- **Infra**: Supervisor-managed, Kubernetes ingress, MongoDB local

---

## Implemented (CHANGELOG)

### 2026-02 (phase 4) — Production integrations with graceful fallback
- **Real Stripe Connect Express** (`stripe_service.create_connect_account`, `create_onboarding_link`, `retrieve_account`, `transfer_to_connect`) — activates automatically when `STRIPE_API_KEY` is a real test/live key. Falls back to mock onboarding when placeholder `sk_test_emergent` is set.
- **Real recurring Stripe Subscriptions** (`stripe_service.ensure_subscription_price` auto-creates Product/Price, `create_subscription_checkout` uses `mode='subscription'`, `cancel_subscription` supports `cancel_at_period_end`). Webhook processes `customer.subscription.updated/deleted`, `invoice.paid`, `account.updated`. Falls back to one-time emergentintegrations Checkout (30-day mock) when real key missing.
- **Real Stripe Transfer.create payouts** — `admin_trigger_payouts` uses `real_mode` flag; real transfers when configured, skips streamers without active Connect; mock-transfer IDs otherwise. Audit log records mode.
- **Google Cloud Live Stream API** — `live_stream_service.provision_stream` creates RTMP Input + HLS transcoding Channel + starts it; `stop_stream` tears down; `active_channels_cost` returns live cost visibility. Gated on `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT` + `LIVESTREAM_GCS_BUCKET`. Returns ingest_url + playback_url on stream create.
- **HlsPlayer React component** (`/app/frontend/src/components/HlsPlayer.jsx`) — hls.js with native Safari fallback and MP4 passthrough. StreamView uses it.
- **RTMP ingest panel** on StreamerDashboard — shows ingest URL + stream key for live streams.
- **Cancel subscription** button on Profile — appears only for real recurring Stripe subscriptions.
- **Key-rotation worker** — `/api/admin/system/rotate-keys` now genuinely generates a new Fernet key, iterates `banking_info`, decrypts with old cipher, re-encrypts with new, swaps the active cipher in-process, logs audit + system event.

### 2026-02 (phase 3) — Enterprise architecture
- **Triple-layer database** — `DBRouter` transparently maps collections to 3 logical DBs (`viewclip_identity`, `viewclip_streaming`, `viewclip_vault`). Each layer is swappable to its own physical cluster via env vars. One-shot migration on startup moved 221 documents from the legacy DB.
- **Vault field-level encryption** — Fernet (AES-128-CBC + HMAC-SHA256) for banking account/routing numbers. `/api/vault/banking` returns only last-4 masked values. Per-write audit log.
- **Level-3 Logic Firewall** — `FirewallMiddleware` with per-IP sliding-window rate limiting (default 300 req/min), global request counter, blocked-request counter, top-paths telemetry.
- **Admin System Control Panel** (`/admin` → System tab) —
  - Live health monitor for all 3 DB layers with latency
  - Encryption status (algorithm, key presence)
  - Hot-swappable cloud streaming providers (Mux / AWS IVS / Cloudflare Stream / mock)
  - Actions: Reload Settings, Deploy Update, Rotate Keys
  - System events feed + Audit log feed
- **Self-promotion engine boot seed** — 3 default View/Clip Originals promos auto-inserted on first startup; Browse page renders an "Originals Hero" strip at the top
- **$7 viewer can receive gifts** — `/api/gifts/send` now accepts `recipient_id` (direct user-to-user gifting) OR `stream_id` (stream-bound). Earnings accrue to any user, not just streamers. `/api/earnings` & `/api/earnings/total` no longer require streamer role.

### 2026-02 (phase 2) — Productivity & engagement suite
- **Referral leaderboard** — `referral_code` auto-generated on signup; `referred_by` attribution; 10% commission credited to referrer on referred user's first paid subscription; public `/api/referrals/leaderboard` endpoint; `/leaderboard` page with medal ranking
- **Follow system** — `/api/streamers/{id}/follow`, `/unfollow`, `/follow-status`, `/api/users/me/follows`; Follow button on StreamView; follower count shown
- **Notifications** — `/api/notifications` CRUD; bell icon in nav with polling every 30s; `/notifications` page; auto-created on new_follower, stream_live, gift_received, referral reward
- **Unified search** — `/api/search?q=` (content, streams, streamers); debounced search bar on Browse page
- **Trending** — `/api/trending` (top 12 VOD + top 12 live by views); horizontal strip on Browse
- **Streamer analytics** — `/api/streamers/me/analytics` (by_source, 30d time-series, top 10 gifters, gift-tier breakdown, streams summary, followers); Analytics section on StreamerDashboard with bar chart
- **Secure heartbeat** — `/api/streams/{id}/heartbeat` replaces client-side `setTimeout`; server accumulates watch-minutes in `watch_sessions` collection; auto-qualifies view at 30-min threshold exactly once per (stream_id, user_id). Anti-fraud: can't be gamed by frontend tampering.

### 2026-02 (phase 1) — Feature drop & rebrand
- **Rebranded** StreamHub → **View/Clip** (logo with animated `/` slash, new dark theme `#05070F`)
- **Stripe Checkout** integration via `emergentintegrations`:
  - `/api/payments/checkout/subscribe` (viewer $7, streamer $50)
  - `/api/payments/checkout/gift-bundle` (all 8 tiers)
  - `/api/payments/checkout/status/{session_id}` (idempotent fulfilment)
  - `/api/webhook/stripe` (signature-verified webhook)
  - `payment_transactions` collection with processed flag
- **Gift tier system** — 8 tiers (t1–t8), wallet per user, `/api/gifts/tiers`, `/api/gifts/wallet`, `/api/gifts/send`
- **Admin Command Center** — 5-tab UI (Settings/Content/Promos/Users/Payouts):
  - Editable rates: viewer_sub_price, streamer_sub_price, earnings_per_view, view_threshold_minutes, gift_base_rate, budget_alert_percent, maintenance_mode
  - Top-line stats (users, live streams, revenue, payouts owed)
  - Batch payout trigger (`/api/admin/payouts/trigger`)
- **Self-Promotion Engine** — `/api/promos` CRUD (admin); Browse feed injects a promo card every 5 content cards
- **Stream Export** — `/api/streams/{id}/export` supports youtube/twitch/x/custom; UI modal with 4 platform buttons
- **Qualified views** — `/api/streams/{id}/qualified-view` (client calls after 30-min watch) drives the $0.005 payout
- **Stripe Connect (mock)** — `/api/streamers/connect/onboard` sets `connect_account_status=active`
- **Auth screen backsplash** — Dynamic movie/TV poster grid with drift animation
- **PaymentSuccess page** — Polls checkout status up to 8×, activates subscription or credits wallet

### Earlier (2026-02, base app)
- FastAPI backend + React frontend scaffold
- Auth (JWT), content CRUD, streams CRUD, comments, basic gifts
- Base testing agent pass at 96.4%

## Test Coverage
- **Backend**: 30/30 tests passing (iteration_2.json)
- **Frontend**: All core flows verified
- Test file: `/app/backend/tests/test_viewclip_api.py`
- Test credentials: `/app/memory/test_credentials.md`

## Known Mocks (explicit)
- **Stripe Connect Express onboarding** — `/api/streamers/connect/onboard` returns mock URL. Production will call `stripe.Account.create(type='express')` + `stripe.AccountLinks.create`.
- **Stripe Connect payouts** — `/api/admin/payouts/trigger` marks earnings `paid_out=true` but doesn't invoke `stripe.Transfer.create`.
- **Live video feeds** — StreamView plays `video_url` directly. No real WebRTC/HLS pipeline.

---

## ROADMAP (P0 / P1 / P2)

### P0 — Next up
- **Real Stripe Connect** — replace mock onboarding with `stripe.Account.create` + AccountLinks; swap `admin/payouts/trigger` to `stripe.Transfer.create`.
- **Live video pipeline** — integrate Mux / AWS IVS / Cloudflare Stream (hot-swappable API Gateway layer).

### P1 — Next
- **WebSocket chat/gifts** — replace 5s comment polling with WS `/api/ws/stream/{stream_id}`; push gift animations in real-time.
- **Real YouTube/Twitch export APIs** — requires streamer OAuth; current export stores mock URLs.
- **Recurring billing** — today subscriptions are one-time 30-day; move to Stripe Subscriptions for auto-renew.
- **Password reset + email verification** (Resend integration).

### P2 — Backlog
- **AES-256 at rest** — enforce MongoDB encryption-at-rest via CSFLE (requires cloud Mongo).
- **Multi-region CDN** for VOD.
- **Creator analytics** dashboard (views over time, earnings/stream, gift heatmap).
- **Mobile app** (React Native).
- **Moderation tools** — comment filtering, stream reports, admin ban/unban.

---

## Key API Surface
| Method | Endpoint | Notes |
|---|---|---|
| POST | /api/auth/register, /login | JWT |
| GET | /api/auth/me | current user |
| GET/POST | /api/content | admin uploads |
| GET/POST | /api/promos | self-promo engine |
| GET/POST | /api/streams | +/end, /join, /qualified-view, /save, /export |
| GET | /api/gifts/tiers, /wallet | |
| POST | /api/gifts/send | wallet-backed gifting |
| POST | /api/payments/checkout/subscribe, /gift-bundle | Stripe |
| GET | /api/payments/checkout/status/{session_id} | polling |
| POST | /api/webhook/stripe | |
| GET/POST | /api/admin/settings | rates, budget alert |
| GET | /api/admin/stats, /users, /payouts | |
| POST | /api/admin/payouts/trigger | batch mock payouts |
| POST | /api/streamers/connect/onboard | mock |

## DB Collections
- `users` — incl. gift_wallet, connect_account_status
- `content` — incl. is_promo flag
- `live_streams` — incl. qualified_views, saved, exports[]
- `comments`, `gifts`, `earnings`, `subscriptions`
- `payment_transactions` — Stripe checkout audit log with `processed` flag
- `settings` — global platform settings (singleton id="global")
- `payouts` — mock transfer history
