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

The backend alone is packaged as a private GHCR image tagged with the commit SHA. The API is published to the host only on loopback; Postgres and Redis have no published host ports. Dev and production Compose project names keep their volumes separate.

## GitHub Actions setup required before the first deployment

The reusable workflow in `.github/workflows/deploy.yml` is connected to `.github/workflows/ci.yml` on the local `dev` branch. It only runs on pushes to `dev` or `main`, after the backend, both frontend, and backend-image jobs pass. Once these changes are merged to `dev`, it will publish the backend image to GHCR, build the frontends with the environment's API URL, upload static releases, run migrations, and switch the Caddy `current` symlinks.

Create GitHub Environments named `development` and `production`, and restrict each to its matching branch (`dev` or `main`). Add these secrets to each environment:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | VPS hostname or IP |
| `DEPLOY_USER` | SSH deployment user |
| `DEPLOY_SSH_KEY` | Private SSH key for that user |
| `DEPLOY_KNOWN_HOSTS` | Verified SSH host-key line for the VPS |

Add the environment variable `VITE_API_BASE_URL` to both environments, set to that environment's public API URL ending in `/api/v1`.

On the VPS, use `~/school-management-system/dev` and `~/school-management-system/prod`, put `.env.dev` and `.env.prod` in their matching directories, and ensure the SSH user can write those directories and run Docker Compose. Log that user into the private GHCR package with a read-only package token so it can pull the image. Merge the routes from [`../deploy/Caddyfile.example`](../deploy/Caddyfile.example) into the host's existing Caddyfile, preserving other sites. The workflow runs migrations automatically; finish and verify the production backup/restore setup before enabling production deployments.
