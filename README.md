# Semantic Project Brain MCP Server

A high-end Python-based MCP (Model Context Protocol) server that provides a local, semantic memory and code-indexer. It uses `tree-sitter` for AST-based parsing of source code to understand class definitions, method signatures, and structures, rather than naive text chunking. It also acts as a "Long-Term Memory" to help AI assistants bypass context window limits by persisting architectural decisions across sessions.

The server uses [ChromaDB](https://docs.trychroma.com/) for fast, local embedding storage, and stores its data in a `.context_db` folder within your current project directory.

## Prerequisites

You need [uv](https://github.com/astral-sh/uv) installed to run the server without managing virtual environments manually.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Available Tools

The server provides three MCP tools:
1. `index_project(path: str)`: Scans a directory, parses code semantically using AST (Python, Java, PHP, TS, JS, HTML), and indexes it.
2. `search_context(query: str)`: A unified search over AST nodes and past project decisions.
3. `remember_decision(topic: str, context: str)`: Saves manual architectural notes or reasoning (e.g., "Why we chose framework X").

## Usage with AI Assistants

You can use `uvx` (part of `uv`) to run this server directly.

### Claude Desktop Integration

To install and use this MCP server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "semantic-brain": {
      "command": "uvx",
      "args": [
        "--from", "fastmcp",
        "--from", "chromadb",
        "--from", "sentence-transformers",
        "--from", "tree-sitter",
        "--from", "tree-sitter-languages",
        "--from", "beautifulsoup4",
        "--from", "pathspec",
        "python",
        "/path/to/this/project/server.py"
      ]
    }
  }
}
```
*Note: Replace `/path/to/this/project/server.py` with the absolute path to the `server.py` file.*

### Cursor Integration

In Cursor, go to **Settings > Features > MCP** and add a new MCP Server:
- **Name:** Semantic Brain
- **Type:** `command`
- **Command:** `uvx --from fastmcp --from chromadb --from sentence-transformers --from tree-sitter --from tree-sitter-languages --from beautifulsoup4 --from pathspec python /path/to/this/project/server.py`

## Instructions for AI Agents (AGENTS.md)

Copy the following block and paste it into your project's `.cursorrules`, `AGENTS.md`, or `GEMINI.md` to instruct the LLM on how to use this server:

```markdown
# Semantic Project Brain Usage Guidelines

You have access to the `semantic-brain` MCP server. Follow these rules rigorously:

1. **Re-indexing:** 
   - If you make significant structural changes (e.g., creating a new module, renaming classes, or refactoring), you MUST trigger `index_project(path=".")` when you finish to keep the AST index up to date.
   - If you cannot find expected code in `search_context`, trigger an index update first.

2. **Understanding the Codebase:**
   - Use `search_context(query="ClassName")` to understand class hierarchies, locate method definitions, and retrieve precise semantic chunks of code instead of grepping the entire workspace.

3. **Remembering Decisions:**
   - Before completing a task that involved a notable architectural decision, tradeoff, or complex logic, you are OBLIGATED to call `remember_decision(topic="...", context="...")`.
   - Store "Why" something was built a certain way, so you and other agents can retrieve it in future sessions using `search_context`.
```
