# Security Policy

This repository is intended for **public release**. This document describes how
secrets are kept out of version control, how to report a vulnerability, and the
checks to run before publishing or tagging a release.

## Scope

**vsmlite-tb** is a research/engineering template for running Viable System
Model (VSM) cycles against the Terminal-Bench evaluation harness. It is not a
production service: there is no public network surface, no database of user
data, and no long-running server component. The threats this policy focuses on
are therefore:

- Leakage of **API keys, tokens, or credentials** into the public repository
  or its history.
- Inclusion of **copyrighted or private third-party materials** (e.g. book
  PDFs, datasets gated behind an NDA).
- Accidental exposure of **local filesystem paths, identities, or host
  network details**.

## Secret handling

### Never commit secrets

Secrets and credential files are git-ignored at the repository root and in the
child template (`seed/child/.gitignore`). The ignored set includes, but is not
limited to:

```
.env                # local environment file (real values)
.env.*              # .env.local, .env.production, etc.
*.secret            # arbitrary secret blobs
secrets.json
credentials.json
*.pem, *.key        # private keys
id_rsa*             # SSH keys
*.pfx, *.p12        # certificate bundles
```

`.env.example` is deliberately **tracked** (negated via `!.env.example`) because
it carries only commented placeholders.

### How secrets are read

Runtime secrets (e.g. `HF_TOKEN`) are read from the environment through
`os.environ.get(...)` (see `eval/config.py`). They are never written into
Python source, shell scripts, or tracked JSON state. The eval datasets are
public, so most tokens are optional.

### If a secret is leaked

Treat any committed credential as **compromised**, regardless of how long it
was exposed:

1. **Rotate / revoke** the credential at its provider immediately. Do not wait
   for history to be rewritten — public mirrors and forks may already hold it.
2. **Remove** the secret from the current tree.
3. **Purge** it from history (e.g. `git filter-repo`, BFG, or GitHub support
   for the affected repo). Force-push the cleaned history and notify anyone
   with a clone.
4. **Open an issue** summarizing the scope (what leaked, how long, what was
   rotated). Do **not** paste the secret into the issue.

## Reporting a vulnerability

We welcome responsible disclosure. If you believe you have found a security
issue (a leaked credential in history, an exploitable flaw, an inclusion of
protected material):

- **Preferred:** open a **private** GitHub Security Advisory
  (`Security` tab → `Report a vulnerability`). This keeps the report private
  until a fix is released.
- **Alternative:** open a confidential issue describing the impact without
  including any secret material.

Please include:

- What you found and where (file path / commit range).
- The potential impact.
- Suggested remediation, if any.

We will acknowledge receipt within a reasonable timeframe and coordinate a
fix and disclosure schedule with you.

## Pre-publish checklist

Run through this list before making a repository public or tagging a release.
Most items are enforced by the automated hooks below, but a manual pass is the
last line of defense.

- [ ] `.gitignore` covers `.env`, `.env.*`, and credential files (it does).
- [ ] No `.env` or `*.secret` file is tracked: `git ls-files | grep -iE '\.env$|\.secret'` returns nothing.
- [ ] Scan the **entire** history, not just `HEAD`:
      `git log --all -p | gitleaks detect --git -v` (or `detect-secrets` /
      `trufflehog`) reports no findings.
- [ ] `*.pdf` and other copyrighted materials are not tracked
      (`git ls-files | grep -i '\.pdf$'` returns nothing).
- [ ] No private filesystem paths (`/home/`, `/Users/`, `/mnt/...`),
      personal emails, or internal hostnames appear in tracked files.
- [ ] `.env.example` contains only commented placeholders — no real values.
- [ ] `seed/child/.gitignore` mirrors the secret rules above (child projects
      inherit them).

## Automated scanning

Secret detection is wired into pre-commit so leaks are caught **before** they
enter the tree. The configuration lives in `.pre-commit-config.yaml` and uses
[gitleaks](https://github.com/gitleaks/gitleaks).

Install once:

```bash
pip install pre-commit
pre-commit install
```

Thereafter, the gitleaks hook runs automatically on `git commit`. To scan the
full history manually at any time (e.g. before going public):

```bash
gitleaks detect --source . --verbose
```
