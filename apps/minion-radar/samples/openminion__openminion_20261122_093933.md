# Builder Brief: openminion/openminion

> MODEL GENERATED: compact live snapshot, real model brief, checkpoint auto approved.

**OpenMinion 0.1.24 adds multimodal input (image/screenshot) and strengthens provider retry behavior while addressing storage migration issues**

## Releases
- [LOW] [v0.1.24: 0.1.24](https://github.com/openminion/openminion/releases/tag/v0.1.24): OpenMinion 0.1.24 adds multimodal input and strengthens tool, memory, provider, and remote-execution behavior.

## Issues to watch
- [MEDIUM] [446](https://github.com/openminion/openminion/issues/446): PostgreSQL storage migrate modules share one alembic_version causing runtime storage failures on sessions
- [MEDIUM] [717](https://github.com/openminion/openminion/issues/717): Provider retry ignores Retry‑After on HTTP 429 causing turns to terminate prematurely

## Actions
- Deploy release v0.1.24
- Verify provider retry logic honors Retry‑After
- Apply fix for shared alembic_version in storage migration
- Monitor the open issues 446 and 717 after deployment

<sub>origin=model_generated run_id=None session=minion-radar:openminion__openminion-film2 state=model_generated</sub>
