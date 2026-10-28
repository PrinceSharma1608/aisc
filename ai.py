
from pathlib import Path
import chess
import chess.engine

PROJECT_DIR = Path(__file__).resolve().parent
STOCKFISH_PATH = PROJECT_DIR / "stockfish-windows-x86-64-universal.exe"


def analyze_candidates(board: chess.Board, depth: int = 10, multipv: int = 3):
    """Return candidate move dictionaries with SAN, score and principal variation."""
    if not STOCKFISH_PATH.is_file():
        raise FileNotFoundError(f"Stockfish executable not found: {STOCKFISH_PATH}")
    if board.is_game_over(claim_draw=True):
        return []
    multipv = max(1, min(int(multipv), board.legal_moves.count()))
    engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_PATH))
    try:
        infos = engine.analyse(board, chess.engine.Limit(depth=max(1, int(depth))), multipv=multipv)
        if isinstance(infos, dict):
            infos = [infos]
        candidates = []
        for info in infos:
            pv = info.get("pv", [])
            if not pv:
                continue
            move = pv[0]
            score_obj = info["score"].pov(board.turn)
            mate = score_obj.mate()
            score = score_obj.score(mate_score=100000)
            temp = board.copy(stack=False)
            san = temp.san(move)
            pv_san = []
            for pv_move in pv:
                pv_san.append(temp.san(pv_move))
                temp.push(pv_move)
            candidates.append({"move": move, "san": san, "score": score, "mate": mate,
                               "pv": pv_san})
        return candidates
    finally:
        engine.quit()


def get_best_move(board: chess.Board, depth: int = 10):
    candidates = analyze_candidates(board, depth=depth, multipv=1)
    return candidates[0]["move"] if candidates else None


def choose_move(board: chess.Board, depth: int = 10):
    """Compatibility helper returning (best move, centipawn score)."""
    candidates = analyze_candidates(board, depth=depth, multipv=1)
    if not candidates:
        return None, None
    return candidates[0]["move"], candidates[0]["score"]


if __name__ == "__main__":
    print("Testing Stockfish integration...")
    print(f"Engine: {STOCKFISH_PATH.name}")
    board = chess.Board()
    for index, item in enumerate(analyze_candidates(board, depth=10, multipv=3), start=1):
        score = f"mate in {item['mate']}" if item["mate"] is not None else f"{item['score'] / 100:+.2f}"
        print(f"{index}. {item['san']} | evaluation {score} | PV: {' '.join(item['pv'][:8])}")
