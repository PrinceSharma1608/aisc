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


def new_randomized_game(rng=None, min_plies: int = 6, max_plies: int = 16) -> chess.Board:
    """Create a fresh, legal opening position with White to move.

    A short random legal opening keeps the game familiar while giving each new
    game a different board and move history. The ordinary ``new_game`` helper
    remains the standard initial position for callers and tests that need it.
    """
    rng = rng or random.SystemRandom()
    min_plies = max(2, int(min_plies))
    max_plies = max(min_plies, int(max_plies))
    min_plies += min_plies % 2
    max_plies -= max_plies % 2
    if max_plies < min_plies:
        max_plies = min_plies
    for _ in range(100):
        board = chess.Board()
        target_plies = rng.randrange(min_plies, max_plies + 1, 2)
        for _ in range(target_plies):
            if board.is_game_over(claim_draw=True):
                break
            board.push(rng.choice(list(board.legal_moves)))
        position = _position_signature(board)
        if (board.turn == chess.WHITE and not board.is_game_over(claim_draw=True)
                and position not in _random_start_positions):
            _random_start_positions.add(position)
            return board
    fallback_rng = random.SystemRandom()
    while True:
        board = chess.Board()
        target_plies = fallback_rng.randrange(min_plies, max_plies + 1, 2)
        for _ in range(target_plies):
            if board.is_game_over(claim_draw=True):
                break
            board.push(fallback_rng.choice(list(board.legal_moves)))
        position = _position_signature(board)
        if (board.turn == chess.WHITE and not board.is_game_over(claim_draw=True)
                and position not in _random_start_positions):
            _random_start_positions.add(position)
            return board


def new_random_reachable_position(rng=None, min_plies: int = 14,
                                  max_plies: int = 40) -> chess.Board:
    """Create a unique, non-terminal middlegame reached by legal random play."""
    rng = rng or random.SystemRandom()
    min_plies = max(1, int(min_plies))
    max_plies = max(min_plies, int(max_plies))
    for _ in range(100):
        board = chess.Board()
        target_plies = rng.randint(min_plies, max_plies)
        for _ in range(target_plies):
            if board.is_game_over(claim_draw=True):
                break
            board.push(rng.choice(list(board.legal_moves)))
        position = _position_signature(board)
        if (len(board.piece_map()) >= 10 and not board.is_game_over(claim_draw=True)
                and position not in _random_start_positions):
            _random_start_positions.add(position)
            return board
    fallback_rng = random.SystemRandom()
    while True:
        board = chess.Board()
        target_plies = fallback_rng.randint(min_plies, max_plies)
        for _ in range(target_plies):
            if board.is_game_over(claim_draw=True):
                break
            board.push(fallback_rng.choice(list(board.legal_moves)))
        position = _position_signature(board)
        if (len(board.piece_map()) >= 10 and not board.is_game_over(claim_draw=True)
                and position not in _random_start_positions):
            _random_start_positions.add(position)
            return board


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
