import app from "./server";
import { PORT } from "./utils/env";
import { startPhase3_2 } from "./phases/phase3_2";

// Start Phase 3.2 (trusted claim ingestion)
startPhase3_2();

app.listen(PORT, () => console.log(`Backend running on :${PORT}`));
