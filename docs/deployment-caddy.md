# Caddy and frontend deployment layout

The VPS already runs Caddy as a host service. Keep it as the only public web server: it serves the two Vite single-page apps from disk and proxies the API hostnames to the backend containers. There are no production frontend containers or Nginx dependency.

## Request routing

| Environment | Hostname role | Caddy target |
| --- | --- | --- |
| Dev | School app | `/home/kris/school-management-system/dev/school/current` |
| Dev | Platform admin | `/home/kris/school-management-system/dev/platform-admin/current` |
| Dev | API | `127.0.0.1:18100` |
| Production | School app | `/home/kris/school-management-system/prod/school/current` |
| Production | Platform admin | `/home/kris/school-management-system/prod/platform-admin/current` |
| Production | API | `127.0.0.1:18200` |

The hostnames in [`../deploy/Caddyfile.example`](../deploy/Caddyfile.example) are examples and must be replaced with the real domains. Merge the site blocks into the VPS's existing Caddyfile; preserve any other sites already hosted there.

Production app, admin, and API responses start with an HSTS `max-age` of one hour. This lets browsers learn the HTTPS policy while keeping the first rollout easy to reverse. After confirming all production hosts serve HTTPS reliably, increase the value to `31536000` (one year). Keep `includeSubDomains` and `preload` disabled until every subdomain is known to support HTTPS.

## Frontend release model

GitHub Actions will build each frontend with its environment's public `VITE_API_BASE_URL`. For a commit SHA, it will upload `dist/` into a new release directory, for example:

```text
/home/kris/school-management-system/dev/school/releases/<commit-sha>/
/home/kris/school-management-system/dev/platform-admin/releases/<commit-sha>/
```

After upload completes, the deployment script will atomically switch each `current` symlink to that release. Caddy continues serving files from `current`; rollback means switching the symlink to a previous release. Keep the Caddy user able to traverse the release parent directories and read the static files, but do not make the directory writable by Caddy.

After a successful deployment, the workflow keeps the active release and the three most recent previous releases for each frontend and environment. Older frontend release directories are removed only after the backend is healthy and both frontend symlinks have switched.

The backend alone is packaged as a private GHCR image with both an immutable commit-SHA tag (used by Compose) and an environment-prefixed tag (`dev-<sha>` or `prod-<sha>`) used for registry retention. The GHCR cleanup retains the four most recent versions for each environment. Pre-retention SHA-only versions are left untouched because their environment cannot be safely inferred. The VPS removes unused tags from this application's backend image repository only; it preserves image IDs used by any containers and does not prune other projects' images. GHCR remains the source for rolling back to earlier image versions.

GHCR version deletion requires the repository's GitHub Actions workflow to have **Admin** access to the package. Configure that in the package's **Package settings → Manage Actions access**. The cleanup step is non-blocking, so a missing permission will be reported in the workflow without failing an otherwise successful deployment.

The API is published to the host only on loopback; Postgres and Redis have no published host ports. Dev and production Compose project names keep their volumes separate.

## GitHub Actions setup required before the first deployment

The reusable workflow in `.github/workflows/deploy.yml` is called by `.github/workflows/ci.yml`. It only runs on pushes to `dev` or `main`, after backend, frontend, and backend-image checks pass. A shared concurrency lock serializes both stages on this one VPS. A successful dev deployment has been verified. The first production deployment has not been run yet. On deployment, the workflow publishes the backend image to GHCR, builds the frontends with the environment's API URL, uploads static releases, runs migrations, waits for service health, and switches the Caddy `current` symlinks.

Create GitHub Environments named `development` and `production`, and restrict each to its matching branch (`dev` or `main`). Add these secrets to each environment:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | VPS hostname or IP |
| `DEPLOY_USER` | SSH deployment user |
| `DEPLOY_SSH_KEY` | Private SSH key for that user |
| `DEPLOY_KNOWN_HOSTS` | Verified SSH host-key line for the VPS |

Add the environment variable `VITE_API_BASE_URL` to both environments, set to that environment's public API URL ending in `/api/v1`.

On the VPS, use `~/school-management-system/dev` and `~/school-management-system/prod`, put `.env.dev` and `.env.prod` in their matching directories, and ensure the SSH user can write those directories and run Docker Compose. Log that user into the private GHCR package with a read-only package token so it can pull the image. Merge the routes from [`../deploy/Caddyfile.example`](../deploy/Caddyfile.example) into the host's existing Caddyfile, preserving other sites. The workflow runs migrations automatically and takes a production database backup before migration. See [`deployment-operations.md`](deployment-operations.md) for the current setup and retention details.
