# gay-world

> *"Demos print and discard. Worlds compose and persist."*

SCUM-scored task decomposition that returns **worlds**, not todos. Each breakdown is a composable, persistent `WorldType` — not an ephemeral checklist that gets checked and forgotten.

Formerly `magic-todo-org` → `scum-world` → `gay-world`. Todo is an antipattern: it prints and discards. Worlds compose and persist.

## The Shift

| Old (todo) | New (world) | Why |
|------------|-------------|-----|
| `TODO Buy shoes` | `world_shoe_acquisition(constraints)` | Returns composable structure |
| `- [ ] check` | `WorldStep(:validate, scum=12)` | SCUM-scored, mergeable |
| Done → archive | Done → `merge(world1, world2)` | Worlds compose into larger worlds |

## SCUM Scoring (GF(3))

Every world-step carries a [SCUM score](https://github.com/plurigrid/asi/tree/main/skills/scum-resource):

```
SCUM(step) = α·MEM + β·CPU + γ·TIME + δ·STALE
```

| Trit | SCUM Range | Action |
|------|-----------|--------|
| **+1** | 0-33 | Execute locally (healthy) |
| **0** | 34-66 | Delegate or schedule (monitor) |
| **-1** | 67-100 | Kill or rent-a-human (terminate) |

## Contents

- `emacs/magic-todo-org.el`: Emacs integration (Org-mode world builder)
- `scripts/magic_todo_mlx.py`: CLI world decomposition via MLX-LM
- `scripts/ingest_to_magic.py`: Batch ingest canonical tasks into worlds

## Usage

```bash
# Decompose a task into a world
echo "set up apartment bedroom" | python scripts/magic_todo_mlx.py --format json --spice 3

# The output is a world, not a todo:
# { "title": "Bedroom Setup World",
#   "steps": [
#     {"text": "Order mattress via channel A", "scum": 15},
#     {"text": "Rent-a-human: furniture assembly (channel H)", "scum": 45},
#     ...
#   ]}
```

### MCP Awareness

Auto-discovers MCP servers from `~/.claude/mcp.json` etc. and injects tool names into the decomposition prompt.

## Emacs

```elisp
(add-to-list 'load-path "/path/to/scum-world/emacs")
(require 'magic-todo-org)  ;; elisp name preserved for backward compat
```

| Command | Description |
|---------|-------------|
| `magic-todo-org-insert` | Decompose task → insert world as Org checklist |
| `magic-todo-org-refresh-at-point` | Re-decompose heading into world |
| `magic-todo-org-regenerate-file` | Batch re-decompose all headings |
| `magic-todo-org-roam-new` | Create org-roam note with world |

## Triad

```
scum-resource (-1) ⊗ gay-world (0) ⊗ rent-a-human (+1) = 0 ✓
```

- **scum-resource**: System-level process scoring (what to kill)
- **gay-world**: Task-level world decomposition (this repo)
- **rent-a-human**: Channel H/Q dispatch when SCUM says delegate

## Requirements

- macOS on Apple Silicon
- Python 3.12+ with `mlx` + `mlx-lm`
- MLX model (default: `mlx-community/Qwen3-8B-4bit`)
