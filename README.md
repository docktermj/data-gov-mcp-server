# data-gov-mcp-server

A read-only MCP (Model Context Protocol) server for searching and exploring
U.S. government open data on [catalog.data.gov](https://catalog.data.gov),
powered by the [CKAN API](https://docs.ckan.org/en/2.11/api/index.html).

## Tools

| Tool | Description |
|------|-------------|
| `package_search` | Search datasets (Solr query syntax, faceting, filtering) |
| `package_show` | Get full metadata and resources for a dataset |
| `package_list` | List dataset names |
| `package_autocomplete` | Autocomplete dataset names |
| `resource_show` | Get metadata for a specific resource |
| `resource_search` | Search resources across datasets |
| `organization_list` | List federal agencies |
| `organization_show` | Get details of an agency |
| `organization_autocomplete` | Autocomplete organization names |
| `group_list` | List topic groups |
| `group_show` | Get details of a topic group |
| `tag_search` | Search tags by name |
| `tag_list` | List all tags |
| `recently_modified_datasets` | Get recently modified datasets |
| `license_list` | List available licenses |
| `status_show` | Get site status and version |

## Usage

### With Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "data-gov": {
      "command": "python3",
      "args": ["/path/to/data-gov-mcp-server/server.py"]
    }
  }
}
```

### With Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "data-gov": {
      "command": "python3",
      "args": ["/path/to/data-gov-mcp-server/server.py"]
    }
  }
}
```

### Standalone

```bash
python3 server.py
```

## Dependencies

- Python 3.11+
- `mcp` >= 1.0.0
- `httpx` >= 0.27.0

Install with:

```bash
pip install mcp httpx
```

## API Reference

- [data.gov](https://data.gov)
- [catalog.data.gov datasets](https://catalog.data.gov/dataset/)
- [CKAN API docs](https://docs.ckan.org/en/2.11/api/index.html)
- Base URL: `https://catalog.data.gov/api/3`
