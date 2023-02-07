import os
from enum import Enum

import pygame
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect
from pygame.sprite import Sprite


LIGHT_SQUARES = 0
DARK_SQUARES = 1
BACKGROUND_COLORS = [(242, 210, 133), (115, 99, 61)]
SELECTED_SQUARE_COLOR = (252, 186, 3)
LEGAL_MOVE_COLORS = [(235, 127, 132), (115, 61, 63)]

BOARD_PIXEL_WIDTH = 640
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

os.environ['SDL_VIDEO_WINDOW_POS'] = "850, 500"


class Player(Enum):
  WHITE = 1
  BLACK = 2

  @property
  def image_abbr(self):
    return "l" if self is Player.WHITE else "d"

  @property
  def back_rank(self):
    return 0 if self is Player.WHITE else 7


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


class Selected:
  def __init__(self, piece, screen_pos):
    self.piece = piece
    self.screen_pos = screen_pos
    self.legal_moves = generate_legal_moves(piece)

  def __str__(self):
    return f"Selected(piece={self.piece}, screen_pos={self.screen_pos}, legal_moves={self.legal_moves})"

  def __repr__(self):
    return str(self)


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


class Globals:
  board = init_board(START_FEN)


def draw_squares(selected):
  for rank in range(8):
    for file in range(8):
      square_type = (rank + file) % 2
      if selected:
        if (rank, file) == (selected.piece.rank, selected.piece.file):
          color = SELECTED_SQUARE_COLOR
        elif (rank, file) in selected.legal_moves:
          color = LEGAL_MOVE_COLORS[square_type]
        else:
          color = BACKGROUND_COLORS[square_type]
      else:
        color = BACKGROUND_COLORS[square_type]
      pygame.draw.rect(screen, color, Rect(get_pos(rank, file), (SQUARE_WIDTH, SQUARE_WIDTH)))


def draw_pieces(selected, screen):
  for rank in range(8):
    for file in range(8):
      if selected and (rank, file) == (selected.piece.rank, selected.piece.file):
        screen.blit(selected.piece.surface, (
          selected.screen_pos[0] - (IMAGE_WIDTH // 2), selected.screen_pos[1] - (IMAGE_WIDTH // 2)
        ))
      elif piece := get_piece_on_board(rank, file):
        screen.blit(piece.surface, (
          piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
          (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
        ))


def get_square(pos):
  return (BOARD_PIXEL_WIDTH - pos[1]) // SQUARE_WIDTH, pos[0] // SQUARE_WIDTH


def get_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def in_bounds(rank, file):
  return (0 <= rank < 8) and (0 <= file < 8)


def get_piece_on_board(rank, file):
  if not in_bounds(rank, file):
    return None
  return Globals.board[rank][file]


def generate_pawn_moves(piece):
  moves = set()
  direction = 1 if piece.player is Player.WHITE else -1
  # non-capture moves
  if piece.rank == piece.player.back_rank + direction:
    new_rank = piece.rank + (2 * direction)
    if not Globals.board[new_rank][piece.file]:
      moves.add((new_rank, piece.file))
  new_rank = piece.rank + (1 * direction)
  if not Globals.board[new_rank][piece.file]:
    moves.add((new_rank, piece.file))
  # capture moves
  for rank_offset, file_offset in [(direction, 1), (direction, -1)]:
    new_rank, new_file = piece.rank + rank_offset, piece.file + file_offset
    if piece_on_new_square := get_piece_on_board(new_rank, new_file):
      if piece.player != piece_on_new_square.player:
        moves.add((new_rank, new_file))
  # todo: en passant
  return moves


def generate_bishop_moves(piece):
  moves = set()
  for rank_direction, file_direction in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
    collision = False
    distance = 1
    while not collision:
      new_rank, new_file = distance * rank_direction + piece.rank, distance * file_direction + piece.file
      if in_bounds(new_rank, new_file):
        if piece_on_new_square := get_piece_on_board(new_rank, new_file):
          if piece_on_new_square.player != piece.player:
            # capture
            moves.add((new_rank, new_file))
          collision = True
        else:
          moves.add((new_rank, new_file))
      else:
        # hit a wall
        collision = True
      distance += 1
  return moves


def generate_legal_moves(piece):
  if piece.type is PieceType.PAWN:
    return generate_pawn_moves(piece)
  elif piece.type is PieceType.BISHOP:
    return generate_bishop_moves(piece)
  # elif piece.type is PieceType.KNIGHT:
  #   return generate_knight_moves(piece)
  # elif piece.type is PieceType.QUEEN:
  #   return generate_queen_moves(piece)
  # elif piece.type is PieceType.KING:
  #   return generate_king_moves(piece)


def move(piece, new_rank, new_file):
  Globals.board[piece.rank][piece.file] = None
  piece.rank = new_rank
  piece.file = new_file
  Globals.board[new_rank][new_file] = piece


if __name__ == "__main__":
  pygame.init()
  screen = set_mode([BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH])
  running = True
  selected = None
  while running:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.MOUSEBUTTONDOWN:
        rank, file = get_square(event.pos)
        if piece := get_piece_on_board(rank, file):
          selected = Selected(piece, event.pos)
      elif event.type == pygame.MOUSEBUTTONUP:
        if selected and event.pos:
          rank, file = get_square(event.pos)
          if (rank, file) in selected.legal_moves:
            move(selected.piece, rank, file)
          else:
            print(f"attempted move to ({rank}, {file}) is illegal for {selected}!")
          selected = None
      elif event.type == pygame.MOUSEMOTION:
        if selected:
          selected.screen_pos = event.pos
    draw_squares(selected)
    draw_pieces(selected, screen)
    pygame.display.flip()
  pygame.quit()
