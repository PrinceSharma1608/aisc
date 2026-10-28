"""Regression checks for game interaction helpers."""
import chess

from game_logic import legal_targets, material_balance, new_game, play_human_move, san_history, undo_last_turn


def main():
    board = new_game()
    assert len(list(board.legal_moves)) == 20
    e2, e4 = chess.parse_square("e2"), chess.parse_square("e4")
    assert e4 in legal_targets(board, e2)
    before = board.fen()
    assert play_human_move(board, e2, chess.parse_square("e5")) is None
    assert board.fen() == before
    human = play_human_move(board, e2, e4)
    assert human and board.peek() == human
    board.push_uci("e7e5")
    assert san_history(board) == ["e4", "e5"]
    assert undo_last_turn(board) == 2
    assert board.fen() == chess.STARTING_FEN
    assert material_balance(board) == 0
    board.push_uci("e2e4")
    assert undo_last_turn(board) == 1
    assert board.fen() == chess.STARTING_FEN
    assert new_game().fen() == chess.STARTING_FEN
    print("PASS: initial board, legal move rejection, SAN history, material balance, new game, and undo.")


if __name__ == "__main__":
    main()
