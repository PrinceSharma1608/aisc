"""Regression checks for the custom chess search comparison."""
import chess

from comparison_ai import SearchCancelled, parse_fen, run_comparison, search_position


def test_standard_position_and_trace():
    board = chess.Board()
    before = board.fen()
    result = run_comparison(board, depth=3)
    assert result["summary"]["same_score"]
    assert result["minimax"]["best_move"] in {m.uci() for m in board.legal_moves}
    assert result["alpha_beta"]["best_move"] in {m.uci() for m in board.legal_moves}
    assert board.fen() == before, "Search mutated the caller's board."
    assert result["alpha_beta"]["cutoffs"] > 0
    assert result["alpha_beta"]["pruned_moves"] > 0
    for trace in (result["minimax"], result["alpha_beta"]):
        ids = {node["id"] for node in trace["nodes"]}
        assert all(parent in ids and child in ids for parent, child in trace["edges"])
        assert trace["nodes_visited"] == sum(node["kind"] != "pruned" for node in trace["nodes"])
        assert trace["leaf_nodes_evaluated"] == sum(node["kind"] == "leaf" for node in trace["nodes"])


def test_custom_and_invalid_fen():
    board = parse_fen("7k/6pp/8/8/8/8/6PP/7K w - - 0 1")
    result = run_comparison(board, depth=2)
    assert result["summary"]["same_score"]
    try:
        parse_fen("this is not a FEN")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid FEN was accepted.")


def test_terminal_positions():
    checkmate = parse_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    result = run_comparison(checkmate, depth=2)
    assert result["minimax"]["best_move"] is None
    assert result["minimax"]["best_score"] == result["alpha_beta"]["best_score"]
    stalemate = parse_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    result = run_comparison(stalemate, depth=2)
    assert result["minimax"]["best_score"] == result["alpha_beta"]["best_score"] == 0


def test_live_search_progress_and_cancel():
    board = chess.Board()
    before = board.fen()
    updates = []
    search_position(board, 2, "alpha_beta", progress=lambda *values: updates.append(values))
    assert updates and all(len(update) == 4 for update in updates)
    assert any(update[0] > 0 for update in updates)

    cursor_events = []
    search_position(board, 2, "minimax", on_node=lambda *values: cursor_events.append(values))
    assert cursor_events and any(event[1] for event in cursor_events)
    for fen, path, ply, *_ in cursor_events:
        cursor = board.copy(stack=True)
        for uci in path:
            cursor.push_uci(uci)
        assert cursor.fen() == fen
        assert ply == len(path)

    def cancel_after_search_begins(visited, *_):
        if visited >= 100:
            raise SearchCancelled()

    try:
        search_position(board, 3, "minimax", progress=cancel_after_search_begins)
    except SearchCancelled:
        pass
    else:
        raise AssertionError("Search cancellation callback was ignored.")
    assert board.fen() == before


def main():
    test_standard_position_and_trace()
    test_custom_and_invalid_fen()
    test_terminal_positions()
    test_live_search_progress_and_cancel()
    print("PASS: comparison agreement, legality, board restoration, trace integrity, FEN validation, terminal handling, live progress, and cancellation.")


if __name__ == "__main__":
    main()
