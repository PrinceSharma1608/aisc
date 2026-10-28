"""Small UI-independent helpers for the human-versus-engine game."""
import chess

MATERIAL_VALUES = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}


def new_game() -> chess.Board:
    return chess.Board()


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
