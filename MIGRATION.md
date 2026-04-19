# View/Clip — Migration Guide

**Goal:** move this codebase off Emergent to any server, cloud VM, Kubernetes cluster, or a hybrid setup (frontend on Vercel + backend on Fly.io + DB on Atlas) **without losing any data or functionality**.

Every section below is self-contained — you can skip the ones that don't apply.

---

## TL;DR — the 5-minute migration plan

```bash
# 1. Export everything off Emergent in one shot
bash scripts/export_for_migration.sh ~/viewclip-export

# 2. Spin the whole stack up on any Docker host
docker compose up -d

# 3. Swap MongoDB to Atlas later by changing ONE env var (MONGO_URL)
```

That's it. Nothing on Emergent is load-bearing once you have the export bundle + your `.env` files.

---

## 1. Inventory — what actually needs to move

| Asset | Where it lives today | Where it must live after | Emergent-specific? |
|---|---|---|---|
| Backend code | `/app/backend` | Any Python 3.11+ host | No |
| Frontend code | `/app/frontend` | Any Node 20+ / static host | No |
| MongoDB data | Local Mongo in the pod | Atlas / self-host / RDS Document DB | **Yes — must dump/restore** |
| Env vars (secrets) | `/app/backend/.env`, `/app/frontend/.env` | Your secret manager | **Yes — hidden in Emergent UI** |
| Supervisor config | `/etc/supervisor/conf.d/` | systemd / Docker / k8s Deployment | Replace |
| Proprietary SDK | `emergentintegrations` (PyPI: custom index) | Replace with official `stripe` + `openai` SDKs | **Yes — see §6** |
| Preview URL | `*.preview.emergentagent.com` | Your domain + your CDN | Replace |

Anything not on that list is portable out of the box.

---

## 2. Environment variables — exporting & templates

**IMPORTANT**: Emergent hides the `.env` file contents in the UI. Pull the files directly from the pod before exporting:

```bash
# Inside the Emergent pod:
cat /app/backend/.env   > /tmp/backend.env
cat /app/frontend/.env  > /tmp/frontend.env
```

Canonical templates live in the repo:
- [`backend/.env.example`](./backend/.env.example)
- [`frontend/.env.example`](./frontend/.env.example)

### Backend variables — grouped

| Variable | Required? | Default | What it does |
|---|---|---|---|
| `MONGO_URL` | ✅ | `mongodb://localhost:27017` | Mongo connection string. Swap to Atlas `mongodb+srv://…` when migrating. |
| `DB_NAME` | ✅ | `streaming_platform` | Legacy single-DB name (kept for one-shot migration). |
| `DB_NAME_IDENTITY` | ✅ | `viewclip_identity` | Layer 1 DB: users, auth, referrals, notifications. |
| `DB_NAME_STREAMING` | ✅ | `viewclip_streaming` | Layer 2 DB: streams, content, comments, gifts. |
| `DB_NAME_VAULT` | ✅ | `viewclip_vault` | Layer 3 DB: banking, earnings, payouts. |
| `VAULT_ENCRYPTION_KEY` | ✅ | (auto-generated) | Fernet key used for `banking_info.*_enc` **and** `users.totp_secret`. **If you lose this you cannot decrypt existing vault data.** |
| `JWT_SECRET` | ✅ | `your-secret…` | HS256 signing key. Change BEFORE production. Changing it invalidates every existing session token — plan for a re-login. |
| `APP_VERSION` | ⛔ | `1.4.0` | Cosmetic — shown in admin health + `/api/health`. |
| `APP_ENV` | ⛔ | `development` | Free-form tag for logs. |
| `CORS_ORIGINS` | ✅ | `*` | Comma-separated origins allowed by CORSMiddleware. Set to your frontend origin in prod. |
| `FIREWALL_RATE_LIMIT_PER_MIN` | ⛔ | `300` | Sliding-window per-IP rate limit. |
| `ADMIN_IP_ALLOWLIST` | ⛔ | *empty* | Comma-separated IPs/CIDRs allowed to reach `/api/admin/*`. Empty = disabled. |
| `STRIPE_API_KEY` | ✅ for payments | `sk_test_emergent` | `sk_test_…` or `sk_live_…`. The placeholder triggers mock mode. |
| `STRIPE_WEBHOOK_SECRET` | ✅ for real subscriptions | *empty* | `whsec_…` from Stripe dashboard. |
| `GOOGLE_CLOUD_PROJECT` | optional | *empty* | For real HLS streaming. Mock mode until all 3 GCP vars are set. |
| `LIVESTREAM_GCS_BUCKET` | optional | *empty* | GCS bucket receiving HLS segments. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | optional | *empty* | JSON string (preferred, no file). |
| `GOOGLE_APPLICATION_CREDENTIALS` | optional | *empty* | Alt: filesystem path to service-account JSON. |
| `LIVESTREAM_LOCATION` | ⛔ | `us-central1` | GCP region. |

