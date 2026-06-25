# _ops — Operational artifacts and runbooks

This directory holds operational documentation and vendor-handoff
packages that aren't part of the runtime addon code. The runtime
modules live in the sibling directories (`cw_*`, `sourcing_reference`,
etc.); `_ops/` is for things humans run, not things Odoo loads.

## Structure

```
_ops/
├── vendor-handoff/
│   └── <YYYY-MM-DD>/         A snapshot prepared for vendor ingest on a
│                             specific date. Each folder contains:
│                               * COVER_NOTE.md
│                               * <date>.bundle           one-shot git bundle
│                               * 0001-*.patch through    text-readable backups
│                                 NNNN-*.patch            of every commit
│
├── backup-recovery/
│   └── RECOVERY.md           Step-by-step restore procedure for
│                             CW19_Test, written against a specific
│                             reference backup. Binary backups (DB
│                             dumps, filestore archives) are NOT tracked
│                             here — they live on the operator's local
│                             machine and on the production box.
│
└── dev-notes/
    ├── README.md            Index of topic-grouped engineering notes
    └── qweb-inherit-gotchas.md   QWeb template-inherit pitfalls
    └── RECOVERY.md           Step-by-step restore procedure for
                              CW19_Test, written against a specific
                              reference backup. Binary backups (DB
                              dumps, filestore tar) are NOT tracked
                              here — they live on the operator's local
                              machine and on the production box.
```

## What is and isn't in here

* **Yes**: cover notes, READMEs, runbooks, format-patches, git bundles
  (all small text or compressed-text payloads useful for review).
* **No**: PostgreSQL dump files, filestore archives, role-password
  globals files, certificates. Those are sensitive and/or large; they
  belong on the operator's backup volume, not in git.

## Why this exists

Historically these artifacts lived only on the operator's laptop or in
ad-hoc paths on the Contabo box. Tracking them in the same repo as the
modules they document means: (1) the vendor sees the handoff package
without a separate channel; (2) when the cover note references a
specific commit SHA, that commit is reachable from the same repo; (3)
runbooks evolve alongside the code they describe.
