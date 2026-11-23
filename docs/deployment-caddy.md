# Caddy and frontend deployment layout

The VPS already runs Caddy as a host service. Keep it as the only public web server: it serves the two Vite single-page apps from disk and proxies the API hostnames to the backend containers. There are no production frontend containers or Nginx dependency.

## Request routing

| Environment | Hostname role | Caddy target |
| --- | --- | --- |
| Dev | School app | `/srv/school-management-system/dev/school/current` |
| Dev | Platform admin | `/srv/school-management-system/dev/platform-admin/current` |
| Dev | API | `127.0.0.1:18100` |
| Production | School app | `/srv/school-management-system/prod/school/current` |
| Production | Platform admin | `/srv/school-management-system/prod/platform-admin/current` |
| Production | API | `127.0.0.1:18200` |

The hostnames in [`../deploy/Caddyfile.example`](../deploy/Caddyfile.example) are examples and must be replaced with the real domains. Merge the site blocks into the VPS's existing Caddyfile; preserve any other sites already hosted there.

## Frontend release model

GitHub Actions will build each frontend with its environment's public `VITE_API_BASE_URL`. For a commit SHA, it will upload `dist/` into a new release directory, for example:

```text
/srv/school-management-system/dev/school/releases/<commit-sha>/
/srv/school-management-system/dev/platform-admin/releases/<commit-sha>/
```

After upload completes, the deployment script will atomically switch each `current` symlink to that release. Caddy continues serving files from `current`; rollback means switching the symlink to a previous release. Keep the Caddy user able to traverse the release parent directories and read the static files, but do not make the directory writable by Caddy.

The backend alone is packaged as a private GHCR image tagged with the commit SHA. The API is published to the host only on loopback; Postgres and Redis have no published host ports. Dev and production Compose project names keep their volumes separate.

This file describes the target layout. The CI/CD workflow, real domains, VPS paths, permissions, and live Caddyfile changes are still pending.
