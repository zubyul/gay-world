#!/usr/bin/env python3
"""Ingest canonical tasks into Magic ToDo MLX for enrichment.

Reads the canonical task JSON (produced by worlds/a/dedup_tasks.py),
feeds each task through magic_todo_mlx.py's _generate_plan() to enrich
with subtasks/categories, and writes back to the canonical org file.

Pipeline: worlds/a/canonical_tasks.json -> [this] -> worlds/p/capture-buffer-canonical.org

Usage:
    python3 ingest_to_magic.py [--input FILE] [--output FILE] [--model MODEL]
                               [--spice N] [--dry-run] [--max-tasks N]

Without --model or MLX available, falls back to a rule-based breakdown
that still produces useful org output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
WORLDS_ROOT = SCRIPT_DIR.parent.parent.parent  # worlds/
DEFAULT_INPUT = WORLDS_ROOT / 'a' / 'canonical_tasks.json'
DEFAULT_OUTPUT = WORLDS_ROOT / 'p' / 'capture-buffer-canonical.org'

# Try to import magic_todo_mlx for MLX-powered enrichment
sys.path.insert(0, str(SCRIPT_DIR))
_MLX_AVAILABLE = False
try:
    from magic_todo_mlx import _generate_plan, GenCfg
    _MLX_AVAILABLE = True
except ImportError:
    pass

DEFAULT_MODEL = os.environ.get('MAGIC_TODO_MODEL', 'mlx-community/Qwen3-8B-4bit')


def _rule_based_breakdown(task_text, priority=None):
    """Fallback: produce a simple rule-based breakdown without MLX.

    Returns dict matching magic_todo_mlx plan schema:
    {"title": str, "steps": [{"text": str, "substeps": None}]}
    """
    steps = []
    text_lower = task_text.lower()

    # Heuristic step generation based on task content
    if any(kw in text_lower for kw in ['buy', 'purchase', 'order']):
        steps = [
            {"text": "Find best price/vendor", "substeps": None},
            {"text": "Add to cart or place order", "substeps": None},
            {"text": "Confirm shipping/delivery", "substeps": None},
        ]
    elif any(kw in text_lower for kw in ['deploy', 'launch', 'release']):
        steps = [
            {"text": "Check all prerequisites are ready", "substeps": None},
            {"text": "Run deployment command or script", "substeps": None},
            {"text": "Confirm service is live and responding", "substeps": None},
        ]
    elif any(kw in text_lower for kw in ['configure', 'set up', 'setup', 'install']):
        steps = [
            {"text": "Gather required credentials/keys", "substeps": None},
            {"text": "Run configuration commands", "substeps": None},
            {"text": "Confirm setup works end-to-end", "substeps": None},
        ]
    elif any(kw in text_lower for kw in ['register', 'sign up', 'enroll']):
        steps = [
            {"text": "Prepare required documents/info", "substeps": None},
            {"text": "Submit registration form", "substeps": None},
            {"text": "Follow up on confirmation", "substeps": None},
        ]
    elif any(kw in text_lower for kw in ['fix', 'debug', 'resolve']):
        steps = [
            {"text": "Reproduce the issue", "substeps": None},
            {"text": "Identify root cause", "substeps": None},
            {"text": "Apply fix and confirm resolution", "substeps": None},
        ]
    elif any(kw in text_lower for kw in ['build', 'create', 'implement', 'add']):
        steps = [
            {"text": "Define scope and requirements", "substeps": None},
            {"text": "Implement core functionality", "substeps": None},
            {"text": "Integrate with existing system", "substeps": None},
        ]
    else:
        steps = [
            {"text": "Identify first concrete action", "substeps": None},
            {"text": "Execute the action", "substeps": None},
            {"text": "Confirm completion", "substeps": None},
        ]

    return {
        "title": task_text,
        "steps": steps,
    }


def enrich_task(task_text, spice=3, model=None, use_mlx=True):
    """Enrich a task with subtask breakdown.

    If MLX is available and use_mlx=True, uses the local LLM.
    Otherwise falls back to rule-based breakdown.

    Returns dict: {"title": str, "steps": [{"text": str, "substeps": ...}]}
    """
    if use_mlx and _MLX_AVAILABLE and model:
        try:
            cfg = GenCfg(
                model=model,
                spice=spice,
                max_tokens=900,
                temp=0.2,
                top_p=0.9,
                seed=42,
                context=None,
                mcp_servers=None,
            )
            plan = _generate_plan(task_text, cfg)
            return plan
        except Exception as e:
            print(f"  MLX enrichment failed for '{task_text[:50]}...': {e}",
                  file=sys.stderr)
            return _rule_based_breakdown(task_text)
    else:
        return _rule_based_breakdown(task_text)


def format_org_timestamp(dt=None):
    """Format datetime as org-mode timestamp."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('[%Y-%m-%d %a %H:%M]')


