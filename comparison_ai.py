"""Compare plain Minimax and Alpha-Beta using the same evaluation and move order."""
from __future__ import annotations
import time
import chess

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0,
}
MATE_SCORE = 100_000


def evaluate(board: chess.Board, ply: int = 0) -> int:
    """Static score from White's perspective, in centipawns."""
    if board.is_checkmate():
        return -MATE_SCORE + ply if board.turn == chess.WHITE else MATE_SCORE - ply
    if board.is_game_over(claim_draw=True):
        return 0
    score = 0
    for sq, piece in board.piece_map().items():
        value = PIECE_VALUES[piece.piece_type]
        rank = chess.square_rank(sq)
        if piece.piece_type == chess.PAWN:
            advance = rank if piece.color == chess.WHITE else 7 - rank
            value += advance * 7
        if piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            file_c = abs(chess.square_file(sq) - 3.5)
            rank_c = abs(rank - 3.5)
            value += int(18 - 4 * (file_c + rank_c))
        score += value if piece.color == chess.WHITE else -value
    return score


def _ordered_moves(board: chess.Board):
    def priority(move):
        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            score += 10_000 + 10 * PIECE_VALUES[victim.piece_type] - (PIECE_VALUES[attacker.piece_type] if attacker else 0) if victim else 10_000
        if move.promotion:
            score += 8_000 + PIECE_VALUES[move.promotion]
        if board.gives_check(move):
            score += 500
        return score
    return sorted(list(board.legal_moves), key=priority, reverse=True)


def _trace_node(nodes, parent, depth, kind, san="", score=None, alpha=None, beta=None):
    node_id = len(nodes)
    nodes.append({"id": node_id, "parent": parent, "depth": depth, "kind": kind,
                  "san": san, "score": score, "alpha": alpha, "beta": beta})
    return node_id


def _search(board, depth, algorithm, progress=None):
    nodes, edges = [], []
    counters = {"visited": 1, "evaluated": 0, "cutoffs": 0, "pruned_moves": 0}
    root = _trace_node(nodes, None, 0, "root", "ROOT")
    alpha_beta = algorithm == "alpha_beta"

    def visit(d, alpha, beta, parent_id, ply):
        if progress and (len(nodes) & 255) == 0:
            progress(counters["visited"], counters["evaluated"], counters["cutoffs"], counters["pruned_moves"])
        if d == 0 or board.is_game_over(claim_draw=True):
            value = evaluate(board, ply)
            counters["evaluated"] += 1
            leaf = _trace_node(nodes, parent_id, ply, "leaf", "Leaf", value, alpha, beta)
            counters["visited"] += 1
            edges.append((parent_id, leaf))
            return value
        maximizing = board.turn == chess.WHITE
        best = -float("inf") if maximizing else float("inf")
        moves = _ordered_moves(board)
        if not moves:
            value = evaluate(board, ply)
            counters["evaluated"] += 1
            leaf = _trace_node(nodes, parent_id, ply, "leaf", "Terminal", value, alpha, beta)
            counters["visited"] += 1
            edges.append((parent_id, leaf))
            return value
        for index, move in enumerate(moves):
            san = board.san(move)
            child = _trace_node(nodes, parent_id, ply, "move", san, None, alpha, beta)
            counters["visited"] += 1
            nodes[child]["alpha"], nodes[child]["beta"] = alpha, beta
            edges.append((parent_id, child))
            board.push(move)
            try:
                value = visit(d - 1, alpha, beta, child, ply + 1)
            finally:
                board.pop()
            nodes[child]["score"] = value
            if maximizing:
                best = max(best, value)
            else:
                best = min(best, value)
            if alpha_beta:
                if maximizing:
                    alpha = max(alpha, best)
                else:
                    beta = min(beta, best)
                if alpha >= beta and index < len(moves) - 1:
                    counters["cutoffs"] += 1
                    nodes[parent_id]["cutoff"] = True
                    nodes[parent_id]["alpha"], nodes[parent_id]["beta"] = alpha, beta
                    for skipped in moves[index + 1:]:
                        skipped_san = board.san(skipped)
                        pruned = _trace_node(nodes, parent_id, ply, "pruned", skipped_san, None, alpha, beta)
                        edges.append((parent_id, pruned))
                        counters["pruned_moves"] += 1
                    break
        nodes[parent_id]["score"] = best
        nodes[parent_id]["alpha"], nodes[parent_id]["beta"] = alpha, beta
        return best

    start = time.perf_counter()
    best_move, best_score = None, None
    moves = _ordered_moves(board)
    if not moves:
        best_score = evaluate(board)
        counters["evaluated"] += 1
        counters["visited"] += 1
        leaf = _trace_node(nodes, root, 0, "leaf", "Terminal", best_score)
        edges.append((root, leaf))
    else:
        maximizing = board.turn == chess.WHITE
        best_score = -float("inf") if maximizing else float("inf")
        alpha, beta = -float("inf"), float("inf")
        for index, move in enumerate(moves):
            san = board.san(move)
            child = _trace_node(nodes, root, 1, "move", san, None, alpha, beta)
            counters["visited"] += 1
            nodes[child]["alpha"], nodes[child]["beta"] = alpha, beta
            edges.append((root, child))
            board.push(move)
            try:
                value = visit(depth - 1, alpha, beta, child, 2)
            finally:
                board.pop()
            nodes[child]["score"] = value
            if best_move is None or (value > best_score if maximizing else value < best_score):
                best_score, best_move = value, move
            if alpha_beta:
                if maximizing:
                    alpha = max(alpha, best_score)
                else:
                    beta = min(beta, best_score)
                nodes[root]["alpha"], nodes[root]["beta"] = alpha, beta
                if alpha >= beta and index < len(moves) - 1:
                    counters["cutoffs"] += 1
                    nodes[root]["cutoff"] = True
                    nodes[root]["alpha"], nodes[root]["beta"] = alpha, beta
                    for skipped in moves[index + 1:]:
                        skipped_san = board.san(skipped)
                        pruned = _trace_node(nodes, root, 1, "pruned", skipped_san, None, alpha, beta)
                        edges.append((root, pruned))
                        counters["pruned_moves"] += 1
                    break
    nodes[root]["score"] = best_score
    elapsed = time.perf_counter() - start
    return {"algorithm": algorithm, "best_move": best_move.uci() if best_move else None,
            "best_move_san": board.san(best_move) if best_move else "—",
            "best_score": int(best_score),
            "nodes_visited": counters["visited"],
            "leaf_nodes_evaluated": counters["evaluated"],
            # Retain this field for callers written against the earlier interface.
            "nodes_evaluated": counters["evaluated"],
            "cutoffs": counters["cutoffs"], "pruned_moves": counters["pruned_moves"],
            "elapsed": elapsed, "nodes": nodes, "edges": edges}


