# Instantiation checklist

Use this list to apply [evidence-gated roles](evidence-gated-roles.md) in a repository. Accessible overview: [manifesto.md](manifesto.md). Items are ordered for greenfield work; on an existing repo, audit in the same order and record gaps honestly.

**Terminology:** **HWIL** = hardware-in-the-loop (actuator automation). **Human** / **human-in-the-loop** = operator role (always spelled out; `HUMAN_*` env tokens).

## Checklist

1. **Name roles** — Human (human-in-the-loop), actuator automation (HWIL), software (SIL), environment, consumer, harness. One tree or package per role. Per-role agent rules state **may invent?** explicitly.

2. **Evidence contract** — Choose a gitignored (or clearly non-source) evidence root. Define schemas for unlock records (status, reason, next command, metrics). Only the harness reads unlock predicates; producers write evidence; consumers call `require_*` and refuse closed.

3. **Split human assent from automation flags** — Human-only tokens (`HUMAN_*`) for path, identity confirmation, and energize confirm. Separate sim/automation flags (`RAD_LAB_HWIL_SIM`) that skip USB or prompts without forging human claims. Agents must not set assent tokens.

4. **License / identity policy** — No hardcoded operator identity. Require explicit supply (env or CLI). Validate shape; do not invent identity to unblock a lab. Document that legality stays with the human.

5. **Power / duration policy** — Encode ceilings in manifests. Fail-closed clamp before energize. Tests assert defaults respect ceilings. Agents must not raise limits to pass a stage. (Domain equivalents: torque, bias voltage, duty cycle.)

6. **Human-readable writeups** — For any step that expects judgment or assent, write a short scannable summary beside machine JSON: pass/fail, identity/limits used, decisive metrics, plots pointer, next command on failure. Assent without that summary is incomplete human-in-the-loop practice.

7. **Import and lint rules** — Consumers must not import actuator transmit/flash modules. Human assent modules must not import those either. Enforce with tests (AST import lint or equivalent).

8. **Make / CI map to roles** — `check` / `sim` → software (SIL) and harness unit tests; image/archive → environment; stage/energize/firmware → HWIL actuator automation after human assent; lesson/consumer → refuses unless evidence ready. CI stays AI-native for software; physical stages use sim only when explicitly gated.

9. **Document the two loops** — Autonomous (SIL) vs physical (human constructs, HWIL measures). Refusals print the **next human command**. Root agent router points at per-role rules.

10. **Defer until needed** — Instruments, multi-step campaigns, and injury/hazard classes are optional extensions. Do not conflate them with license/identity or power/duration. Do not build a fat orchestrator that prompts and energizes.

## rad-lab mapping

| Checklist item | Current instantiation | Gap? |
| --- | --- | --- |
| 1 Roles | [`human/`](../../human/), [`hardware/`](../../hardware/) (HWIL), [`software/`](../../software/), [`environment/`](../../environment/), [`lesson/`](../../lesson/), [`harness/`](../../harness/); [`AGENTS.md`](../../AGENTS.md) | No |
| 2 Evidence | `reports/<board>/stage.json`; [`harness/ready.py`](../../harness/ready.py); [`harness/radboards.py`](../../harness/radboards.py) | Partial: campaign labs write under `reports/` but do not always unlock via harness predicates |
| 3 Assent vs sim | Human assent via `HUMAN_LOOPBACK`, `HUMAN_TX_CONFIRM`, `HUMAN_FIRMWARE`; sim via `RAD_LAB_HWIL_SIM` in [`human/assent.py`](../../human/assent.py) | No |
| 4 License / identity | Callsign via `RAD_LAB_CALLSIGN` / `--callsign` in [`human/assent.py`](../../human/assent.py); [`local.env.example`](../../local.env.example) | No hardcoded default; no license-database verification (by design) |
| 5 Power / duration | Board `max_tx_db` / `max_tx_ms`; `clamp_tx_gain` / `require_tx` | Watch for labs that bypass clamp—audit when adding TX paths |
| 6 Human-readable writeups | JSON, JUnit, plots; stage failures include `reason` / `next` | **Yes** — no standard `REPORT.md` beside every judgment step; [`hardware/docs/reports.md`](../../hardware/docs/reports.md) still emphasizes machine scrapers |
| 7 Import lint | [`harness/tests/test_import_lint.py`](../../harness/tests/test_import_lint.py) | Covers `lesson`, `human`, `software`, and `harness` role boundaries |
| 8 Make / CI | [`Makefile`](../../Makefile); [`.github/workflows/check.yml`](../../.github/workflows/check.yml) | No |
| 9 Two loops documented | This folder + role READMEs | Keep root pointer current |
| 10 Deferrals | Hazard classes not in feature set; instruments/campaigns not generalized | Intentional |

## Applying elsewhere

Copy the role permission table and evidence rules; rename trees to the domain. Keep the harness thin. Treat the first physical energize path as the place where human assent, ceilings, identity, and writeups must meet—everything else can stay software-autonomous (SIL) until then.