### Frontend variables

| Variable | Required? | What it does |
|---|---|---|
| `REACT_APP_BACKEND_URL` | ✅ | Base URL of the backend (no trailing slash, no `/api`). |
| `WDS_SOCKET_PORT` | ⛔ | Dev-only, webpack HMR socket port. |
| `REACT_APP_ENABLE_VISUAL_EDITS` | ⛔ | Emergent-only feature flag — set to `false` or remove. |
| `ENABLE_HEALTH_CHECK` | ⛔ | Emergent platform probe — remove after migration. |

---

## 3. MongoDB — moving off the pod

### Option A — MongoDB Atlas (recommended, fully managed)

1. Create a free **M0** cluster at https://cloud.mongodb.com. Region = same as your backend.
2. **Network Access** → add `0.0.0.0/0` for testing (tighten to your backend egress IP after go-live).
3. **Database Access** → create a user `viewclip_app` with *Atlas admin* role for initial import; downgrade to `readWrite` on the 3 DBs afterwards.
4. Dump everything off the current pod:
   ```bash
   mongodump --uri="mongodb://localhost:27017" --out=/tmp/mongodump_$(date +%F)
   ```
5. Restore into Atlas:
   ```bash
   mongorestore --uri="mongodb+srv://viewclip_app:<PASSWORD>@<CLUSTER>.mongodb.net/" /tmp/mongodump_<DATE>
   ```
6. Update `backend/.env`:
   ```bash
   MONGO_URL="mongodb+srv://viewclip_app:<PASSWORD>@<CLUSTER>.mongodb.net/?retryWrites=true&w=majority"
   ```
7. Restart backend → verify at `/api/admin/system/health` that all 3 layers show `status: ok`.

### Option B — Self-host Mongo in Docker

Already wired in the repo's [`docker-compose.yml`](./docker-compose.yml). Data is persisted to a named volume `viewclip-mongo-data`. Back it up with:
```bash
docker run --rm -v viewclip-mongo-data:/data/db -v $(pwd):/backup alpine tar czf /backup/mongo-backup.tgz /data/db
```

### Option C — AWS DocumentDB

Works as a drop-in with these caveats:
- `motor`/`pymongo` 4.x requires TLS → append `?tls=true&tlsCAFile=global-bundle.pem`.
- Aggregation pipelines we use (`admin_analytics`, `stream_earnings`) are all supported by DocDB 5.0+.

### ⚠️ Don't forget the vault key!

Banking info and admin TOTP secrets are encrypted with `VAULT_ENCRYPTION_KEY`. **Copy the key BEFORE you wipe the old pod.** Without it, those documents become unreadable ciphertext.

Recommended production pattern: store the key in AWS Secrets Manager / GCP Secret Manager and inject it as env var at boot.

---

## 4. Secrets — where to store them after migration

