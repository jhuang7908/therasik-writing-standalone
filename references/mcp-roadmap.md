# MCP Integration Guide
## TheraSIK Academic Writing Suite

Version: 1.0.0  
Transport: stdio (works with all MCP clients)

---

## Quick Start (all platforms)

```bash
# 1. Install dependencies
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\writing_system_productization\therasik-academic-writing-suite"
pip install -r requirements-mcp.txt

# 2. Verify installation
python scripts/validate_basic_skill.py .

# 3. Start the MCP server (stdio)
python scripts/mcp_server.py
```

---

## Platform Integration

### Claude Code (CLI)

Add to `~/.claude/claude_desktop_config.json` (or via `claude mcp add`):

```json
{
  "mcpServers": {
    "therasik": {
      "command": "python",
      "args": ["scripts/mcp_server.py"],
      "cwd": "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite"
    }
  }
}
```

Then in Claude Code:
```
/mcp therasik search_literature query="antibody complement activation"
/mcp therasik get_journal_requirements journal_name="nature"
/mcp therasik create_manuscript_project project_dir="./my_paper"
```

### Cursor

In `.cursor/mcp.json` (project root) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "therasik": {
      "command": "python",
      "args": [
        "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite/scripts/mcp_server.py"
      ],
      "env": {
        "THERASIK_DIR": "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite"
      }
    }
  }
}
```

Cursor will auto-discover all 13 tools. Use via Agent mode or `@therasik`.

### Codex (OpenAI)

Codex supports MCP via its tool config. Add to your Codex project config:

```json
{
  "tools": [
    {
      "type": "mcp",
      "server": {
        "command": "python",
        "args": [
          "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite/scripts/mcp_server.py"
        ]
      }
    }
  ]
}
```

### Antigravity / Any stdio-compatible client

Point the client at the server script. The server speaks MCP over stdin/stdout:

```bash
python "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite/scripts/mcp_server.py"
```

### Cowork (Claude Desktop)

In Cowork settings, add a custom MCP server:
- Command: `python`
- Args: `scripts/mcp_server.py`
- Working directory: `D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\writing_system_productization\therasik-academic-writing-suite`

---

## Available Tools (17 total)

### Manuscript Workflow

| Tool | Description |
|------|-------------|
| `create_manuscript_project` | Scaffold a new project from template |
| `run_manuscript_workflow` | Run full QA + render pipeline |
| `get_manuscript_status` | Read all gate statuses at a glance |
| `run_qa_gate` | Run a single QA gate (reference/ai_style/paragraph/figure) |

### Literature Database (RAG)

| Tool | Description |
|------|-------------|
| `search_literature` | FTS5 + TF-IDF search over stored papers |
| `add_paper_by_doi` | Fetch via cloud proxy (cached) or CrossRef direct |
| `add_paper_by_pmid` | Fetch via cloud proxy (cached) or PubMed direct |
| `get_paper` | Retrieve paper by ID, DOI, or PMID |
| `import_pdf_full_text` | Extract and store full text from PDF |
| `export_references_csv` | Export papers to project references.csv |

### Journal Requirements (5,226 journals)

| Tool | Description |
|------|-------------|
| `get_journal_requirements` | Word limits, sections, styles — cloud then local |
| `list_journals` | List all journals in the local database |

### Submission Preparation

| Tool | Description |
|------|-------------|
| `check_submission_compliance` | Word count, sections, figures, QA gate status |
| `prepare_submission_package` | Full package: compliance + cover letter + checklist + files |
| `generate_cover_letter` | Journal-specific cover letter template |

### System

| Tool | Description |
|------|-------------|
| `validate_skill_installation` | Check that the suite is correctly installed |

---

## Literature Database CLI (standalone)

The literature database also has a full CLI interface:

```bash
# Initialize
python scripts/literature_db.py init

# Add papers
python scripts/literature_db.py add-doi 10.1038/s41586-021-03819-2
python scripts/literature_db.py add-pmid 34912118

# Search
python scripts/literature_db.py search "antibody complement activation" --limit 10
python scripts/literature_db.py search "FcRn" --year-from 2018 --journal "Nature"

# Get full record
python scripts/literature_db.py get 10.1038/s41586-021-03819-2 --json

# Import PDF full text
python scripts/literature_db.py import-pdf paper.pdf --doi 10.1038/s41586-021-03819-2

# Export to project
python scripts/literature_db.py export-csv abc123 def456 \
  --out "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/ada245/writing_system_productization/therasik-academic-writing-suite/assets/literature_db/exports/references.csv"

# Stats
python scripts/literature_db.py stats
```

---

## Supported Journals (built-in)

| Key | Journal |
|-----|---------|
| `nature` | Nature |
| `science` | Science |
| `cell` | Cell |
| `nejm` | New England Journal of Medicine |
| `lancet` | The Lancet |
| `nature_medicine` | Nature Medicine |
| `plos_one` | PLOS ONE |
| `frontiers_pharmacology` | Frontiers in Pharmacology |
| `jbc` | Journal of Biological Chemistry |
| `immunity` | Immunity |

Add more journals by placing JSON files in `assets/journal_requirements/`
and updating `_index.json`.

---

## Security Notes

- The MCP server has no authentication layer -- run only on localhost or
  trusted internal networks.
- Never pass manuscript text or API keys through public MCP endpoints.
- See `references/versioning.md` for the full security policy.
- Never commit `.env` or provider API keys.