def run_comparison(position=None, depth=3, progress=None):
    if not isinstance(depth, int) or depth < 1 or depth > 4:
        raise ValueError("Depth must be an integer between 1 and 4.")
    board = position.copy(stack=True) if isinstance(position, chess.Board) else chess.Board()
    def report(label):
        if progress:
            return lambda visited, leaves, cutoffs, pruned: progress(label, visited, leaves, cutoffs, pruned)
        return None
    if progress:
        progress("Minimax", 0, 0, 0, 0)
    minimax = _search(board.copy(stack=True), depth, "minimax", report("Minimax"))
    if progress:
        progress("Alpha-Beta", 0, 0, 0, 0)
    alpha_beta = _search(board.copy(stack=True), depth, "alpha_beta", report("Alpha-Beta"))
    mn, ab = minimax["nodes_evaluated"], alpha_beta["nodes_evaluated"]
    reduction = ((mn - ab) / mn * 100.0) if mn else 0.0
    summary = {
        "minimax_nodes": mn, "alpha_beta_nodes": ab,
        "minimax_visited_nodes": minimax["nodes_visited"],
        "alpha_beta_visited_nodes": alpha_beta["nodes_visited"],
        "pruned_moves": alpha_beta["pruned_moves"],
        "node_reduction_percent": reduction,
        "minimax_time": minimax["elapsed"], "alpha_beta_time": alpha_beta["elapsed"],
        "same_score": minimax["best_score"] == alpha_beta["best_score"],
        "same_best_move": minimax["best_move"] == alpha_beta["best_move"],
    }
    return {"minimax": minimax, "alpha_beta": alpha_beta, "summary": summary, "depth": depth}


class SearchCancelled(Exception):
    """Raised by a progress callback to stop an in-flight custom search."""


def search_position(position: chess.Board, depth: int, algorithm: str, progress=None):
    """Run one algorithm on a copied position; progress receives actual search counters."""
    if not isinstance(depth, int) or depth < 1 or depth > 4:
        raise ValueError("Depth must be an integer between 1 and 4.")
    if algorithm not in ("minimax", "alpha_beta"):
        raise ValueError("Algorithm must be 'minimax' or 'alpha_beta'.")
    board = position.copy(stack=True)
    if progress:
        progress(0, 0, 0, 0)
    return _search(board, depth, algorithm, progress=progress)


def parse_fen(fen: str) -> chess.Board:
    """Parse a FEN and reject syntactically or positionally invalid boards."""
    try:
        board = chess.Board(fen.strip())
    except (ValueError, TypeError, IndexError) as exc:
        raise ValueError(f"Invalid FEN: {exc}") from exc
    if not board.is_valid():
        raise ValueError("Invalid FEN: the position is not legally valid.")
    return board


if __name__ == "__main__":
    result = run_comparison(depth=3)
    for label, key in (("MINIMAX", "minimax"), ("ALPHA-BETA", "alpha_beta")):
        item = result[key]
        print(f"\n{label}: best={item['best_move_san']} ({item['best_score']} cp), leaves={item['nodes_evaluated']}, time={item['elapsed']:.3f}s, cutoffs={item['cutoffs']}, pruned={item['pruned_moves']}")
    print("Same score:", result["summary"]["same_score"])
