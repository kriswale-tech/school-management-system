# Deployment Readiness Checklist

**Target:** One Hetzner VPS, with separate dev and production environments.

This is the working deployment checklist for the repository. The VPS layout is one Hetzner server with separate dev and production Compose projects; the existing host Caddy serves the frontends and proxies API requests. GHCR will hold the private backend image tagged by commit SHA. The project has Django/DRF, two Vite frontends, PostgreSQL, Redis, Celery worker/beat, Cloudinary, R2, Arkesel, Paystack SaaS billing, and Amazon SES.

## Current state and blockers

- [x] Django security and URL settings now come from the environment; deployed environments reject debug mode, wildcard/missing hosts, non-HTTPS origins, missing URLs, and weak/missing secret keys.
- [x] Keep root `compose.yml` for local development; separate `compose.deploy.yml` plus `compose.dev.yml` and `compose.prod.yml` define the server stacks.
- [x] Production backend image uses Gunicorn, a non-root runtime, collected static files, and a health check. Frontends are built as static files for host Caddy; no production frontend images are needed.
- [x] Deployment Compose files use separate project names, volumes, databases, Redis instances, and loopback-only published ports for host Caddy.
- [x] A CI workflow now checks backend tests/migrations, both frontend typechecks/builds (plus school frontend lint), the production backend image build, and the `dev`-only source rule for PRs into `main`.
- [x] GitHub `main` ruleset blocks direct pushes and requires the existing CI checks. The deployment workflow is now connected locally and waits for the CI jobs to pass; merge this change to `dev` before the first deploy.
- [ ] No real `.env.dev` or `.env.prod` values are created yet; create them in `~/school-management-system/dev` and `~/school-management-system/prod` on the VPS only, with restrictive permissions. Both names are gitignored.
- [ ] `MIGRATION_FILE_STORAGE` defaults to local disk. Production should use private R2 storage for migration staging files; bulk-import failure files currently use app-local disk and need an explicit persistence/expiry plan.
- [ ] `.github/workflows/deploy.yml` is connected to CI locally; merge it to `dev` after the VPS registry login and environment setup are ready.
- [ ] `docs/STATUS.md` is older than the November 2026 feature notes. Use code and the recent notes as operational evidence; update the status doc as deployment work lands.
- [ ] Current worktree has a modified `.DS_Store` and untracked `AGENTS.md` / `CLAUDE.md`. Decide whether these are intended repository changes before staging; do not bundle them into a deployment commit by accident.

## Environment separation to establish

- [ ] Create GitHub Environments named `development` and `production`; scope deploy secrets and variables to the matching environment. Restrict dev deploys to `dev` and prod deploys to `main`; gate production where supported.
- [ ] Connect deployment so pushes to `dev` deploy the dev stack and pushes to `main` deploy production after CI passes. PRs must remain CI-only.
- [x] Use one Hetzner VPS with isolated Compose projects, networks, volumes, databases, Redis instances, credentials, and domains. Never point dev at production data or services.
- [x] Use host Caddy as the public HTTPS reverse proxy; app ports bind to localhost and database/Redis ports are not published.
- [x] Keep `.env.dev` and `.env.prod` in their matching per-environment deployment directories under `~/school-management-system/` on the VPS and ignored by Git.
- [ ] Use separate hostnames, for example `dev.school-domain` / `dev-admin.school-domain` / `dev-api.school-domain`, and corresponding production hostnames. Final DNS/domain choices are an implementation input.
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
- [x] Use separate named data volumes and commit-SHA backend image tags; GHCR publishing and rollback workflow remain to be implemented.
- [x] Add `.dockerignore` files to exclude env files, Git metadata, media, and build caches.
- [x] Use the already-installed host Caddy; exact hostname routing and certificate checks await the DNS/domain decisions and VPS setup.

### 3. CI, security gates, and image publishing

- [x] On pull requests: backend dependency install, Django tests and migration checks; school frontend lint/typecheck/build; platform admin typecheck/build; production backend image build.
- [x] Pin workflow actions to reviewed commit SHAs, set minimum `contents: read` permissions, and avoid deployment credentials in CI.
- [ ] Add Compose/config validation, secret scanning, and dependency vulnerability scanning.
- [ ] Add CodeQL or equivalent source analysis, Dependabot/Renovate updates, container scanning (e.g. Trivy), and secret scanning/push protection in repository settings.
- [ ] Publish the backend image to GHCR only after CI passes on `dev` or `main`, tag it with the full commit SHA, and deploy that exact tag. Build both frontends with the environment's API URL and upload static releases for Caddy to serve.
- [x] `main` ruleset requires a PR, the four CI checks plus the source-branch policy check, blocks force pushes/deletion, and does not allow bypass. See [github-branch-protection.md](./github-branch-protection.md).
- [ ] Protect `main`, require passing checks and review, and use concurrency locks so simultaneous deployments cannot race for the same environment.
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
