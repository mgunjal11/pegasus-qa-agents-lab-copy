#!/usr/bin/env python3
"""Patch report-template.html Â§5 traceability section visibility."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / ".cursor/skills/coverage-validator/report-template.html"
t = p.read_text(encoding="utf-8")

old_css = """    .section-trace { border: 1px solid #c4b5fd; }
    .section-trace .section-head { background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%); }
    .section-trace .section-body { background: linear-gradient(180deg, #faf5ff 0%, #fff 100%); padding: 0; }
    .section-trace .table-wrap { padding: 0 1rem 1rem; overflow-x: auto; }
    .section-trace table th { background: #ede9fe; color: #5b21b6; }
    .section-trace tbody tr:nth-child(even) { background: #faf5ff; }
    .section-trace td:first-child { font-weight: 700; color: #6d28d9; }"""

new_css = """    .section-trace { border: 2px solid #8b5cf6; }
    .section-trace .section-head { background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%); }
    .section-trace .section-body {
      background: linear-gradient(180deg, #faf5ff 0%, #fff 100%);
      padding: 1.25rem 1.5rem 1.5rem;
    }
    .section-trace .trace-section-lead {
      color: #4c1d95;
      font-size: 0.875rem;
      margin-bottom: 1rem;
      padding: 0.65rem 0.9rem;
      background: #ede9fe;
      border-left: 3px solid #7c3aed;
      border-radius: 0 6px 6px 0;
      line-height: 1.5;
    }
    .section-trace .table-wrap {
      padding: 0.25rem 0 0;
      overflow-x: auto;
      overflow-y: visible;
      margin-bottom: 0.5rem;
    }
    .section-trace table.trace-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid #c4b5fd;
      border-radius: 8px;
      overflow: visible;
      font-size: 0.9rem;
      background: #fff;
    }
    .section-trace table.trace-table th {
      background: #ede9fe;
      color: #4c1d95;
      font-weight: 700;
      padding: 0.7rem 0.75rem;
      text-align: left;
      border-bottom: 2px solid #c4b5fd;
    }
    .section-trace table.trace-table td {
      color: #1e293b;
      vertical-align: top;
      padding: 0.7rem 0.75rem;
      border-bottom: 1px solid #ede9fe;
      line-height: 1.45;
    }
    .section-trace tbody tr:nth-child(even) td { background: #faf5ff; }
    .section-trace tbody tr:hover td { background: #f5f3ff; }
    .section-trace td:first-child { font-weight: 700; color: #6d28d9; white-space: nowrap; }
    .section-trace td:nth-child(2) { min-width: 200px; max-width: 340px; }
    .section-trace td.evidence-cell { min-width: 180px; max-width: 300px; }
    .section-trace .evidence-list {
      margin: 0.25rem 0 0.35rem;
      padding-left: 1.15rem;
      font-size: 0.8rem;
      list-style: disc;
    }
    .section-trace .evidence-list code {
      font-size: 0.78rem;
      word-break: break-word;
      white-space: normal;
      background: #f1f5f9;
      padding: 0.1rem 0.25rem;
      border-radius: 3px;
    }
    .section-trace .evidence-empty { color: #94a3b8; }"""

old_body = """      <div class="section-body">
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th><th>Requirement</th><th>Code</th><th>Dev tests</th><th>Owner</th><th>QA scope</th><th>Evidence</th></tr>"""

new_body = """      <div class="section-body">
        <p class="trace-section-lead">Per-requirement mapping from Jira acceptance criteria to branch/PR code, dev tests, ownership, and file-level evidence.</p>
        <div class="table-wrap">
          <table class="trace-table">
            <thead>
              <tr><th>ID</th><th>Requirement</th><th>Code</th><th>Dev tests</th><th>Owner</th><th>QA scope</th><th>Evidence</th></tr>"""

changed = False
if old_css in t:
    t = t.replace(old_css, new_css)
    changed = True
if old_body in t:
    t = t.replace(old_body, new_body)
    changed = True
if changed:
    p.write_text(t, encoding="utf-8")
    print("patched", p)
else:
    print("no changes needed", p)
