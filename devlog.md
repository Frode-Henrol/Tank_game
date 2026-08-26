# Tank Game — Devlog Commit Shortlist

Scanned all 258 commits (2025-02-18 → 2026-08-26, single branch history). Below is a curated,
chronological shortlist grouped into "chapters" that could each be a segment of a devlog video.
Picked using commit-message keywords ("add", "new", milestone words) + diff size (big
insertion/deletion counts = likely a visible feature, not a tweak). Pure "update"/"fix typo"/README
churn commits are filtered out except where they mark a chapter boundary.

Legend: `hash` `date` — message — *why it's video-worthy*

---

## Chapter 1 — Genesis (Feb 2025)
The very first prototype. Good for a "where it all began" cold open.

- `c5286cb` 2025-02-18 — "tes" — **first commit in the repo**
- `0452076` 2025-02-20 — "New deflect func" — core mechanic prototyping
- `f667d86` 2025-02-20 — "Deflect virker ok, men dog mange der flyver gennem" — early Danish commit messages, deflect mechanic mostly working
- `044a089` 2025-02-22 — "Store forbedringer" (big improvements) — 176 insertions
- `a4b0990` 2025-02-22 — "tankgame class + making game not FPS bound" — architecture foundation, 596 insertions
- `3b9844b` 2025-02-22 — "New simple map editor" — first map editor
- `81645e2` 2025-02-22 — "Map gen works roughly" — first working map generation
- `9a65b17` 2025-02-25 — "New 3d render folder and content" — **abandoned 3D detour**, worth a "what if" beat
- `37a3c88` 2025-03-02 — "3D model rendering works. Rough state" — last trace of the 3D experiment before it was dropped for 2D

## Chapter 2 — Core Loop & Map Editor (Mar 2025)
- `c66866a` 2025-03-06 — "New folder struture" — first big reorg, 489 insertions/900 deletions
- `22ec29e` 2025-03-06 — "Simple gui made" — first GUI, 347 insertions
- `b81c412` 2025-03-06 — "Quick play feature added"
- `7d98979` 2025-03-06 — "first step toward ai" — **AI seed commit**
- `5627821` 2025-03-10 — "new unit folder + rotating turret logic no visuals" — turret rotation groundwork
- `3e397aa` 2025-03-10 — "menu added to map editor" — 37 files touched, editor UI grows
- `26032dc` 2025-03-11 — "New button features"
- `76ef512` 2025-03-12 — "e" — 632 insertions despite the throwaway message, worth checking diff
- `6ff3d8e` 2025-03-12 — "New countdown feature when pressing play"
- `2527a51` 2025-03-13 — "Made textfield class"
- `a7b9322` 2025-03-13 — "Triangle point checker function" — 266 insertions, geometry groundwork

## Chapter 3 — Pathfinding System (Mar 2025, ~2 week arc)
Clean self-contained arc: 0% → 100% in commit messages, good for a montage.
- `966c84c` 2025-03-20 — "Path finding test script done" — 558 insertions
- `0ced695` 2025-03-25 — "pathfinding 25% done"
- `8155200` 2025-03-25 — "pathfinding 99% works fine"
- `e2dd935` 2025-03-27 — "Added pathfinding debug to tankgame" — 155 insertions, likely has a visual debug overlay — **good screenshot candidate**
- `5cb80c1` 2025-03-27 — "path nodes setting in map_maker added"

## Chapter 4 — AI Buildout (Late Mar – Apr 2025)
The AI goes from nothing to a full state machine. Great montage material — the commit messages
themselves read like a progress bar.
- `ebf9f16` 2025-03-31 — "add/fix: settings, godmode, debug + tanks"
- `68d1b86` 2025-04-04 — "add: ai features"
- `0f39ba0` 2025-04-05 — "add: all states besides dodge added" — state machine nearly complete
- `d8f7c5e` 2025-04-05 — "add: 99% done dodge state"
- `6b8e90c` 2025-04-05 — "ai 99.999%" — funny milestone commit, good for a quick laugh cut
- `8034d45` 2025-04-05 — "add: wall bounce predict feature 100%" — AI predicts ricochets
- `8fc5185` 2025-04-03 — "add: big overhaul of the ai class: rewritten" — 973 insertions, major rewrite
- `91ed2e5` 2025-04-06 — "predict function added"
- `c83c2ca` 2025-04-12 — "Added projectile prediction for ai defense"
- `6b99bea` 2025-04-12 — "Mine dodge for ai" — AI reacts to mines

## Chapter 5 — Performance Overhaul (Apr 2025)
Good for a "the game was chugging, here's how it got fixed" segment — pair with an FPS counter overlay if you have old footage/screenshots.
- `67292b9` 2025-04-16 — "rework: game logic no longer fps bounds"
- `8321e57` 2025-04-16 — "ai not fps bound. Logic runs 60hz"
- `bc4e188` 2025-04-16 — "replace pygame timing with perf"
- `917bb2f` 2025-04-16 — "major performence upgrades" — 1041 insertions, the big one
- `87117d7` 2025-04-17 — "line_intersection func rewritten with cython" — notable engineering flex, worth calling out on screen

## Chapter 6 — Visual & Audio Polish (Apr 2025)
This is probably your best-looking b-roll chapter — explosions, muzzle flash, tracks, sound.
- `c39e04b` 2025-04-14 — "Custome tank images added for all tanks" — every tank gets unique art
- `c097fb5` 2025-04-14 — "custom ai for 9 tanks" — 292 insertions
- `7559b5a` 2025-04-14 — "new sound effects added"
- `665623f` 2025-04-14 — "simpel muzzle flash logic added"
- `300e7ae` 2025-04-14 — "fading tank track added" — nice small visual detail
- `1bc52b1` 2025-04-15 — "add: explosion effect" — 1006 insertions/1488 deletions, big visual rewrite
- `1b97b99` 2025-04-15 — "map textures added"
- `b429078` 2025-04-03 — "New turret graphics"

