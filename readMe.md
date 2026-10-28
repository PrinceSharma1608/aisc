# Chess Arena

Chess Arena is a Windows desktop application built with Pygame, `python-chess`, and a bundled Stockfish executable. It has two modes:

- **Play with AI:** play White against Stockfish. Click a piece, then a highlighted legal square. The game panel shows SAN move history, check and terminal status, material balance, and the latest move. Undo removes the last move pair when available.
- **Algorithm Comparison:** compare the project's own plain Minimax and Alpha-Beta implementations. Both search the same position at the same depth with the same evaluation and deterministic move ordering. Choose the standard position, a small endgame preset, or enter a valid FEN. Click a visible tree node to inspect its type, ply, score, alpha/beta bounds, and cutoff status.
- **Parallel self-play:** from Algorithm Comparison, choose **Play full games** to see two live boards. Minimax plays both colors on one board and Alpha-Beta plays both colors on the other, from the exact same selected start position. The boards advance from real search results. Per-algorithm visited nodes, leaf evaluations, cutoffs, skipped moves, and elapsed search time accumulate across moves, while current-search counts update as the workers run. Stop or reset the games at any time.

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
