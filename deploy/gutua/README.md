# `gutua` runtime and development handoff

`gutua` (the UK Gigabyte laptop) is the authoritative 24/7 execution host for
Orchestrator v3, JAA development, and Market Aligner. The Mac is the preferred
machine for digital-twin experiments, but it is not a concurrent JAA worker or
database writer.

## Authority boundaries

- JAA source of truth: `/home/gutua/giga/orchestrator-v3/projects/job-application-automation`
- Orchestrator v3 state: `/home/gutua/giga/orchestrator-v3/state`
- Market Aligner source: `/home/gutua/giga/market-aligner`
- Mutable databases: `/home/gutua/giga/shared/market-aligner`
- Private giga-user corpus: `/home/gutua/giga/giga-user`
- Health snapshot: `/home/gutua/giga/health/status.json`
- Automated database snapshots: `/home/gutua/giga/backups/daily`
- Manual cutover/probe snapshots: `/home/gutua/giga/backups/market-aligner`
- Preserved v2 cold standby: `/home/gutua/cold-standby/orchestrator-v2-20260722T120000Z`
- Preserved Mac JAA worktrees: `/home/gutua/giga/archives/jaa-mac-worktrees-20260722.tar.gz`

Do not develop JAA independently on the Mac after cutover. Bring changes back
with Git, or perform an explicit quiesce/snapshot/reverse-handoff. Never allow
the Mac and `gutua` to write the Market Aligner SQLite files concurrently.

## Services

```text
orchestrator-v3.service              continuous v3/JAA factory
market-aligner-collector.service     continuous Scrapling-aware collection
market-aligner-processor.timer       scoring and opportunity-gate cycle
giga-database-backup.timer           online SQLite snapshots with retention
giga-health.timer                    compact health JSON
```

The active Codex CLI is `0.145.0`; `0.139.0` was the pre-cutover version and
can be restored with `npm install -g @openai/codex@0.139.0` if the newer CLI
itself regresses. The Linux Bubblewrap receipt must be regenerated after any
orchestrator isolation/runner/manifest change:

```bash
cd /home/gutua/giga/orchestrator-v3
.venv/bin/python -m dispatch.isolation certify --root "$PWD"
```

Inspect them from WSL:

```bash
systemctl status orchestrator-v3.service market-aligner-collector.service
systemctl list-timers market-aligner-processor.timer giga-database-backup.timer giga-health.timer
journalctl -u orchestrator-v3.service -n 100 --no-pager
journalctl -u market-aligner-collector.service -n 100 --no-pager
```

The units restart failed long-running processes automatically. Systemd journal
retention is capped at 1 GiB persistent / 256 MiB runtime with a 30-day maximum.
The Windows scheduled task starts Ubuntu/WSL after login; Windows AC
sleep/hibernate and the AC lid-close sleep action are disabled.

## Safe pause and resume

Pause v3 before touching its canonical checkout or state:

```bash
sudo systemctl stop orchestrator-v3.service
touch /home/gutua/giga/orchestrator-v3/STOP
```

Resume only after the checkout and state are coherent:

```bash
mkdir -p /home/gutua/giga/orchestrator-v3/state/operator-stops
mv /home/gutua/giga/orchestrator-v3/STOP \
  /home/gutua/giga/orchestrator-v3/state/operator-stops/STOP.manual-$(date -u +%Y%m%dT%H%M%SZ)
sudo systemctl start orchestrator-v3.service
```

Pause Market Aligner before database maintenance:

```bash
sudo systemctl stop market-aligner-collector.service market-aligner-processor.timer
sudo systemctl stop market-aligner-processor.service
```

## Fetching databases to the Mac

From the giga-user directory on the Mac:

```bash
./deploy/gutua/fetch_market_aligner_databases.sh /absolute/destination
```

This asks `gutua` to create consistent SQLite online backups first, then copies
that immutable snapshot over Tailscale. Treat the fetched files as read-only.

## Rollback

If v3 fails, arm its `STOP` file and stop/disable its service. The old v2 tree
remains untouched at `/home/gutua/agentic-orchestrator`, with an independently
verified snapshot and Git bundle in the cold-standby directory above. Restore
v2 manually only after confirming v3 is stopped; never run both factories
against the same project or state.