def state_to_org_keyword(state, is_done=False):
    """Map canonical state to org TODO keyword."""
    if is_done:
        return 'DONE'
    state_map = {
        'NOW': 'NOW',
        'NEXT': 'NEXT',
        'TODO': 'TODO',
        'BUY': 'BUY',
        'BLOCKED': 'BLOCKED',
        'IN_PROGRESS': 'IN_PROGRESS',
        'STARTED': 'STARTED',
        'SUBSTANTIAL': 'NEXT',
        'ABANDONED': 'CANCELLED',
    }
    return state_map.get(state, 'TODO')


def tasks_to_canonical_org(tasks, enrichments, output_path):
    """Write canonical org file from tasks and their enrichments.

    Args:
        tasks: list of canonical task dicts from dedup_tasks.py
        enrichments: dict mapping task_id -> plan dict
        output_path: path to write the org file
    """
    lines = []
    now_ts = format_org_timestamp()

    # Header
    lines.append('#+TITLE: Canonical Capture Buffer — Single Source of Truth')
    lines.append('#+AUTHOR: magic-todo-dedup-pipeline')
    lines.append('#+DATE: ' + now_ts)
    lines.append('#+STARTUP: overview indent')
    lines.append('#+TODO: NOW(!) NEXT(n) TODO(t) BUY(B) BLOCKED(b) IN_PROGRESS(p) | DONE(d) CANCELLED(c)')
    lines.append('#+PRIORITIES: A B C')
    lines.append('#+PROPERTY: header-args :eval never')
    lines.append('')
    lines.append('# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('# This file is AUTO-GENERATED by the M-A-P dedup pipeline.')
    lines.append('# Source: worlds/a/dedup_tasks.py -> worlds/m/ingest_to_magic.py')
    lines.append('# All other org files in worlds/p/projects/ are read-only archives.')
    lines.append('# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('')

    # Stats section
    active_count = sum(1 for t in tasks if not t.get('is_done', False))
    done_count = sum(1 for t in tasks if t.get('is_done', False))
    lines.append('* Pipeline Stats')
    lines.append(':PROPERTIES:')
    lines.append(':GENERATED: ' + now_ts)
    lines.append(':TOTAL_TASKS: ' + str(len(tasks)))
    lines.append(':ACTIVE: ' + str(active_count))
    lines.append(':END:')
    lines.append('')

    # Group tasks by category (based on tags and state)
    categories = {}
    for task in tasks:
        tags = task.get('tags', [])
        state = task.get('state', 'TODO')

        if state == 'BUY':
            cat = 'Purchases'
        elif state == 'NOW':
            cat = 'Immediate Actions'
        elif any(t in tags for t in ['chain', 'aptos', 'move']):
            cat = 'Blockchain & Aptos'
        elif any(t in tags for t in ['bci', 'audio', 'hardware']):
            cat = 'Hardware & Audio'
        elif any(t in tags for t in ['infra', 'cloud', 'network']):
            cat = 'Infrastructure'
        elif any(t in tags for t in ['teglonlabs', 'entity']):
            cat = 'Teglon Labs'
        elif any(t in tags for t in ['social', 'loom']):
            cat = 'Social & Coordination'
        elif state in ('BLOCKED', 'IN_PROGRESS', 'STARTED'):
            cat = 'In Progress & Blocked'
        else:
            cat = 'General Tasks'

        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)

    # Category ordering preference
    cat_order = [
        'Immediate Actions', 'Purchases', 'In Progress & Blocked',
        'Teglon Labs', 'Blockchain & Aptos', 'Hardware & Audio',
        'Infrastructure', 'Social & Coordination', 'General Tasks',
    ]

    for cat in cat_order:
        if cat not in categories:
            continue
        cat_tasks = categories[cat]

        lines.append('* ' + cat)
        lines.append('')

        for task in cat_tasks:
            task_id = task.get('id', 0)
            text = task['text']
            state = state_to_org_keyword(task.get('state', 'TODO'),
                                         task.get('is_done', False))
            priority = task.get('priority')

            # Build heading
            prio_str = ' [#%s]' % priority if priority else ''
            heading = '** %s%s %s' % (state, prio_str, text)
            lines.append(heading)

            # Properties
            lines.append(':PROPERTIES:')
            lines.append(':TASK_ID: %d' % task_id)
            sources = task.get('source_files', [])
            if sources:
                lines.append(':SOURCES: %s' % ', '.join(sources))
            dup_count = task.get('duplicate_count', 1)
            if dup_count > 1:
                lines.append(':DUPLICATES: %d' % dup_count)
            for pk, pv in task.get('properties', {}).items():
                if pk not in ('TASK_ID', 'SOURCES', 'DUPLICATES'):
                    lines.append(':%s: %s' % (pk, pv))
            lines.append(':END:')

            # Enrichment (subtasks from magic-todo)
            enrichment = enrichments.get(task_id)
            if enrichment and enrichment.get('steps'):
                for step in enrichment['steps']:
                    step_text = step.get('text', '').strip()
                    if step_text:
                        lines.append('*** TODO ' + step_text)
                    substeps = step.get('substeps')
                    if substeps and isinstance(substeps, list):
                        for ss in substeps:
                            if isinstance(ss, str) and ss.strip():
                                lines.append('**** TODO ' + ss.strip())
                            elif isinstance(ss, dict) and ss.get('text', '').strip():
                                lines.append('**** TODO ' + ss['text'].strip())

            lines.append('')

    # Add uncategorized leftover
    used_cats = set(cat_order)
    for cat, cat_tasks in categories.items():
        if cat in used_cats:
            continue
        lines.append('* ' + cat)
        lines.append('')
        for task in cat_tasks:
            task_id = task.get('id', 0)
            text = task['text']
            state = state_to_org_keyword(task.get('state', 'TODO'))
            lines.append('** %s %s' % (state, text))
            lines.append('')

    # Write file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return len(tasks)


def main():
    ap = argparse.ArgumentParser(
        description='Ingest canonical tasks through Magic ToDo MLX enrichment.')
    ap.add_argument('--input', '-i', default=str(DEFAULT_INPUT),
                    help='Input canonical tasks JSON (from dedup_tasks.py)')
    ap.add_argument('--output', '-o', default=str(DEFAULT_OUTPUT),
                    help='Output canonical org file')
    ap.add_argument('--model', default=DEFAULT_MODEL,
                    help='MLX model to use for enrichment')
    ap.add_argument('--spice', type=int, default=3, choices=[1, 2, 3, 4, 5],
                    help='Breakdown granularity (1=simple, 5=extreme)')
    ap.add_argument('--no-mlx', action='store_true',
                    help='Skip MLX enrichment, use rule-based fallback')
    ap.add_argument('--dry-run', action='store_true',
                    help='Print plan without writing files')
    ap.add_argument('--max-tasks', type=int, default=None,
                    help='Process at most N tasks (for testing)')

    args = ap.parse_args()

    # Read canonical tasks
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        print(f"Run worlds/a/dedup_tasks.py first to generate it.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tasks = data.get('tasks', [])
    if not tasks:
        print("No tasks found in input.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(tasks)} canonical tasks from {args.input}", file=sys.stderr)

    # Limit tasks if requested
    if args.max_tasks:
        tasks = tasks[:args.max_tasks]
        print(f"Processing first {len(tasks)} tasks (--max-tasks)", file=sys.stderr)

    # Enrich each task
    use_mlx = not args.no_mlx and _MLX_AVAILABLE
    if use_mlx:
        print(f"Using MLX model: {args.model}", file=sys.stderr)
    else:
        if not args.no_mlx and not _MLX_AVAILABLE:
            print("MLX not available, using rule-based fallback.", file=sys.stderr)
        else:
            print("Using rule-based fallback (--no-mlx).", file=sys.stderr)

    enrichments = {}
    for i, task in enumerate(tasks):
        task_id = task.get('id', i + 1)
        task_text = task['text']
        is_done = task.get('is_done', False)

        if is_done:
            # Don't enrich completed tasks
            continue

        print(f"  [{i+1}/{len(tasks)}] Enriching: {task_text[:60]}...",
              file=sys.stderr)

        plan = enrich_task(
            task_text,
            spice=args.spice,
            model=args.model if use_mlx else None,
            use_mlx=use_mlx,
        )
        enrichments[task_id] = plan

    print(f"Enriched {len(enrichments)} tasks.", file=sys.stderr)

    if args.dry_run:
        print("\n--- DRY RUN: Would write to", args.output, "---")
        preview = {
            'task_count': len(tasks),
            'enriched_count': len(enrichments),
            'sample_enrichment': enrichments.get(
                next(iter(enrichments), None), None
            ),
        }
        json.dump(preview, sys.stdout, indent=2)
        print()
        return 0

    # Write canonical org
    count = tasks_to_canonical_org(tasks, enrichments, args.output)
    print(f"Wrote {count} tasks to {args.output}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
