"""Data.gov MCP Server - Read-only access to the CKAN API at catalog.data.gov."""

from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://catalog.data.gov/api/3/action"
USER_AGENT = "data-gov-mcp-server/1.0"
TIMEOUT = 30.0

mcp = FastMCP(
    "data-gov",
    instructions=(
        "A read-only MCP server for searching and exploring U.S. government open data "
        "on catalog.data.gov (powered by CKAN). Use package_search as the primary "
        "discovery tool, then package_show for full dataset details."
    ),
)


async def _ckan_request(action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call a CKAN API action via POST with JSON body and return the result."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.post(
            f"{BASE_URL}/{action}",
            json={k: v for k, v in (params or {}).items() if v is not None},
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"CKAN API error: {body.get('error', body)}")
        return body["result"]


# ---------------------------------------------------------------------------
# Dataset / Package tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def package_search(
    query: str = "",
    filter_query: str | None = None,
    sort: str | None = None,
    rows: int = 10,
    start: int = 0,
    facet_field: str | None = None,
) -> dict[str, Any]:
    """Search datasets on data.gov using Solr query syntax.

    This is the primary discovery tool. Supports full-text search, field-specific
    queries, faceting, and sorting.

    Args:
        query: Search query string (Solr syntax). Examples: "climate", "title:water",
               "organization:epa-gov", "tags:health". Empty string returns all datasets.
        filter_query: Filter query to apply (e.g., "organization:nasa-gov",
                      "res_format:CSV", "license_id:cc-by").
        sort: Sorting of results (e.g., "score desc", "metadata_modified desc",
              "name asc"). Default is relevance.
        rows: Number of results to return (max 1000, default 10).
        start: Offset for pagination (default 0).
        facet_field: Comma-separated facet fields (e.g., "organization,tags,res_format").
    """
    params: dict[str, Any] = {"q": query, "rows": rows, "start": start}
    if filter_query:
        params["fq"] = filter_query
    if sort:
        params["sort"] = sort
    if facet_field:
        params["facet"] = "true"
        params["facet.field"] = f'["{facet_field}"]' if "," not in facet_field else f'[{",".join(f"{f.strip()!r}" for f in facet_field.split(","))}]'
    result = await _ckan_request("package_search", params)
    # Summarize to keep response manageable
    datasets = []
    for pkg in result.get("results", []):
        datasets.append({
            "name": pkg.get("name"),
            "title": pkg.get("title"),
            "id": pkg.get("id"),
            "organization": (pkg.get("organization") or {}).get("title"),
            "notes": (pkg.get("notes") or "")[:300],
            "metadata_modified": pkg.get("metadata_modified"),
            "num_resources": pkg.get("num_resources"),
            "tags": [t["name"] for t in pkg.get("tags", [])],
            "license_title": pkg.get("license_title"),
            "formats": list({r.get("format", "").upper() for r in pkg.get("resources", []) if r.get("format")}),
        })
    return {
        "count": result.get("count"),
        "datasets": datasets,
        "facets": result.get("search_facets", {}),
    }


@mcp.tool()
async def package_show(id: str) -> dict[str, Any]:
    """Get full metadata and resources for a single dataset.

    Args:
        id: The dataset name (slug) or ID. Example: "supply-chain-greenhouse-gas-emission-factors-v1-3-by-naics-6"
    """
    pkg = await _ckan_request("package_show", {"id": id})
    resources = []
    for r in pkg.get("resources", []):
        resources.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "description": (r.get("description") or "")[:200],
            "format": r.get("format"),
            "url": r.get("url"),
            "size": r.get("size"),
            "created": r.get("created"),
            "last_modified": r.get("last_modified"),
        })
    return {
        "name": pkg.get("name"),
        "title": pkg.get("title"),
        "id": pkg.get("id"),
        "notes": pkg.get("notes"),
        "organization": (pkg.get("organization") or {}).get("title"),
        "maintainer": pkg.get("maintainer"),
        "maintainer_email": pkg.get("maintainer_email"),
        "metadata_created": pkg.get("metadata_created"),
        "metadata_modified": pkg.get("metadata_modified"),
        "license_title": pkg.get("license_title"),
        "tags": [t["name"] for t in pkg.get("tags", [])],
        "num_resources": pkg.get("num_resources"),
        "resources": resources,
        "extras": {e["key"]: e["value"] for e in pkg.get("extras", [])},
    }


