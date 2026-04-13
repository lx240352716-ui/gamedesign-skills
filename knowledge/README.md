# Knowledge Base

This directory contains the project's knowledge base. Source data files are not tracked by git — only the directory structure and READMEs are committed.

## Directory Structure

```
knowledge/
  README.md          # This file
  gamedocs/          # Place .docx/.xlsx design documents here
  gamedata/          # Place gamedata .xlsx tables here (organized by module)
  wiki/              # Auto-generated wiki (by wiki_compiler.py)
```

## Setup

1. Place your `.docx` design documents in `gamedocs/`
2. Place your `.xlsx` game data tables in `gamedata/{ModuleName}/`
3. Run the initialization scripts:

```bash
# Parse gamedocs -> generates .cache/*.md
python references/scripts/core/doc_reader.py

# Parse gamedata tables -> generates knowledge md files
python references/scripts/core/table_reader.py

# Compile wiki from parsed data
python references/scripts/core/wiki_compiler.py
```

## Generated Files

After running the scripts, the following files will be generated:

- `knowledge/*.md` — Table-level knowledge (skill.md, buff.md, hero.md, etc.)
- `knowledge/gamedocs/.cache/*.md` — Parsed design documents (markdown)
- `knowledge/wiki/*.md` — Compiled wiki (entities, concepts, index)
- `knowledge/wiki/cn_en_map.json` — Chinese-English term mapping

These generated files are excluded from git (`.gitignore`).
