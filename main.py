
import pygame
import chess
import sys

pygame.init()

SIZE = 80
BOARD = SIZE * 8
INFO = 60

screen = pygame.display.set_mode((BOARD, BOARD + INFO))
pygame.display.set_caption("AI Chess Arena")

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)

font = pygame.font.SysFont("Segoe UI Symbol", 52)
info_font = pygame.font.SysFont("Arial", 22)
board = chess.Board()

SYMBOLS = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}


def draw():
    for row in range(8):
        for col in range(8):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            rect = pygame.Rect(col * SIZE, row * SIZE, SIZE, SIZE)
            pygame.draw.rect(screen, color, rect)

            square = chess.square(col, 7 - row)
            piece = board.piece_at(square)

            if piece:
                symbol = SYMBOLS[piece.symbol()]
                image = font.render(symbol, True, (25, 25, 25))
                screen.blit(image, image.get_rect(center=rect.center))

    if board.is_checkmate():
        status = "Checkmate!"
    elif board.is_stalemate():
        status = "Draw: stalemate"
    elif board.is_game_over():
        status = "Game over"
    else:
        status = "White to move" if board.turn else "Black to move"

    pygame.draw.rect(screen, (35, 35, 35), (0, BOARD, BOARD, INFO))
    label = info_font.render(status, True, (255, 255, 255))
    screen.blit(label, (12, BOARD + 18))


def main():
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw()
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
