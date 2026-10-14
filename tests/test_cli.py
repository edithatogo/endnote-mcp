"""CLI behaviour that the server's rebuild_index tool depends on."""

import sqlite3

import yaml
from click.testing import CliRunner

from endnote_mcp.cli import cli


def test_index_reads_config_from_env(sample_xml, tmp_path, monkeypatch):
    """rebuild_index runs `endnote-mcp index` without --config, so a server
    configured through ENDNOTE_MCP_CONFIG, as the desktop bundle is, must have
    its indexer read that file rather than the platform default."""
    db_path = tmp_path / "library.db"
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({
        "endnote_xml": str(sample_xml),
        "pdf_dir": str(tmp_path),
        "db_path": str(db_path),
    }), encoding="utf-8")
    monkeypatch.setenv("ENDNOTE_MCP_CONFIG", str(config))
    # Keep the platform default out of reach: it may hold a real library.
    monkeypatch.setattr(
        "endnote_mcp.cli.get_default_config_path", lambda: tmp_path / "missing.yaml",
    )
    monkeypatch.setattr("endnote_mcp.embeddings.is_available", lambda: False)

    result = CliRunner().invoke(cli, ["index", "--skip-pdfs"])

    assert result.exit_code == 0, result.output
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM references_").fetchone()[0] == 3
    conn.close()
