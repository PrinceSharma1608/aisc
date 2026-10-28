# Chess Arena

Chess Arena is a Windows desktop application built with Pygame, `python-chess`, and a bundled Stockfish executable. It has two modes:

- **Play with AI:** play White against Stockfish by clicking a piece and a highlighted legal square, or press **Space** / click **Minimax move** to let the custom Minimax algorithm choose White's move. While searching, the right panel diagrams up to ten candidate moves with their scores, highlights the chosen move, and plays it after a brief review. The panel also shows search progress, SAN move history, check and terminal status, and material balance. Undo removes the last move pair when available.
- **Algorithm Comparison:** compare the project's own plain Minimax and Alpha-Beta implementations. Each time you enter comparison mode, it selects a fresh randomized three-piece queen endgame with a mate in one, so the visualized game ends quickly. The dashboard shows the exact shared position on both boards before the game starts. Choose the standard start, generate another near-mate position, select the king-and-pawn endgame, or enter a valid FEN. Click a visible tree node to inspect its type, ply, score, alpha/beta bounds, and cutoff status.
- **Visualized game:** from Algorithm Comparison, choose **Visualize game**. Before each search, both boards show every legal destination, grouped piece by piece. Minimax and Alpha-Beta then animate their recursive branches concurrently at a slower pace. Each pane shows its current board, SAN line, and alpha/beta bounds. A shared bar beneath the boards counts the moves played. When both searches finish with matching scores, Minimax's selected move advances the shared game. Per-algorithm visited nodes, leaf evaluations, cutoffs, skipped moves, and search time accumulate throughout the game. Stop or reset at any time.

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
