"""Small UI-independent helpers for the human-versus-engine game."""
import random
import chess


_random_start_positions = set()


def _position_signature(board: chess.Board):
    """Identify the visible/legal position without move counters."""
    return (board.board_fen(), board.turn, board.castling_xfen(), board.ep_square)

MATERIAL_VALUES = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}


def new_game() -> chess.Board:
    return chess.Board()


def new_random_endgame_position(rng=None, max_plies: int = 250) -> chess.Board:
    """Play random legal games until a fresh, natural 5–6 piece endgame appears."""
    rng = rng or random.SystemRandom()
    max_plies = max(40, int(max_plies))
    for _ in range(200):
        board = chess.Board()
        target_pieces = rng.choice((5, 6))
        for _ in range(max_plies):
            if board.is_game_over(claim_draw=True):
                break
            moves = list(board.legal_moves)
            captures = [move for move in moves if board.is_capture(move)]
            move = rng.choice(captures) if captures and rng.random() < 0.82 else rng.choice(moves)
            board.push(move)
            pieces_left = len(board.piece_map())
            if (pieces_left == target_pieces and not board.is_game_over(claim_draw=True)
                    and not board.is_check() and not _has_mate_in_one(board)):
                position = _position_signature(board)
                if position not in _random_start_positions:
                    _random_start_positions.add(position)
                    return board
    # A separate entropy source avoids repeating positions if a caller injects
    # a deterministic RNG during tests or a future custom setup.
    return new_random_endgame_position(random.SystemRandom(), max_plies)


def _has_mate_in_one(board: chess.Board) -> bool:
    for move in list(board.legal_moves):
        board.push(move)
        is_mate = board.is_checkmate()
        board.pop()
        if is_mate:
            return True
    return False


def legal_targets(board: chess.Board, from_square: chess.Square,
                  color: chess.Color = chess.WHITE) -> list[chess.Square]:
    piece = board.piece_at(from_square)
    if not piece or piece.color != color:
        return []
    return [move.to_square for move in board.legal_moves if move.from_square == from_square]


def play_human_move(board: chess.Board, from_square: chess.Square,
                    to_square: chess.Square, promotion: int = chess.QUEEN):
    """Push a legal human move; auto-promote pawns to a queen. Return its Move or None."""
    piece = board.piece_at(from_square)
    promote = promotion if piece and piece.piece_type == chess.PAWN and chess.square_rank(to_square) in (0, 7) else None
    move = chess.Move(from_square, to_square, promotion=promote)
    if move not in board.legal_moves:
        return None
    board.push(move)
    return move


def undo_last_turn(board: chess.Board) -> int:
    """Undo the latest engine/human pair, or the remaining human move after an engine error."""
    if not board.move_stack:
        return 0
    board.pop()
    removed = 1
    if board.move_stack and board.turn == chess.BLACK:
        board.pop()
        removed += 1
    return removed


def san_history(board: chess.Board) -> list[str]:
    temp = chess.Board(board.root().fen())
    history = []
    for move in board.move_stack:
        history.append(temp.san(move))
        temp.push(move)
    return history


def material_balance(board: chess.Board) -> int:
    """Current on-board material difference in pawn units; positive favors White."""
    return sum(MATERIAL_VALUES[piece.piece_type] * (1 if piece.color else -1)
               for piece in board.piece_map().values())
