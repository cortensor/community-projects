# Minion Radar demo script (1 to 4 minutes)

A recorded demo from the 22 Nov 2026 real Portal run is in [`demo/minion-radar-demo.mp4`](../demo/minion-radar-demo.mp4), with a spoken script in [`demo/VOICEOVER.md`](../demo/VOICEOVER.md). The notes below remain the recording guide if you want a second take.

Record a short screen video of a real Cortensor Portal run. Speak in plain English. Do not read out any API key. The key stays in the ignored `.env` file.

Target length: about 1 to 4 minutes of talking after you trim the quiet model wait. A timed film run on 21 Nov 2026 took 3 minutes 47 seconds end to end in WAT (Africa/Lagos). The snapshot appears almost at once. Nearly all of the remaining time is hosted model latency, often around 2 to 4 minutes. Keep recording, then trim the quiet wait in the editor.

Times below are in WAT (Africa/Lagos).

## Before you hit record

1. Join the official Cortensor Discord from your phone if you have not already. You may need that later for the Hackathon 5 submission repo.
2. On the recording machine, open a terminal in the Minion Radar folder, with the virtual environment on:
   `source .venv/bin/activate`
3. Confirm `.env` has `CORTENSOR_API_KEY` already set. Do not open or share that file on camera.
4. Optional warmup, off camera: `openminion setup --provider cortensor-portal --model oss-20b --agent radar --no-chat --check-provider`

## Command to run on camera

```bash
python -m minion_radar --repo openminion/openminion --film --out samples
```

`--film` uses a compact repo snapshot, the real `oss-20b` model, and auto approves the checkpoint the same way `--yes` does.

## What you will see

1. Right away: a short film mode note, then `[tool] radar_snapshot: 3 new releases, 8 new issues` (counts may change).
2. A quiet wait while Cortensor Portal `oss-20b` runs. On the 21 Nov 2026 timed run this was most of the 3 minutes 47 seconds.
3. Then, together: `[approval] auto approved radar_save_checkpoint (--yes)` and the Builder Brief.

## What to say

Keep these spoken lines free of hyphen characters.

**Opening, while the command is visible (about 20 seconds):**
"This is Minion Radar, an Open Minion agent for Cortensor Hackathon 5. It tells a builder what changed in a repo since they last looked. I am running it live on the Open Minion GitHub repo, using the Cortensor Portal oss 20b model."

**Right after you press enter, when the snapshot line appears (about 15 seconds):**
"There is the snapshot tool. That is live GitHub data, not a fixture. Next the hosted model writes a short builder brief, then the agent saves a checkpoint. That checkpoint is a local write, so Open Minion asks for approval. This film mode auto approves it so the step is visible on screen."

**While the terminal is quiet:**
"The hosted model can take a few minutes. The tools themselves are quick. Almost all of the wait is model latency. I will keep the terminal in view until the brief appears."

**When you see `[approval] auto approved radar_save_checkpoint`:**
"And there is the approval step. The next run will only show items newer than this checkpoint."

**When the Builder Brief prints (about 45 to 60 seconds):**
"Here is the brief. It has a headline, the latest releases with a risk level, issues worth watching, and concrete actions. The release links keep the official GitHub tag, including the leading v when GitHub uses one."
Point at one real item, for example release v0.1.23 or issue 642, and say it out loud.

**Close (about 15 seconds):**
"That is a full real model run with the Open Minion SDK: tools, structured output, a session, and an approved memory write. Setup is in the README. Thanks for watching."

## If something is slow or messy

- If the run takes more than about three minutes, keep recording the output and trim the quiet wait in the editor. Do not stop before the brief and the approval line appear.
- The approval line may appear just before the brief. That is still a real checkpoint save. Say the approval line anyway.
- If the brief is labelled film mode and looks a little generic, that can happen when the model echoes the snapshot and Minion Radar falls back to a rule based brief from the same live data. The versions, links, and approval step are still real. You can still point at those.
- If the command fails, do not improvise a fake run. Switch to `--no-model` only to show the shape of a brief, and say clearly that it is rule based, not a model run. Then retry the film command off camera and record a second take.

## What not to show

- The `.env` file, any API key, or the Open Minion config if it might contain a secret.
- Wallet screens, Discord, or payment pages.
- A `--demo` run presented as the real model demo. `--demo` is labelled simulated and uses no model.
