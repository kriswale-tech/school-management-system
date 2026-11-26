# Deployment Readiness Checklist

**Target:** One Hetzner VPS, with separate dev and production environments.

This is the working deployment checklist for the repository. The VPS layout is one Hetzner server with separate dev and production Compose projects; the existing host Caddy serves the frontends and proxies API requests. GHCR holds the private backend image, tagged by commit SHA for deployment and by environment plus SHA for retention. See [`deployment-operations.md`](deployment-operations.md) for the up-to-date operational state and release/image cleanup policy.

## Current state and blockers

- [x] Django security and URL settings now come from the environment; deployed environments reject debug mode, wildcard/missing hosts, non-HTTPS origins, missing URLs, and weak/missing secret keys.
- [x] Keep root `compose.yml` for local development; separate `compose.deploy.yml` plus `compose.dev.yml` and `compose.prod.yml` define the server stacks.
- [x] Production backend image uses Gunicorn, a non-root runtime, collected static files, and a health check. Frontends are built as static files for host Caddy; no production frontend images are needed.
- [x] Deployment Compose files use separate project names, volumes, databases, Redis instances, and loopback-only published ports for host Caddy.
- [x] A CI workflow now checks backend tests/migrations, both frontend typechecks/builds (plus school frontend lint), the production backend image build, and the `dev`-only source rule for PRs into `main`.
- [x] GitHub `main` ruleset blocks direct pushes and requires CI checks. Pull requests into `main` must come from `dev`; successful pushes to `dev` and `main` invoke the matching deployment.
- [x] `.env.dev` and `.env.prod` are stored in their matching directories on the VPS. Production email is disabled while SES remains in the sandbox and the production-access request is under review.
- [x] The dev site and email delivery paths have been smoke-tested. The first production deployment and end-to-end school workflow have not been completed.
- [x] Frontend deployment retains the current release and three previous releases per frontend/environment. VPS image cleanup removes unused SchoolAssist backend image tags after successful deployment while preserving images used by containers.
- [ ] GHCR retention keeps the current plus three previous environment-tagged backend image versions. Grant the GitHub Actions workflow Admin access to the GHCR package so it can delete older versions; pre-retention SHA-only versions remain untouched until reviewed.
- [ ] `MIGRATION_FILE_STORAGE` defaults to local disk. Production should use private R2 storage for migration staging files; bulk-import failure files currently use app-local disk and need an explicit persistence/expiry plan.
- [x] `.github/workflows/deploy.yml` is called from CI and dev deployment has succeeded. The production deployment remains pending.
- [ ] Update `docs/STATUS.md` after deployment work is finalized; its older status notes are not the deployment source of truth.

## Environment separation to establish

- [x] GitHub Environments `development` and `production` exist with matching deploy secrets/variables and branch restrictions.
- [x] Pushes to `dev` and `main` deploy the matching stack only after CI passes. Pull requests run CI but do not deploy.
- [x] Use one Hetzner VPS with isolated Compose projects, networks, volumes, databases, Redis instances, credentials, and domains. Never point dev at production data or services.
- [x] Use host Caddy as the public HTTPS reverse proxy; app ports bind to localhost and database/Redis ports are not published.
- [x] Keep `.env.dev` and `.env.prod` in their matching per-environment deployment directories under `~/school-management-system/` on the VPS and ignored by Git.
- [x] Use separate hostnames: `dev.schoolassistgh.com`, `dev-admin.schoolassistgh.com`, `dev-api.schoolassistgh.com`, and production `app.schoolassistgh.com`, `admin.schoolassistgh.com`, `api.schoolassistgh.com`.
- [ ] Give each environment its own PostgreSQL database/volume, Redis namespace or instance, object-storage bucket/prefix and credentials, Cloudinary credentials/folder, Arkesel sender/key, Paystack test/live keys and webhook, SES sender/configuration set, Django secret, and admin/bootstrap credentials.
- [ ] Keep development integrations in provider test/sandbox mode where available. Use synthetic or anonymized test data only. Do not copy production student/guardian data into dev without a documented, approved sanitization process.

## Ordered implementation checklist

### 1. Make configuration production-safe

