# Chess Arena

Chess Arena is a Windows desktop application built with Pygame, `python-chess`, and a bundled Stockfish executable. It has two modes:

- **Play with AI:** choose Easy (depth 2), Medium (depth 6), or Hard (depth 10) before starting. Every new game begins from the standard chess position, with all pieces on their home squares. Play by clicking a piece and a highlighted legal square, or press **Space** / click **Minimax move** to let the custom Minimax algorithm choose White's move. Stockfish chooses randomly among near-best candidate moves, so its play can vary from game to game while each move remains legal. Difficulty controls Stockfish search depth; it is not a guaranteed Elo rating. **Simulate result** hands the current position to Stockfish on both sides at depth 2 and fast-forwards to a natural result; it can be stopped after the current engine move. While Minimax searches, the right panel diagrams up to nine legal candidate moves, highlights the chosen move, and plays it after a brief review. The panel also shows search progress, SAN move history, check and terminal status, and material balance. Undo removes the last move pair when available.
- **Algorithm Comparison:** compare the project's own plain Minimax and Alpha-Beta implementations. Each new comparison position is a fresh, legally reached endgame with five or six pieces, generated through random play and checked to avoid an immediate forced mate. Both boards preview the same position before the game starts. Click a visible tree node to inspect its type, ply, score, alpha/beta bounds, and cutoff status. Use **New random position** to generate another endgame.
- **Visualized game:** choose **Visualize game** from Algorithm Comparison. The demo searches at depth 2. Before each search, both boards show every legal destination, grouped piece by piece; then each board animates the actual recursive positions visited by its algorithm. Alpha-Beta skips pruned branches, so its live numeric node, leaf, cutoff and pruned counts update independently from Minimax. The matching bars under both boards show the same actual game elapsed time; each panel's numeric total search time shows its algorithm's own runtime. Both algorithms analyze the same position at each turn and Minimax's best move advances the shared game after the scores agree. A natural checkmate or draw ends the game; Stop games remains available during long games.

The comparison dashboard reports evaluated leaves separately from visited nodes. Red markers show legal moves skipped after a recorded Alpha-Beta cutoff. Large traces are fully counted but only a visible prefix is drawn. Progress reports actual trace-node/leaf counts; it does not estimate a completion percentage. Search depth 4 may take noticeably longer on a midgame position.

Stockfish difficulty and comparison depth are available from **Settings**. Stockfish depth is a search setting, not an Elo rating. Positive custom-search evaluations favor White; negative evaluations favor Black. Ordinary scores are centipawns, while mate scores use a separate large range.

## Run

From PowerShell in the project folder:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Run the algorithm regression checks:

```powershell
.\.venv\Scripts\python.exe .\test_comparison.py
```

Run the game-state helper checks:

```powershell
.\.venv\Scripts\python.exe .\test_game.py
```

Verify Stockfish candidate analysis:

```powershell
.\.venv\Scripts\python.exe .\ai.py
```

The Stockfish executable is resolved relative to `ai.py`; it does not need to be installed globally. `python-chess` and Pygame should be installed in `.venv`.

## Search metric definitions

- **Visited nodes:** root, explored move nodes, and evaluated leaves. Pruned markers are excluded.
- **Leaf evaluations:** positions where the shared evaluator or terminal scoring is applied.
- **Cutoffs:** Alpha-Beta nodes where the alpha/beta bound made remaining ordered moves irrelevant.
- **Pruned moves:** legal moves omitted after those cutoffs. This is not a count of fully searched subtrees.
- **Node reduction:** reduction in leaf evaluations relative to Minimax for this exact position and depth. Runtime varies by machine and run.
