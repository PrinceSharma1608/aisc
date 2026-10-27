
import chess
from ai import choose_move

board = chess.Board()

print("Initial position:")
print(board)
print("\nAI is thinking...")

move, score = choose_move(board, depth=3)

if move is None:
    print("The game is already over.")
else:
    print("AI selected:", board.san(move))
    print("Internal move:", move.uci())
    print("Evaluation:", score, "centipawns")

    board.push(move)

    print("\nBoard after AI's move:")
    print(board)