| Target host | Recommended secret store |
|---|---|
| AWS ECS / EKS | AWS Secrets Manager → ECS task secrets |
| GCP Cloud Run / GKE | GCP Secret Manager → env mapping |
| Fly.io | `fly secrets set VAULT_ENCRYPTION_KEY=…` |
| Vercel (frontend only) | Project → Settings → Environment Variables |
| Bare metal / Docker | `.env` file restricted to `chmod 600`, loaded via `env_file:` in `docker-compose.yml` |

The only secrets that **must** be identical between environments (to decrypt existing data) are `VAULT_ENCRYPTION_KEY` and whatever key was used to sign JWTs issued to already-logged-in users (`JWT_SECRET`).

---

## 5. Infrastructure — replacing Supervisor

Emergent uses supervisor. On any other host:

| Host | Replacement |
|---|---|
| Docker / docker-compose | Use the bundled [`docker-compose.yml`](./docker-compose.yml). |
| Kubernetes | Convert each service to a `Deployment` + `Service`. Use `/api/health` as liveness and `/api/ready` as readiness (already implemented). |
| Bare metal | Two `systemd` units, one per service. Template in [`deploy/systemd/`](./deploy/systemd/). |
| Fly.io | `fly launch` from `/app/backend`; frontend goes to Vercel/Netlify. |
| Render / Railway | Both detect `requirements.txt` + `package.json` automatically. |

---

## 6. Dependencies — proprietary vs portable

Run [`scripts/audit_deps.sh`](./scripts/audit_deps.sh) to check for platform-locked packages. See [`DEPENDENCY_AUDIT.md`](./DEPENDENCY_AUDIT.md) for the full report. Summary:

- **`emergentintegrations`** (Python) — **proprietary**, installed from Emergent's custom index. Used only for the Stripe Checkout helper. [`DEPENDENCY_AUDIT.md`](./DEPENDENCY_AUDIT.md) includes a drop-in replacement using the official `stripe` Python SDK we already ship. Mock mode + real mode keep working either way.
- Everything else (FastAPI, Motor, React 19, TailwindCSS, Shadcn UI, Lucide, Axios, hls.js, etc.) is standard open-source and ships from PyPI/npm.

---

## 7. Export bundle — the one-command way

```bash
bash scripts/export_for_migration.sh [/output/dir]
```

Produces:
```
viewclip-export-2026-02-18/
├── code/                       # full repo snapshot (excluding node_modules, __pycache__, .git internals)
├── env/
│   ├── backend.env             # your real secrets — treat carefully
│   └── frontend.env
├── mongo/
│   ├── mongodump/              # mongodump output, one folder per DB
│   └── restore.sh              # one-liner to restore into any Mongo URI
├── CHECKLIST.md                # step-by-step cutover checklist
└── MANIFEST.json               # git SHA, timestamp, record counts per collection
```

The script is read-only. It never touches your live pod. Re-runnable.

---

## 8. Post-migration smoke test

Run this from a machine that can reach your new backend:

```bash
API=https://api.your-domain.com
curl -s $API/api/health      # {"status":"ok","version":"1.4.0"}
curl -s $API/api/ready       # {"status":"ready"} — confirms Mongo reachable
curl -s -X POST $API/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@viewclip.com","password":"Admin123!"}' | jq .
```

If all three succeed, your migration is green. Then log in at `https://your-frontend.com/admin/login`, System tab, and confirm:
- `version: 1.4.0`
- All three DB layers `status: ok`
- `stripe_mode` and `livestream_mode` reflect your real/mock state
- Audit log shows the new admin login entry

---

## 9. Rollback plan

If migration goes sideways:
1. Point `MONGO_URL` back at the Emergent pod Mongo (it still exists until you kill the pod).
2. Roll DNS back to `*.preview.emergentagent.com`.
3. Debug at leisure.

Because we never mutate source data during export, the old environment stays a hot standby until you decide otherwise.