@mcp.tool()
async def package_list(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """List dataset names available on data.gov.

    Args:
        limit: Max number of names to return (default 50).
        offset: Offset for pagination.
    """
    result = await _ckan_request("package_list", {"limit": limit, "offset": offset})
    return {"datasets": result, "count": len(result)}


@mcp.tool()
async def package_autocomplete(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Autocomplete dataset names matching a partial string.

    Args:
        query: Partial dataset name to match.
        limit: Max results (default 10).
    """
    return await _ckan_request("package_autocomplete", {"q": query, "limit": limit})


# ---------------------------------------------------------------------------
# Resource tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def resource_show(id: str) -> dict[str, Any]:
    """Get metadata for a specific resource (file/API endpoint within a dataset).

    Args:
        id: The resource ID (UUID).
    """
    return await _ckan_request("resource_show", {"id": id})


@mcp.tool()
async def resource_search(
    query: str,
    order_by: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Search resources across all public datasets.

    Args:
        query: Search query in field:term format. Examples: "format:CSV",
               "name:budget", "description:population".
        order_by: Field to sort by (e.g., "name").
        limit: Max results (default 20).
        offset: Offset for pagination.
    """
    params: dict[str, Any] = {"query": query, "limit": limit, "offset": offset}
    if order_by:
        params["order_by"] = order_by
    return await _ckan_request("resource_search", params)


# ---------------------------------------------------------------------------
# Organization tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def organization_list(
    sort: str | None = None,
    limit: int = 50,
    offset: int = 0,
    all_fields: bool = False,
) -> Any:
    """List organizations (federal agencies) on data.gov.

    Args:
        sort: Sort field (e.g., "name asc", "package_count desc").
        limit: Max results (default 50).
        offset: Offset for pagination.
        all_fields: If True, return full org details instead of just names.
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if all_fields:
        params["all_fields"] = True
    if sort:
        params["sort"] = sort
    return await _ckan_request("organization_list", params)


@mcp.tool()
async def organization_show(
    id: str,
    include_datasets: bool = False,
    include_dataset_count: bool = True,
) -> dict[str, Any]:
    """Get details of a specific organization (federal agency).

    Args:
        id: Organization name (slug) or ID. Example: "nasa-gov", "epa-gov".
        include_datasets: Include the org's datasets in response.
        include_dataset_count: Include dataset count (default True).
    """
    params: dict[str, Any] = {"id": id}
    if include_datasets:
        params["include_datasets"] = True
    if include_dataset_count:
        params["include_dataset_count"] = True
    return await _ckan_request("organization_show", params)


@mcp.tool()
async def organization_autocomplete(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Autocomplete organization names matching a partial string.

    Args:
        query: Partial organization name.
        limit: Max results (default 10).
    """
    return await _ckan_request("organization_autocomplete", {"q": query, "limit": limit})


# ---------------------------------------------------------------------------
# Group tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def group_list(
    sort: str | None = None,
    limit: int = 50,
    offset: int = 0,
    all_fields: bool = False,
) -> Any:
    """List topic groups on data.gov.

    Args:
        sort: Sort field (e.g., "name asc", "package_count desc").
        limit: Max results (default 50).
        offset: Offset for pagination.
        all_fields: If True, return full group details instead of just names.
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if all_fields:
        params["all_fields"] = True
    if sort:
        params["sort"] = sort
    return await _ckan_request("group_list", params)


@mcp.tool()
async def group_show(
    id: str,
    include_datasets: bool = False,
    include_dataset_count: bool = True,
) -> dict[str, Any]:
    """Get details of a specific topic group.

    Args:
        id: Group name (slug) or ID.
        include_datasets: Include the group's datasets in response.
        include_dataset_count: Include dataset count (default True).
    """
    params: dict[str, Any] = {"id": id}
    if include_datasets:
        params["include_datasets"] = True
    if include_dataset_count:
        params["include_dataset_count"] = True
    return await _ckan_request("group_show", params)


# ---------------------------------------------------------------------------
# Tag tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tag_search(query: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """Search tags by name substring.

    Args:
        query: Tag name substring to search for.
        limit: Max results (default 20).
        offset: Offset for pagination.
    """
    return await _ckan_request("tag_search", {"query": query, "limit": limit, "offset": offset})


@mcp.tool()
async def tag_list(query: str | None = None, all_fields: bool = False) -> Any:
    """List all tags, optionally filtered by name.

    Args:
        query: Optional filter string for tag names.
        all_fields: If True, return full tag objects instead of just names.
    """
    params: dict[str, Any] = {}
    if all_fields:
        params["all_fields"] = True
    if query:
        params["query"] = query
    return await _ckan_request("tag_list", params)


# ---------------------------------------------------------------------------
# Recent datasets
# ---------------------------------------------------------------------------


@mcp.tool()
async def recently_modified_datasets(limit: int = 10, offset: int = 0) -> dict[str, Any]:
    """Get datasets sorted by most recently modified.

    Args:
        limit: Max results (default 10).
        offset: Offset for pagination.
    """
    return await package_search(
        query="*:*",
        sort="metadata_modified desc",
        rows=limit,
        start=offset,
    )


# ---------------------------------------------------------------------------
# Misc tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def license_list() -> list[dict[str, Any]]:
    """List all available dataset licenses on data.gov."""
    return await _ckan_request("license_list")


@mcp.tool()
async def status_show() -> dict[str, Any]:
    """Get data.gov site status, version, and installed extensions."""
    return await _ckan_request("status_show")


if __name__ == "__main__":
    mcp.run()
