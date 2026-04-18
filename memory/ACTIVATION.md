# Activating Real Mode — View/Clip

Zero code changes required. Backend auto-detects real credentials on boot and switches out of mock mode.

## 1. Stripe (real subscriptions + Connect + payouts)

Edit `/app/backend/.env` and set these two values:

```bash
STRIPE_API_KEY=sk_test_...            # or sk_live_... in production
STRIPE_WEBHOOK_SECRET=whsec_...       # from Stripe dashboard → Webhooks
```

Then restart: `sudo supervisorctl restart backend`

### Where to get each value
- `STRIPE_API_KEY` → https://dashboard.stripe.com/test/apikeys → copy **Secret key**
- `STRIPE_WEBHOOK_SECRET` →
  1. https://dashboard.stripe.com/test/webhooks → **Add endpoint**
  2. URL: `https://<YOUR-APP>.preview.emergentagent.com/api/webhook/stripe`
  3. Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `account.updated`
  4. After saving → click endpoint → **Reveal signing secret** → copy `whsec_...`

### What happens after activation
- Viewer/Streamer subscriptions issue **real recurring monthly billing** (Stripe auto-creates Product/Price on first checkout)
- Streamer **Connect** onboarding opens the real Stripe-hosted Express flow; `account.updated` webhook keeps status in sync
- `POST /api/admin/payouts/trigger` runs real `stripe.Transfer.create` to each streamer's Connect account
- "Cancel at period end" button becomes functional on Profile

Verify:
```bash
curl -s http://localhost:8001/api/admin/system/health -H "Authorization: Bearer $ADMIN_TOKEN" | grep stripe_mode
# should show: "stripe_mode": "real"
```

## 2. Google Cloud Live Stream (real RTMP → HLS)

Edit `/app/backend/.env` and set:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
LIVESTREAM_GCS_BUCKET=your-bucket-name
LIVESTREAM_LOCATION=us-central1       # optional — default is us-central1

# EITHER paste the service account JSON inline (recommended — no file to upload):
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n","client_email":"...","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}

# OR point to a file you've uploaded into the container:
# GOOGLE_APPLICATION_CREDENTIALS=/app/backend/gcp-service-account.json
```

Then restart: `sudo supervisorctl restart backend`

### Where to get each value
- **Project ID** → https://console.cloud.google.com/ → project selector (top bar)
- **GCS Bucket** → https://console.cloud.google.com/storage/browser → **Create bucket** (Standard, uniform access)
- **Service Account JSON**:
  1. Enable the Live Stream API: https://console.cloud.google.com/apis/library/livestream.googleapis.com
  2. https://console.cloud.google.com/iam-admin/serviceaccounts → **Create Service Account** named `viewclip-livestream`
  3. Grant roles: **Live Stream API Admin**, **Storage Object Admin**
  4. Open the account → **Keys** → **Add Key → Create new key → JSON** → downloads a `.json` file
  5. Open the file, copy the entire contents, and paste as `GOOGLE_SERVICE_ACCOUNT_JSON=...` on a single line (JSON stays valid with escaped `\n` in the private_key field)

### What happens after activation
- `POST /api/streams` provisions a real GCP Live Stream **Input (RTMP_PUSH)** + transcoding **Channel**. Response returns:
  - `ingest_url` = `rtmp://...googleapis.com/...` — streamer plugs into OBS
  - `playback_url` = `https://storage.googleapis.com/<bucket>/streams/<id>/manifest.m3u8` — viewers watch HLS
  - `live_mode: "gcp"` (mock returns `"mock"`)
- `POST /api/streams/{id}/end` tears down channel + input
- Admin health card shows `"livestream_mode": "gcp-livestream"`
- Active channel count + rough $/hour cost visible at `GET /api/admin/streaming/providers`

Verify after adding creds + restart:
```bash
sudo supervisorctl restart backend
sleep 3
tail -n 5 /var/log/supervisor/backend.err.log   # should say "Live Stream: REAL (GCP)"
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `"stripe_mode": "mock (emergentintegrations)"` after adding key | Value is `sk_test_emergent` (placeholder) or missing `sk_` prefix | Double-check you pasted the real secret key from dashboard.stripe.com |
| Stripe checkout returns 502 | Webhook secret missing or invalid API key | Check backend log; re-copy `whsec_...` exactly |
| `livestream_mode` still `mock` | Any of Project ID / Bucket / JSON missing | Check `/api/admin/system/health` → `integrations` field |
| `google.api_core.exceptions.PermissionDenied` in log | Service account missing **Live Stream API Admin** role | Re-add the role in IAM & re-download key JSON |
| RTMP ingest connects but viewer sees nothing | GCS bucket not public-readable | Grant `Storage Object Viewer` to `allUsers` on the bucket (or use signed URLs) |

## Safety notes
- `.env` is **not** committed to git — safe to store secrets here
- Never log `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, or `GOOGLE_SERVICE_ACCOUNT_JSON` contents
- Rotate Stripe keys periodically via dashboard → "Roll secret key"
- Rotate GCP key via IAM → service account → **Keys** → disable old, create new
- Internal Vault encryption key rotation: admin UI → System tab → **Rotate Keys** (re-encrypts banking_info with a new Fernet key)
