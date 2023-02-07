from enum import Enum

import pygame
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect
from pygame.sprite import Sprite


LIGHT_SQUARE_COLOR = (131, 163, 133)
DARK_SQUARE_COLOR = (54, 74, 89)
SELECTED_SQUARE_COLOR = (252, 186, 3)

BOARD_PIXEL_WIDTH = 640
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


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


def draw_squares(selected_piece):
  for rank in range(8):
    for file in range(8):
      if selected_piece and (rank, file) == (selected_piece.rank, selected_piece.file):
        color = SELECTED_SQUARE_COLOR
      else:
        color = LIGHT_SQUARE_COLOR if (rank + file) % 2 == 0 else DARK_SQUARE_COLOR
      pygame.draw.rect(screen, color, Rect(get_pos(rank, file), (SQUARE_WIDTH, SQUARE_WIDTH)))


def init_board(fen):
  board = [[None for _ in range(8)] for _ in range(8)]
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
        board[rank][file] = (Piece(player, PieceType(piece_char.lower()), rank, file))
        file += 1
  return board


def draw_pieces(board, selected_piece, moving_selected_pos, screen):
  for rank in range(8):
    for file in range(8):
      if selected_piece and (rank, file) == (selected_piece.rank, selected_piece.file):
        if moving_selected_pos:
          # print(f"drawing selected piece {selected_piece} at {moving_selected_pos} ...")
          screen.blit(selected_piece.surface, (
            moving_selected_pos[0] - (IMAGE_WIDTH // 2), moving_selected_pos[1] - (IMAGE_WIDTH // 2)
          ))
        else:
          continue
      elif piece := board[rank][file]:
        screen.blit(piece.surface, (
          piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
          (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
        ))


def get_square(pos):
  return (BOARD_PIXEL_WIDTH - pos[1]) // SQUARE_WIDTH, pos[0] // SQUARE_WIDTH


def get_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def move(piece, new_rank, new_file, board):
  board[piece.rank][piece.file] = None
  piece.rank = new_rank
  piece.file = new_file
  board[new_rank][new_file] = piece


if __name__ == "__main__":
  board = init_board(START_FEN)
  pygame.init()
  screen = set_mode([BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH])
  running = True
  selected_piece = None
  moving_selected_pos = None
  while running:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.MOUSEBUTTONDOWN:
        rank, file = get_square(event.pos)
        # print(f"mouse button pressed: {event.pos}. rank: {rank}, file: {file}")
        if piece := board[rank][file]:
          selected_piece = piece
        else:
          selected_piece = None
      elif event.type == pygame.MOUSEBUTTONUP:
        rank, file = get_square(event.pos)
        if selected_piece:
          move(selected_piece, rank, file, board)
          selected_piece = None
          moving_selected_pos = None
      elif event.type == pygame.MOUSEMOTION:
        if selected_piece:
          moving_selected_pos = event.pos
          # print(f"mouse moved ({moving_selected_pos}) with selected piece: {selected_piece}")
    draw_squares(selected_piece)
    draw_pieces(board, selected_piece, moving_selected_pos, screen)
    pygame.display.flip()
  pygame.quit()
