# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-03-28

### Changed
- Switched to `tree-sitter-language-pack` for more robust and comprehensive language support (including PHP).
- Made the `path` argument optional in `index_project` (defaults to current directory).
- Improved `DEFAULT_EXCLUDES` to be even smarter and faster.

## [0.2.0] - 2026-03-28

### Changed
- Converted naive Context Memory into a "Semantic Project Brain".
- `index_project` tool introduced for AST-based code parsing using `tree-sitter`.
- Unified `search_context` tool that searches across both semantic code chunks and manual decisions.
- Replaced `store_context` with `remember_decision` for storing architectural reasoning.

### Added
- Support for extracting AST nodes (classes, methods, functions) for Python, Java, PHP, TypeScript, and JavaScript using `tree-sitter-languages`.
- Structural HTML extraction using `BeautifulSoup`.
- Added snippet for `AGENTS.md` to instruct LLMs on brain usage.
- GitHub Action for automated releases to PyPI on tag creation.
- Project restructuring into a proper Python package (`src/mcp_context_memory`).
- Automated test suite using `pytest` and `pytest-mock`.
- GitHub Action to run tests on push and pull request.
- Explicitly set all project and dev dependencies to their latest stable versions as of March 2026.
- Restricted Python version to 3.10-3.12 for `tree-sitter-languages` compatibility.

## [0.1.0] - 2026-03-28

### Added
- Initial implementation of the Local Context Memory MCP server.
- Basic tools: `store_context`, `query_context`, `list_all_topics`.
