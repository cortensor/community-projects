# Project Status – Minion Radar

**Maintainer:** @ajahelube
**Current Version:** v0.1.0
**Status:** Active

## Current State

- Working OpenMinion 0.1.23 agent with 18 passing tests.
- Real Cortensor Portal `oss-20b` film run on 22 Nov 2026, 9:35:24 AM to 9:39:34 AM WAT (Africa/Lagos), origin `model_generated`, checkpoint auto approved.
- README includes the Hackathon #5 required sections: workflow, example, Building Blocks Tested, and What We Learned.

## Next Steps

- Standalone public repository: https://github.com/ajahelube/minion-radar
- Replace the demo video placeholder in the README once the voiced version is published, then open the Hackathon #5 pull request.

## Known Issues

- Cortensor Portal can take several minutes per turn and may raise `PROVIDER_ERROR`.
- OpenMinion session ids that contain `/` raise `invalid scope`; Minion Radar replaces `/` with `__`.
- Exact official Hackathon #5 submission repository is still unpublished; this PR targets `cortensor/community-projects` following other builders, which official docs have not named as the dedicated repo.
