
import chess
import math

# Material values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

MATE_SCORE = 100_000


def evaluate(board):
    """Positive score favors White; negative favors Black."""
    if board.is_checkmate():
        # The side to move has been checkmated.
        return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE

    if board.is_game_over():
        return 0

    score = 0

    for square, piece in board.piece_map().items():
        value = PIECE_VALUES[piece.piece_type]

        # Small positional bonus for advancing pawns toward promotion.
        if piece.piece_type == chess.PAWN:
            advancement = (
                chess.square_rank(square)
                if piece.color == chess.WHITE
                else 7 - chess.square_rank(square)
            )
            value += advancement * 5

        score += value if piece.color == chess.WHITE else -value

    return score


def move_order_score(board, move):
    """Try captures of valuable pieces first to improve pruning."""
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)

    score = 0

    if victim and attacker:
        score += 10 * PIECE_VALUES[victim.piece_type]
        score -= PIECE_VALUES[attacker.piece_type]

    if move.promotion:
        score += PIECE_VALUES[move.promotion]

    return score


def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate(board), None

    ordered_moves = sorted(
        list(board.legal_moves),
        key=lambda move: move_order_score(board, move),
        reverse=True,
    )

    best_move = None

    if maximizing:
        best_score = -math.inf

        for move in ordered_moves:
            board.push(move)
            score, _ = minimax(
                board, depth - 1, alpha, beta, False
            )
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, best_score)

            if beta <= alpha:
                break

        return best_score, best_move

    else:
        best_score = math.inf

        for move in ordered_moves:
            board.push(move)
            score, _ = minimax(
                board, depth - 1, alpha, beta, True
            )
            board.pop()

            if score < best_score:
                best_score = score
                best_move = move

            beta = min(beta, best_score)

            if beta <= alpha:
                break

        return best_score, best_move


def choose_move(board, depth=3):
    """Return the AI's best move and its evaluation."""
    if board.is_game_over():
        return None, evaluate(board)

    maximizing = board.turn == chess.WHITE

    score, move = minimax(
        board,
        depth,
        -math.inf,
        math.inf,
        maximizing,
    )

    return move, score