## Chapter 7 — Mines, Dodge & Obstacles (Apr 2025)
- `5aae9c3` 2025-04-09 — "add: mine class" — mine system seed
- `1726a95` 2025-04-11 — "mines added"
- `fafcd18` 2025-04-27 — "advanced dodge added"
- `b3a9056` 2025-04-27 — "Advanded dodge fully implemented"
- `2c7c2b6` 2025-04-24 — "test of texture des" — obstacle texture pass, 193 insertions
- `70fe6ad` 2025-04-27 — "updated and fixed textures for obstacles"

## Chapter 8 — Content Expansion (Apr–May 2025)
- `dec5c8b` 2025-05-01 — "10 new tank types" — 451 insertions, big content drop
- `4d080e5` 2025-05-03 — "+ 50 maps and victory screen" — **1506 insertions, the single biggest content commit in the whole history**
- `986629f` 2025-04-30 — "added ekstra life per 5 rounds won" — new mechanic
- `86811ea` 2025-04-29 — "visual upgrades to level screen"

## Chapter 9 — The Big Refactor (May 2025)
- `b3c076e` 2025-05-04 — "rotate start fix and refactor of files" — 6336 deletions, major cleanup
- `8aa14e3` 2025-05-12 — "complete refactor of package + multiplayer menu" — **275 files touched**, this is the repo restructure that set the stage for multiplayer

## Chapter 10 — Multiplayer: First Attempt (May 2025)
This is a full narrative arc on its own — from "test method for udp" to "simple 2 player mode works
locally" to sync bugs to it going quiet. Could be its own dedicated video segment.
- `62eaa5e` 2025-05-12 — "Local host-client connection test succes" — 183 insertions, first successful connection
- `073eed0` 2025-05-13 — "Simple MP test with tank pos done" — first synced position
- `b438291` 2025-05-14 — "Simple driving,rotation,shoot sync test added"
- `35f6773` 2025-05-14 — "Simple lobby layout with primitive usernames" — first lobby UI
- `f7a6f4b` 2025-05-14 — "player 2 and 3 tank and rename player - player1"
- `1215d4e` 2025-05-15 — "3 players added, ai can also target them"
- `05c6213` 2025-05-17 — "simple 2 player mode works locally over udp" — **406 insertions, milestone: MP works locally**
- `e2ba7b7` 2025-05-17 — "fixed turretrotation client->host->client" — sync bug fixing begins
- `79cdff4` 2025-05-18 — "shot_Fired bool -> int counter" — sync bug fix attempt
- `4ab81be` 2025-05-18 — "shot sync problems still not fixed" — **honest "still broken" commit, good storytelling beat before the hiatus**
- `0a7e053` 2025-05-21 — "broken mp" — last commit before the long quiet stretch

## The Gap (Sep 2025 → Aug 2026, ~11.5 months)
Nothing but README/doc churn from May 21 to Sep 4, 2025, then **no commits at all until
2026-08-25**. This is a genuinely good story beat for the video: multiplayer got shelved half-working, project went quiet for almost a year, then came back specifically to finish it.

## Chapter 11 — Multiplayer: The Return (Aug 25–26, 2026, i.e. yesterday/today)
The revival arc — picks up exactly where it left off and actually finishes the job. This is your
strongest "recent" material since it's freshest and most testable live.
- `ade6454` 2026-08-25 — "new control setting" — first commit back after the hiatus
- `40ae9a6` 2026-08-26 — "multiplayer test" — 625 insertions/532 deletions, MP work resumes in earnest
- `41253f1` 2026-08-26 — "added multiplayer for singleplayer maps" — **454 insertions, big milestone: existing SP maps become playable in MP**
- `ee20394` 2026-08-26 — "fixed menu not closing socket" — 238 insertions
- `bccca37` 2026-08-26 — "fixes for lobby" — 153 insertions
- `6c32454` 2026-08-26 — "harden multiplayer connection: thread-safety + clean reconnect" — engineering-maturity beat, good to narrate
- `6a0cb46` 2026-08-26 — "fix: client stuck in lobby forever if it misses game-start message" — 189 insertions
- `84d0b4d` 2026-08-26 — "fix actual root cause: client_handle_level_result() was unreachable" — nice "found the real bug" beat
- `7debc24` 2026-08-26 — "fix crash on rejoining after a match ends (IndexError)" — **most recent commit, natural "present day" endpoint for the video**

---

## Suggested video structure
1. **Cold open**: show the game running today (multiplayer working), then cut to `c5286cb`/first prototype for contrast.
2. **Chapters 1–2**: fast montage, prototype era, mostly text/log overlay since there's little to show visually yet.
3. **Chapter 3 (pathfinding) + Chapter 4 (AI)**: your best "systems getting smart" narrative — consider checking out `e2dd935` for the pathfinding debug overlay if it draws anything on screen.
4. **Chapter 5 (performance) + Chapter 6 (visual/audio polish)**: strongest visual b-roll chapter, lean on it.
5. **Chapters 7–9**: content growth + the big refactor as a "growing pains" beat.
6. **Chapter 10 (first MP attempt) → The Gap → Chapter 11 (MP return)**: the emotional arc of the video — built something, it broke, shelved it, came back and fixed it. This is probably your closing act.

## Next steps if useful
- I can check out specific commits and run the game to grab actual screenshots/footage for the ones flagged above, if you tell me which chapters you want to prioritize.
- If you have a rough total runtime in mind, I can trim this list down further per chapter.
