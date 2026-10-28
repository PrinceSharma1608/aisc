# Chess Arena

Chess Arena is a Windows desktop application built with Pygame, `python-chess`, and a bundled Stockfish executable. It has two modes:

- **Play with AI:** choose Easy (depth 2), Medium (depth 6), or Hard (depth 10) before starting, then play White against Stockfish by clicking a piece and a highlighted legal square, or press **Space** / click **Minimax move** to let the custom Minimax algorithm choose White's move. Difficulty controls Stockfish search depth; it is not a guaranteed Elo rating. **Simulate result** hands the current game to Stockfish on both sides at depth 2 and fast-forwards to a natural result; you can stop after the current move. While Minimax searches, the right panel diagrams up to nine legal candidate moves with their scores, highlights the chosen move, and plays it after a brief review. The panel also shows search progress, SAN move history, check and terminal status, and material balance. Undo removes the last move pair when available.
- **Algorithm Comparison:** compare the project's own plain Minimax and Alpha-Beta implementations. Comparison mode prepares a fresh randomized 7–9-piece tactical position with a mate in one. Both boards preview the same position before the game starts. Generate another position or enter a valid FEN for analysis. Click a visible tree node to inspect its type, ply, score, alpha/beta bounds, and cutoff status.
- **Visualized game:** choose **Visualize game** from Algorithm Comparison. The demo searches at depth 2. Before each search, both boards show every legal destination, grouped piece by piece; then each board animates the actual recursive positions visited by its algorithm. Alpha-Beta skips pruned branches, so its live node and pruned-move bars update independently from Minimax and its panel reports its completion time. Separate move bars track the shared game under each board. Both searches must agree before the best move advances the game. The mate-in-one setup ends the demo promptly. **New position** returns to the dashboard with a fresh tactical position for preview before the next start.

The comparison dashboard reports evaluated leaves separately from visited nodes. Red markers show legal moves skipped after a recorded Alpha-Beta cutoff. Large traces are fully counted but only a visible prefix is drawn. Progress reports actual trace-node/leaf counts; it does not estimate a completion percentage. Search depth 4 may take noticeably longer on the starting position.

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
