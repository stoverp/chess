import os
from enum import Enum, auto
import random

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

ROOK_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISHOP_DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

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


class MoveType(Enum):
  OUT_OF_BOUNDS = auto()
  SELF_OCCUPIED = auto()
  CAPTURE = auto()
  OPEN_SQUARE = auto()

  @classmethod
  def get_type(cls, player, rank, file):
    if not ((0 <= rank < 8) and (0 <= file < 8)):
      return MoveType.OUT_OF_BOUNDS
    if piece_on_new_square := Globals.board[rank][file]:
      if player == piece_on_new_square.player:
        return MoveType.SELF_OCCUPIED
      else:
        return MoveType.CAPTURE
    else:
      return MoveType.OPEN_SQUARE


class PieceType(Enum):
  PAWN = 'p'
  KNIGHT = 'n'
  BISHOP = 'b'
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
        piece = Piece(player, PieceType(piece_char.lower()), rank, file)
        if player is Player.WHITE:
          Globals.white_pieces.add(piece)
        else:
          Globals.black_pieces.add(piece)
        board[rank][file] = piece
        file += 1
  return board


class Globals:
  white_pieces = set()
  black_pieces = set()
  board = None


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
      elif piece := Globals.board[rank][file]:
        screen.blit(piece.surface, (
          piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
          (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
        ))


def get_square(pos):
  return (BOARD_PIXEL_WIDTH - pos[1]) // SQUARE_WIDTH, pos[0] // SQUARE_WIDTH


def get_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def generate_pawn_moves(piece):
  moves = set()
  direction = 1 if piece.player is Player.WHITE else -1
  # one-square standard move
  rank_candidates = [piece.rank + (1 * direction)]
  # two-square opening move
  if piece.rank == piece.player.back_rank + direction:
    rank_candidates.append(piece.rank + (2 * direction))
  for new_rank in rank_candidates:
    if MoveType.get_type(piece.player, new_rank, piece.file) is MoveType.OPEN_SQUARE:
      moves.add((new_rank, piece.file))
  # capture moves
  for rank_offset, file_offset in [(direction, 1), (direction, -1)]:
    new_rank, new_file = piece.rank + rank_offset, piece.file + file_offset
    if MoveType.get_type(piece.player, new_rank, new_file) is MoveType.CAPTURE:
      moves.add((new_rank, new_file))
  # todo: en passant
  return moves


def generate_slide_moves(piece, directions):
  moves = set()
  for rank_direction, file_direction in directions:
    collision = False
    distance = 1
    while not collision:
      new_rank, new_file = distance * rank_direction + piece.rank, distance * file_direction + piece.file
      move_type = MoveType.get_type(piece.player, new_rank, new_file)
      if move_type in (MoveType.SELF_OCCUPIED, MoveType.OUT_OF_BOUNDS):
        collision = True
      else:
        moves.add((new_rank, new_file))
        if move_type is MoveType.CAPTURE:
          collision = True
      distance += 1
  return moves


def generate_knight_moves(piece):
  moves = set()
  for far_rank in [True, False]:
    for rank_direction in [1, -1]:
      for file_direction in [1, -1]:
        new_rank = (2 if far_rank else 1) * rank_direction + piece.rank
        new_file = (1 if far_rank else 2) * file_direction + piece.file
        move_type = MoveType.get_type(piece.player, new_rank, new_file)
        if move_type in (MoveType.OPEN_SQUARE, MoveType.CAPTURE):
          moves.add((new_rank, new_file))
  return moves


def generate_king_moves(piece):
  moves = set()
  for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
    new_rank = rank_direction + piece.rank
    new_file = file_direction + piece.file
    move_type = MoveType.get_type(piece.player, new_rank, new_file)
    if move_type in (MoveType.OPEN_SQUARE, MoveType.CAPTURE):
      moves.add((new_rank, new_file))
    # todo: don't put king in check!
    # todo: castling
  return moves


def generate_legal_moves(piece):
  if piece.type is PieceType.PAWN:
    return generate_pawn_moves(piece)
  elif piece.type is PieceType.KNIGHT:
    return generate_knight_moves(piece)
  elif piece.type is PieceType.BISHOP:
    return generate_slide_moves(piece, BISHOP_DIRECTIONS)
  elif piece.type is PieceType.ROOK:
    return generate_slide_moves(piece, ROOK_DIRECTIONS)
  elif piece.type is PieceType.QUEEN:
    return generate_slide_moves(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS)
  elif piece.type is PieceType.KING:
    return generate_king_moves(piece)


def generate_all_legal_moves(pieces):
  all_legal_moves = []
  for piece in pieces:
    for move in generate_legal_moves(piece):
      all_legal_moves.append((piece, move[0], move[1]))
  return all_legal_moves


def move(piece, new_rank, new_file):
  Globals.board[piece.rank][piece.file] = None
  piece.rank = new_rank
  piece.file = new_file
  game_over = False
  if captured_piece := Globals.board[new_rank][new_file]:
    player_pieces = Globals.white_pieces if captured_piece.player is Player.WHITE else Globals.black_pieces
    player_pieces.remove(captured_piece)
    if captured_piece.type is PieceType.KING:
      game_over = True
  Globals.board[new_rank][new_file] = piece
  return game_over


if __name__ == "__main__":
  pygame.init()
  screen = set_mode([BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH])
  Globals.board = init_board(START_FEN)
  active_player = Player.WHITE
  selected = None
  running = True
  while running:
    if active_player is Player.BLACK:
      piece, rank, file = random.choice(generate_all_legal_moves(Globals.black_pieces))
      if move(piece, rank, file):
        running = False
      active_player = Player.WHITE
    else:
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
          rank, file = get_square(event.pos)
          if piece := Globals.board[rank][file]:
            if piece.player is Player.WHITE:
              selected = Selected(piece, event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
          if selected and event.pos:
            rank, file = get_square(event.pos)
            if (rank, file) in selected.legal_moves:
              if move(selected.piece, rank, file):
                running = False
              active_player = Player.BLACK
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
