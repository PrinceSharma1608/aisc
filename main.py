
import pygame
import chess
import sys

pygame.init()

SIZE = 80
BOARD_SIZE = SIZE * 8
INFO_HEIGHT = 90

screen = pygame.display.set_mode(
    (BOARD_SIZE, BOARD_SIZE + INFO_HEIGHT)
)
pygame.display.set_caption("AI Chess Arena")

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HIGHLIGHT = (246, 246, 105)
TARGET = (80, 180, 90)

font = pygame.font.SysFont("Segoe UI Symbol", 52)
info_font = pygame.font.SysFont("Arial", 20)

board = chess.Board()
selected = None
message = "Select a piece to move"

SYMBOLS = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}


def get_square(pos):
    x, y = pos
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        return None

    col = x // SIZE
    row = y // SIZE
    return chess.square(col, 7 - row)


def draw():
    legal_targets = set()

    if selected is not None:
        legal_targets = {
            move.to_square
            for move in board.legal_moves
            if move.from_square == selected
        }

    for row in range(8):
        for col in range(8):
            square = chess.square(col, 7 - row)
            rect = pygame.Rect(
                col * SIZE, row * SIZE, SIZE, SIZE
            )

            color = LIGHT if (row + col) % 2 == 0 else DARK

            if square == selected:
                color = HIGHLIGHT

            pygame.draw.rect(screen, color, rect)

            if square in legal_targets:
                center = rect.center

                if board.piece_at(square):
                    pygame.draw.circle(
                        screen, TARGET, center, SIZE // 2 - 3, 4
                    )
                else:
                    pygame.draw.circle(
                        screen, TARGET, center, 10
                    )

            piece = board.piece_at(square)
            if piece:
                symbol = SYMBOLS[piece.symbol()]
                image = font.render(symbol, True, (25, 25, 25))
                screen.blit(
                    image, image.get_rect(center=rect.center)
                )

    if board.is_checkmate():
        status = "Checkmate!"
    elif board.is_stalemate():
        status = "Draw: stalemate"
    elif board.is_game_over():
        status = "Game over"
    elif board.is_check():
        status = "Check!"
    else:
        status = "White to move" if board.turn else "Black to move"

    pygame.draw.rect(
        screen, (35, 35, 35),
        (0, BOARD_SIZE, BOARD_SIZE, INFO_HEIGHT)
    )

    label = info_font.render(status, True, (255, 255, 255))
    screen.blit(label, (12, BOARD_SIZE + 10))

    hint = info_font.render(message, True, (210, 210, 210))
    screen.blit(hint, (12, BOARD_SIZE + 42))


def handle_click(pos):
    global selected, message

    if board.is_game_over():
        message = "Game over. Close and restart the program."
        return

    square = get_square(pos)
    if square is None:
        return

    piece = board.piece_at(square)

    if selected is None:
        if piece and piece.color == board.turn:
            selected = square
            message = "Choose a highlighted destination"
        else:
            message = "Select a piece belonging to the side to move"
        return

    move = chess.Move(selected, square)

    # Automatic queen promotion for this first version.
    moving_piece = board.piece_at(selected)
    if (
        moving_piece
        and moving_piece.piece_type == chess.PAWN
        and chess.square_rank(square) in (0, 7)
    ):
        move.promotion = chess.QUEEN

    if move in board.legal_moves:
        board.push(move)
        message = "Last move: " + board.peek().uci()
        selected = None
    elif piece and piece.color == board.turn:
        selected = square
        message = "Piece selected. Choose a highlighted destination"
    else:
        selected = None
        message = "Illegal move. Try a highlighted destination"


def main():
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[1] < BOARD_SIZE:
                    handle_click(event.pos)

            if event.type == pygame.KEYDOWN:
                global board, selected, message

                if event.key == pygame.K_r:
                    board = chess.Board()
                    selected = None
                    message = "Game restarted"

                elif event.key == pygame.K_ESCAPE:
                    selected = None
                    message = "Selection cancelled"

        draw()
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
