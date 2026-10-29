"""Regression checks for game interaction helpers."""
import random
import chess
from ai import choose_varied_candidate

from game_logic import (legal_targets, material_balance, new_game, new_randomized_game,
                        new_random_endgame_position, play_human_move, san_history,
                        undo_last_turn)


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
    random_opening_a, random_opening_b = new_randomized_game(), new_randomized_game()
    assert random_opening_a.is_valid() and random_opening_b.is_valid()
    assert random_opening_a.turn == chess.WHITE and random_opening_b.turn == chess.WHITE
    assert random_opening_a.fen() != random_opening_b.fen()
    random_endgame_a = new_random_endgame_position()
    random_endgame_b = new_random_endgame_position()
    for endgame in (random_endgame_a, random_endgame_b):
        assert endgame.is_valid() and not endgame.is_check()
        assert len(endgame.piece_map()) in (5, 6)
        assert endgame.root().fen() == chess.STARTING_FEN
        for move in list(endgame.legal_moves):
            endgame.push(move)
            assert not endgame.is_checkmate(), "Endgame generator created a forced mate in one."
            endgame.pop()
    assert random_endgame_a.fen() != random_endgame_b.fen()
    choices = [{"score": 25, "san": "A"}, {"score": -40, "san": "B"},
               {"score": -250, "san": "C"}]
    assert choose_varied_candidate(choices, tolerance_cp=100, rng=random.Random(3)) in choices[:2]
    selected = {choose_varied_candidate(choices, tolerance_cp=100, rng=random.Random(seed))["san"]
                for seed in range(20)}
    assert selected == {"A", "B"}
    assert choose_varied_candidate([]) is None
    print("PASS: legal move helpers, fresh randomized starts, near-best Stockfish variation, SAN history, and undo.")


if __name__ == "__main__":
    main()
