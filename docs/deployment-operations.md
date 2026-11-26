# Deployment operations

This document records the deployment setup and the operational choices made for SchoolAssist. Secrets and credential values belong only in the VPS environment files or GitHub Environment secrets; never add their values here.

## Current deployment state

- Dev is deployed and available at `https://dev.schoolassistgh.com`; its school, platform-admin, and API hosts are `dev.schoolassistgh.com`, `dev-admin.schoolassistgh.com`, and `dev-api.schoolassistgh.com`.
- Production is prepared but has not had its first deployment. Its school, platform-admin, and API hosts are `app.schoolassistgh.com`, `admin.schoolassistgh.com`, and `api.schoolassistgh.com`.
- Both stacks run on the existing Hetzner VPS under `/home/kris/school-management-system/{dev,prod}`. Host Caddy serves the static frontends and proxies API requests to loopback ports `18100` (dev) and `18200` (production).
- The VPS keeps `.env.dev` and `.env.prod` in the matching stage directory. Production has `EMAIL_ENABLED=false` while the SES account remains in the sandbox.

## CI and deployment flow

- Pull requests into `dev` or `main` run CI checks. Pull requests do not deploy.
- Pull requests into `main` must come from the repository's `dev` branch. Direct pushes to `main` are blocked by the GitHub ruleset.
- A push to `dev` or `main` deploys only after the backend, frontend, and image-build checks pass. The reusable deployment workflow selects the development or production GitHub Environment from the branch.
- Deployments share one GitHub concurrency group because both stages use the same VPS. This prevents dev and production deploys or image cleanup from racing each other.
- The workflow builds and publishes the backend image to GHCR using its full commit SHA. Compose deploys that immutable SHA tag. After a successful deployment, the workflow adds a `dev-<sha>` or `prod-<sha>` tag and runs registry retention.
- Frontend build output is uploaded to a new SHA-named release directory. After the backend passes health checks, Caddy's `current` symlinks switch atomically to the new frontend releases.
- A production deployment starts PostgreSQL, runs the configured R2 database backup, applies migrations, starts the services, waits for health, switches the frontends, then performs cleanup.

## Retention and rollback

- Frontend files: keep the active release plus the three most recent previous releases for each frontend in each environment. Older directories are removed only after deployment and both frontend switches succeed.
- VPS backend images: remove unused tags from the SchoolAssist backend image repository after successful deployment. Any image ID used by a container is retained, including the active dev and production images. Cleanup is scoped to this repository and never prunes images for other VPS projects.
- GHCR backend images: retain the four most recent successful deployment versions for `dev` and the four most recent for `prod`. The SHA tag remains the deploy reference; the stage-prefixed tag lets the cleanup script distinguish environment history. GHCR versions published before stage-prefixed tags existed are left untouched because their environment cannot be inferred safely.
- GHCR deletion uses the workflow's `GITHUB_TOKEN`. In the package settings, grant this repository's GitHub Actions workflow **Admin** access under **Manage Actions access**. Registry cleanup is non-blocking: a permission failure is shown in the workflow log but does not invalidate a deployment that already succeeded.
- Rollback images are retained in GHCR and can be pulled again; the VPS is not used as the historical image archive. Database schema changes still require a forward-fix or restore plan rather than an automatic old-image rollback.

## Email and current blockers

- The `schoolassistgh.com` SES domain identity is verified in `eu-north-1`, and DKIM is successful. Dev tests succeeded for both the internal sender (`noreply@team.schoolassistgh.com`) and guardian sender (`noreply@notify.schoolassistgh.com`) using a verified recipient.
- SES production access is awaiting a response on the AWS Support case. Until approval, sandbox recipient verification applies; production email stays disabled.
- Before broad production launch, complete the production backup restore drill, end-to-end school acceptance flow, and the remaining security/operations checks in the [deployment readiness checklist](deployment-readiness-checklist.md).

## Related files

- Deployment workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)
- Deployment Compose: [`compose.deploy.yml`](../compose.deploy.yml), [`compose.dev.yml`](../compose.dev.yml), and [`compose.prod.yml`](../compose.prod.yml)
- Frontend and Caddy routing: [`deployment-caddy.md`](deployment-caddy.md)
- GHCR retention helper: [`deploy/cleanup-ghcr-versions.py`](../deploy/cleanup-ghcr-versions.py)
- Production database backup: [`deploy/backup-prod-postgres-r2.sh`](../deploy/backup-prod-postgres-r2.sh)
