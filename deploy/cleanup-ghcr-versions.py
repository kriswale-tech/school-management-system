#!/usr/bin/env python3
"""Keep the latest four GHCR backend image versions for dev and prod."""

from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


API = "https://api.github.com"
PACKAGE = "school-management-system-backend"
RETAIN_PER_ENVIRONMENT = 4
STAGES = ("dev", "prod")


def request_json(url: str, *, method: str = "GET") -> tuple[object, str]:
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GH_TOKEN is not set")

    request = Request(
        url,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            parsed = json.loads(body) if body else None
            return parsed, response.headers.get("Link", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"GitHub API {method} failed ({exc.code}) for {url}: {detail}"
        ) from exc


def list_versions(endpoint: str) -> list[dict]:
    versions: list[dict] = []
    url = f"{endpoint}?per_page=100"
    while url:
        page, link_header = request_json(url)
        if not isinstance(page, list):
            raise RuntimeError("GitHub returned an unexpected package-version response")
        versions.extend(item for item in page if isinstance(item, dict))
        next_link = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        url = next_link.group(1) if next_link else ""
    return versions


def tags_for(version: dict) -> set[str]:
    metadata = version.get("metadata") or {}
    container = metadata.get("container") or {}
    tags = container.get("tags") or []
    return {tag for tag in tags if isinstance(tag, str)}


def main() -> int:
    owner = os.environ.get("GITHUB_REPOSITORY", "").split("/", 1)[0].strip()
    if not owner:
        raise RuntimeError("GITHUB_REPOSITORY is not set")

    owner_info, _ = request_json(f"{API}/users/{quote(owner, safe='')}")
    owner_route = "orgs" if isinstance(owner_info, dict) and owner_info.get("type") == "Organization" else "users"
    endpoint = (
        f"{API}/{owner_route}/{quote(owner, safe='')}/packages/container/"
        f"{quote(PACKAGE, safe='')}/versions"
    )
    versions = list_versions(endpoint)

    ordered: dict[str, list[dict]] = {}
    for stage in STAGES:
        prefix = f"{stage}-"
        stage_versions = [
            version
            for version in versions
            if any(tag.startswith(prefix) for tag in tags_for(version))
        ]
        ordered[stage] = sorted(
            stage_versions,
            key=lambda version: str(version.get("created_at") or ""),
            reverse=True,
        )

    keep_ids = {
        version.get("id")
        for stage_versions in ordered.values()
        for version in stage_versions[:RETAIN_PER_ENVIRONMENT]
    }

    tagged_versions = [
        version
        for version in versions
        if any(
            tag.startswith(f"{stage}-")
            for stage in STAGES
            for tag in tags_for(version)
        )
    ]
    legacy_count = len(versions) - len(tagged_versions)
    deleted = 0

    for version in tagged_versions:
        version_id = version.get("id")
        if version_id in keep_ids:
            continue
        tags = sorted(tags_for(version))
        request_json(f"{endpoint}/{version_id}", method="DELETE")
        deleted += 1
        print(f"Deleted old GHCR image version {version_id} with tags: {', '.join(tags)}")

    counts = ", ".join(f"{stage}={len(ordered[stage])}" for stage in STAGES)
    print(
        f"GHCR retention complete: kept up to {RETAIN_PER_ENVIRONMENT} versions per "
        f"environment ({counts}); deleted {deleted}; left {legacy_count} pre-retention "
        "versions without environment tags untouched."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # Keep the deployment workflow's cleanup non-blocking.
        print(f"GHCR image cleanup could not complete: {exc}", file=sys.stderr)
        sys.exit(1)
