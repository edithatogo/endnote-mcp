# Contributing to endnote-mcp

EndNote MCP makes a user's EndNote library searchable through an MCP server and command-line tools. Useful contributions include parser and search fixes, server interoperability, packaging, tests and documentation.

## Before you start

Read [README.md](README.md) and [pyproject.toml](pyproject.toml), then check existing issues and pull requests. Identify whether a change affects metadata, attachments, semantic indexing, CLI behaviour or desktop bundles. Use synthetic library records and documents that can be redistributed; personal research libraries are not development fixtures.

For bugs, provide the affected version or commit, environment, minimal reproduction, expected result and observed result. For a substantial proposal, describe the use case and compatibility impact before expanding implementation scope. Use existing issue templates when offered.

## Development and validation

Follow the Python version matrix in [Tests](.github/workflows/test.yml). The existing workflow installs the relevant extras and runs:

```sh
uv sync --extra dev --extra semantic
uv run pytest tests/ -v
```

Run the affected test modules during development and the applicable suite before integration. Report which supported Python versions and optional capabilities were actually exercised. Record unavailable semantic models or external resources rather than treating a skipped path as verified.

Add a regression example for changed parsing, citations, search results or error handling, and update user-facing configuration guidance. Packaging changes should also follow the README's bundle-building and version-check instructions. Check CLI and desktop configuration compatibility and explain migration or reindexing needs. An indexing test should not modify a contributor's original EndNote library.

## Pull requests

Create a focused branch from the current `main` branch and submit a pull request to this repository. Link the relevant issue or existing project task, explain the resulting behaviour, and update affected examples and documentation. Keep unrelated changes in separate pull requests.

Report executed commands, outcomes and the commit they validate. Identify unavailable checks and remaining limitations explicitly. Follow the repository's existing review and automated-check requirements; retain required gates and current ownership. Address findings and verify the final head before integration. Repository changes do not themselves authorise a release or external operational action.

## Security, rights and conduct

Follow the [security policy](https://github.com/edithatogo/.github/blob/main/SECURITY.md). Use private vulnerability reporting if available; otherwise request a private contact without publishing vulnerability details. Keep credentials, personal information and restricted source material out of issues, fixtures, logs and artifacts.

Read the [existing licence](LICENSE) and preserve attribution and third-party terms. Follow the [code of conduct](https://github.com/edithatogo/.github/blob/main/CODE_OF_CONDUCT.md) and keep technical discussions respectful.

## Basis for this guide

This guide follows [GitHub's contribution-guideline guidance](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors) and the contribution-process and testing principles in [OpenSSF Best Practices](https://www.bestpractices.dev/en/criteria). It does not assert certification.
