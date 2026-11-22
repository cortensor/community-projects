# Builder Brief: openminion/openminion

**OpenMinion 0.1.23 just released with configuration and CLI improvements; security audit issue remains critical**

## Releases
- [LOW] [0.1.23](https://github.com/openminion/openminion/releases/tag/0.1.23): Adds `openminion config diff` for previewing imports, preserves provider finish reasons (e.g., `length`, `content_filter`), creates Playwright artifact dirs only on first browser use, improves CLI error handling, and packs verified runtime binaries.
- [LOW] [0.1.22](https://github.com/openminion/openminion/releases/tag/0.1.22): Minor bug fixes and performance tweaks (details truncated).

## Issues to watch
- [LOW] [memctl: derive the default config when the implicit default memory.yaml is absent](https://github.com/openminion/openminion/pull/815): Apply patch or add a default `memory.yaml` before running memctl
- [HIGH] [security audit: approval binding holds and guards fail closed, but PII sits in 0644 stores and approval/rollback events are missing](https://github.com/openminion/openminion/issues/642): Address PII permissions, add missing audit logs for approval/rollback, review guard logic, and submit a fix

## Actions
- Validate the new release in your CI pipeline.
- Run `openminion config diff <file>` to confirm configuration diff behavior.
- Apply PR #815 locally (ensure a default memory configuration).
- Prioritize resolving issue #642; assign to the security maintainer and add logging for approval/rollback events.
- Monitor future releases for any potential breaking changes such as migration of tool artifacts or configuration semantics.

<sub>run_id=f1cf3fd1d4be4961b936133dc6a735d0 session=minion-radar:openminion__openminion-json state=completed</sub>