- [x] Add environment parsing for Django `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and HTTPS/proxy security settings.
- [x] Fail closed for unsafe secret keys, debug mode, hosts, origins, and public URLs in deployed environments.
- [x] Make the school frontend and platform admin API base URLs configurable through `VITE_API_BASE_URL`; CI must set the environment-specific value when it builds the static assets.
- [ ] Confirm JWT/cookie domain and same-site behavior for the selected hostname layout; retain HTTP-only and Secure cookies, exact CORS origins, CSRF trusted origins, and HSTS only after HTTPS is verified.
- [ ] Review all settings read by `sms-backend/core/settings.py` and services, including PostgreSQL, Redis/Celery, `MIGRATION_FILE_STORAGE`, R2, Cloudinary, SES, Arkesel, Paystack, messaging policies, and signed-link TTLs. Maintain a non-secret variable inventory in `.env.example`.
- [ ] Ensure secrets are never placed in images, build args, GitHub logs, checked-in env files, or frontend variables. Rotate any credential that has ever been committed or exposed; never copy production secrets into dev.

### 2. Build production images and Compose topology

- [ ] Preserve root `compose.yml` as the local developer workflow.
- [x] Add production backend image with pinned dependencies, Gunicorn, static collection, non-root runtime, and no source bind mounts. Migrations are an explicit one-off service.
- [x] Document host Caddy `file_server` routes for both SPA frontends and reverse-proxy routes for each API hostname.
- [x] Add separate dev/prod Compose project definitions with PostgreSQL, Redis, one worker, and one beat per environment, health checks, restart policies, and dependency health conditions.
- [x] Keep PostgreSQL and Redis private; bind app ports to localhost for host Caddy.
- [x] Use separate named data volumes and immutable commit-SHA backend image tags. Successful deployments receive environment-prefixed GHCR tags for four-version-per-environment retention.
- [x] Add `.dockerignore` files to exclude env files, Git metadata, media, and build caches.
- [x] Use the already-installed host Caddy with the configured dev and production hostnames and certificate checks.

### 3. CI, security gates, and image publishing

- [x] On pull requests: backend dependency install, Django tests and migration checks; school frontend lint/typecheck/build; platform admin typecheck/build; production backend image build.
- [x] Pin workflow actions to reviewed commit SHAs, set minimum `contents: read` permissions, and avoid deployment credentials in CI.
- [ ] Add Compose/config validation, secret scanning, and dependency vulnerability scanning.
- [ ] Add CodeQL or equivalent source analysis, Dependabot/Renovate updates, container scanning (e.g. Trivy), and secret scanning/push protection in repository settings.
- [x] Publish the backend image to GHCR only after CI passes on `dev` or `main`, tag it with the full commit SHA, and deploy that exact tag. Build both frontends with the environment's API URL and upload static releases for Caddy to serve.
- [x] Retain the current and three previous frontend releases per environment; preserve only backend images in use on the VPS; retain four successful GHCR image versions per environment. Grant workflow Admin access to the GHCR package before registry deletion can take effect.
- [x] `main` ruleset requires a PR, the four CI checks plus the source-branch policy check, blocks force pushes/deletion, and does not allow bypass. See [github-branch-protection.md](./github-branch-protection.md).
- [x] Protect `main` with the configured PR/CI rules and serialize dev/production deployments through one shared lock because they use the same VPS.
- [ ] Keep deployment credentials unavailable to fork PRs and general CI. Prefer a constrained SSH deploy key/user or a pull-only registry credential on the host; restrict it to the required repository and paths. Do not expose the Docker socket to untrusted jobs.

### 4. Provision Hetzner hosts and network

- [ ] Choose region, VPS size, storage, and whether to use one or two servers based on expected users, database size, file volume, and recovery targets.
- [ ] Create non-root operator/deploy users; SSH keys only, disable password login and root SSH, apply security updates, configure time sync, and document emergency console/recovery access.
- [ ] Configure Hetzner Cloud Firewall and host firewall: allow inbound 80/443 and restricted SSH only; deny public access to PostgreSQL, Redis, and app ports. Restrict egress if operationally practical.
- [ ] Configure DNS A/AAAA records and HTTPS for school app, platform admin, and API. Validate webhook routes and provider callback URLs after DNS is live.
- [ ] Set log rotation and disk/volume alerts. Monitor available disk, memory, CPU, container restarts, HTTP health, PostgreSQL capacity, certificate expiry, and backup age.

### 5. Secrets, providers, and credential rotation

- [ ] Generate a unique high-entropy Django `SECRET_KEY` per environment. Store actual credentials in `~/school-management-system/dev/.env.dev` and `~/school-management-system/prod/.env.prod` on the VPS, with restrictive file permissions; keep deploy credentials in GitHub secrets.
- [ ] Create distinct, least-privilege R2 credentials and private buckets for reports/receipts and migration files; set `MIGRATION_FILE_STORAGE=r2`. Decide the retention and cleanup policy for failed imports and locally staged bulk-import artifacts.
- [ ] Configure Cloudinary credentials/folders separately; verify upload preset security, signed/unsigned behavior, and access controls.
- [ ] Verify SES sending domain, production access, sender identity, configuration set and SNS event subscription. Test invite, OTP/email fallback, guardian message, bounce/complaint handling, and suppression behavior.
- [ ] Configure Arkesel production SMS sender/key and delivery-status webhook. Test login OTP, signup OTP (still noted as DEBUG-only in docs; verify current implementation), batch messaging, and failure/retry behavior.
- [ ] Configure Paystack test and live keys separately, webhook URL/signature verification, idempotency, and reconciliation. Keep SaaS billing credentials distinct from any school fee provider credentials.
- [ ] Maintain a credential register: owner, environment, purpose, creation/expiry date, rotation interval, revocation procedure, and last rotation. Rotate immediately on staff/offboarding or suspected exposure; stage replacement, verify, then revoke old keys.

### 6. Database migrations and release safety

- [ ] Run Django `check --deploy`, `makemigrations --check --dry-run`, and migration plan checks against the production settings before release.
- [ ] Back up production before every schema migration; test migrations against a restored copy and classify whether each migration is backward compatible.
- [ ] Release sequence: pull immutable images → verify image/config → take backup → run one-off migration job → deploy/recreate app and worker → wait for health checks → smoke test → observe → mark release complete.
- [ ] Never automatically roll back a database schema/data migration with an old image. Document forward-fix and point-in-time recovery procedures.
- [ ] Keep one Celery beat instance only. Check task idempotency/retries, dead-letter/failure visibility, and scheduled timezone semantics; cron currently runs in UTC.

### 7. Backups and disaster recovery

- [ ] Schedule encrypted PostgreSQL logical backups (e.g. `pg_dump`), with a retention policy and off-host/off-provider destination. Hetzner server backups/snapshots are useful for host recovery but are not the database backup strategy by themselves.
- [ ] Define RPO/RTO, retention (daily/weekly/monthly), encryption key custody, access controls, and alerting for backup failure or stale backups.
- [ ] Back up any persistent private import artifacts if required; separately document Cloudinary/R2 retention, versioning/lifecycle, and recovery.
- [ ] Test a full restore to an isolated environment on a schedule. Verify restored database, media/document links, application login, and a sample school workflow; record duration and gaps.
- [ ] Document incident contacts, Hetzner console recovery, DNS failover/manual cutover, secret revocation, restore commands, and post-restore checks.

### 8. Staging acceptance and production launch

- [ ] Deploy a staging stack with independent secrets/providers/storage and no production school data.
- [ ] Follow the 13 Nov deployment note's end-to-end scenario: migrate schema, seed billing plans, create platform admin, keep public signup disabled, create school, accept invite, finish setup, add student, record payment, generate a report, deliver an email/SMS, and process a Paystack test webhook.
- [ ] Verify tenant isolation, role access, CORS/CSRF, secure cookies, webhook authentication, error pages, log redaction, browser/API health, Celery scheduled tasks, and private signed-file access.
- [ ] Test backup and restore, failed deployment recovery, image rollback, and secret rotation before production contains live school data.
- [ ] Launch production with public signup disabled unless intentionally enabled, create the first platform administrator securely, verify DNS/TLS and provider callbacks, and use a monitored low-risk school onboarding before broad rollout.
- [ ] Establish post-launch monitoring, incident response, patch cadence, provider balance/quota alerts, audit-log retention, and a regular access review.

## Suggested work sequence

1. **Configuration and security baseline** — externalize and validate settings, define environment URL/secret inventory, confirm domain names and the one-VPS/two-VPS choice.
2. **Container separation** — retain local Compose; add production images and isolated dev/prod Compose deployments.
3. **CI and image registry** — make PR checks reliable, scan, publish immutable images.
4. **Dev/staging on Hetzner** — provision host, DNS/TLS, private services, dev credentials, deployment workflow.
5. **Backups and recovery** — implement and restore-test before production.
6. **Production release path** — production environment secrets/approval, least-privilege deploy access, migration/release/rollback runbook.
7. **Provider acceptance and launch** — SES, Arkesel, Paystack, R2, end-to-end school, monitoring.

## Repository touchpoints

| Work | Likely files/locations |
| --- | --- |
| Runtime settings | `sms-backend/core/settings.py`, `.env.example` |
| Backend image | `sms-backend/Dockerfile`, `sms-backend/requirements.txt`, `sms-backend/.dockerignore` |
| School frontend build | `sms-frontend/src/app/api/api.ts`, Vite config, CI artifact build |
| Platform frontend build | `platform-admin/src/lib/api.ts`, Vite config, CI artifact build |
| Local and server topology | `compose.yml`, `compose.deploy.yml`, `compose.dev.yml`, `compose.prod.yml`, `deploy/Caddyfile.example` |
| CI and deploy | `.github/workflows/`, GitHub `development` / `production` Environments |
| Operations | `docs/` runbooks for provisioning, deployment, backup/restore, incident response, rotation |

## References

- [GitHub deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [GitHub deployment controls and concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
- [Docker Compose in production](https://docs.docker.com/compose/how-tos/production/)
- [Hetzner Cloud backup FAQ](https://docs.hetzner.com/cloud/servers/backups-snapshots/faq/)
