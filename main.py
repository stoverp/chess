from enum import Enum

import pygame
from pygame import mouse
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect
from pygame.sprite import Sprite


class Player(Enum):
  WHITE = 1
  BLACK = 2

  @property
  def image_abbr(self):
    return "l" if self is Player.WHITE else "d"


class PieceType(Enum):
  PAWN = 'p'
  BISHOP = 'b'
  KNIGHT = 'n'
  ROOK = 'r'
  QUEEN = 'q'
  KING = 'k'


class Piece(Sprite):
  def __init__(self, player, type, rank, file):
    super(Piece, self).__init__()
    self.player = player
    self.type = type
    self.rank = rank
    self.file = file
    self.surface = load(f"images/Chess_{type.value}{player.image_abbr}t60.png")

  def __str__(self):
    return f"Piece(player={self.player}, type={self.type}, rank={self.rank}, file={self.file})"

  def __repr__(self):
    return str(self)


BOARD_PIXEL_WIDTH = 640
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def draw_board():
  for rank in range(8):
    for file in range(8):
      color = (131, 163, 133) if (rank + file) % 2 == 0 else (54, 74, 89)
      pygame.draw.rect(screen, color, Rect(rank * SQUARE_WIDTH, file * SQUARE_WIDTH, SQUARE_WIDTH, SQUARE_WIDTH))


def init_pieces(fen):
  pieces = []
  # for now, ignore extra metadata after board repr
  fen = fen.split(" ")[0]
  for inverse_rank, rank_line in enumerate(fen.split("/")):
    rank = 7 - inverse_rank
    file = 0
    for piece_char in rank_line:
      if piece_char.isdigit():
        file += int(piece_char)
      else:
        player = Player.WHITE if piece_char.isupper() else Player.BLACK
        pieces.append(Piece(player, PieceType(piece_char.lower()), rank, file))
        file += 1
  return pieces


def draw_pieces(pieces, screen):
  for piece in pieces:
    screen.blit(piece.surface, (
      piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
      (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
    ))


if __name__ == "__main__":
  pieces = init_pieces(START_FEN)
  pygame.init()
  screen = set_mode([BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH])
  running = True
  while running:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.MOUSEBUTTONDOWN:
        print(f"mouse button pressed: {event}")
    draw_board()
    draw_pieces(pieces, screen)
    pygame.display.flip()
  pygame.quit()
