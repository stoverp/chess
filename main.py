import math
import os
import time
from argparse import ArgumentParser
from collections import defaultdict
from enum import Enum, auto

import pygame as pg
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect
from pygame.sprite import Sprite

SEARCH_DEPTH = 3

LIGHT_SQUARES = 0
DARK_SQUARES = 1
BACKGROUND_COLORS = [(242, 210, 133), (115, 99, 61)]
SELECTED_SQUARE_COLOR = (252, 186, 3)
LEGAL_MOVE_COLORS = [(235, 127, 132), (115, 61, 63)]
LAST_MOVE_COLORS = [(127, 235, 226), (61, 113, 115)]

# todo: limit window resizing to preserve aspect ratio
DISPLAY_WIDTH = 1120
BOARD_PIXEL_WIDTH = 560
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

ROOK_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISHOP_DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

os.environ['SDL_VIDEO_WINDOW_POS'] = "300, 100"


class PlayerColor(Enum):
  WHITE = 1
  BLACK = 2

  @property
  def abbr(self):
    return "w" if self is PlayerColor.WHITE else "b"

  @property
  def image_abbr(self):
    return "l" if self is PlayerColor.WHITE else "d"

  @property
  def back_rank(self):
    return 0 if self is PlayerColor.WHITE else 7

  @property
  def opponent(self):
    return PlayerColor.BLACK if self is PlayerColor.WHITE else PlayerColor.WHITE


class PlayerState:
  def __init__(self, player_color):
    self.player_color = player_color
    self.pieces = defaultdict(set)

  def in_check(self):
    opponent = Globals.players[self.player_color.opponent]
    for move in generate_all_legal_moves(opponent, filter_checks=False):
      if move.captured_piece and move.captured_piece.type is PieceType.KING:
        return True
    return False

  def find_rook(self, king_side: bool):
    # warning: this currently returns None if a rook has been moved out of its home
    # todo: okay for now since this method is only used for castling rights, but perhaps revisit
    for rook in self.pieces[PieceType.ROOK]:
      if king_side:
        if rook.file == 7:
          return rook
      else:
        if rook.file == 0:
          return rook
    return None

  def find(self, piece_type):
    piece_set = self.pieces[piece_type]
    if not piece_set:
      return None
    return next(iter(piece_set))


class MoveType(Enum):
  OUT_OF_BOUNDS = auto()
  SELF_OCCUPIED = auto()
  CAPTURE = auto()
  OPEN_SQUARE = auto()

  @classmethod
  def get_type(cls, player, rank, file):
    if not in_bounds(rank, file):
      return MoveType.OUT_OF_BOUNDS
    if piece_on_new_square := Globals.board[rank][file]:
      if player == piece_on_new_square.player_color:
        return MoveType.SELF_OCCUPIED
      else:
        return MoveType.CAPTURE
    else:
      return MoveType.OPEN_SQUARE


class PieceType(Enum):
  PAWN = 'p', 1
  KNIGHT = 'n', 3
  BISHOP = 'b', 3
  ROOK = 'r', 5
  QUEEN = 'q', 9
  KING = 'k', 0

  def __new__(cls, value, score):
    obj = object.__new__(cls)
    obj._value_ = value
    obj.score = score
    return obj


class Piece(Sprite):
  def __init__(self, player_color, type, rank, file):
    super(Piece, self).__init__()
    self.player_color = player_color
    self.type = type
    self.rank = rank
    self.file = file
    self.n_times_moved = 0
    self.surface = load(f"images/Chess_{type.value}{player_color.image_abbr}t60.png")

  def __str__(self):
    return f"Piece(player_color={self.player_color}, type={self.type}, rank={self.rank}, file={self.file})"

  def __repr__(self):
    return str(self)

  def fen(self):
    abbr = self.type.value
    return abbr.upper() if self.player_color is PlayerColor.WHITE else abbr


class Move:
  def __init__(self, piece, rank, file):
    self.piece = piece
    self.rank = rank
    self.file = file
    # todo: this assumes that a Move is created only when the board is in the appropriate state
    self.captured_piece = Globals.board[rank][file]
    self.old_rank = piece.rank
    self.old_file = piece.file
    self.castling_rook_move = None

  def __str__(self):
    return f"Move(piece={self.piece}, rank={self.rank}, file={self.file}, captured_piece={self.captured_piece}, old_rank={self.old_rank}, old_file={self.old_file})"

  def __repr__(self):
    return str(self)

  def __eq__(self, other):
    if not other:
      return False
    return self.piece == other.piece and self.rank == other.rank and self.file == other.file

  def __hash__(self):
    return hash(repr(self))

  def apply(self):
    if self.captured_piece:
      Globals.players[self.captured_piece.player_color].pieces[self.captured_piece.type].remove(self.captured_piece)
    self.piece.rank = self.rank
    self.piece.file = self.file
    Globals.board[self.old_rank][self.old_file] = None
    Globals.board[self.rank][self.file] = self.piece
    self.piece.n_times_moved += 1
    # handle castling special case
    file_diff = self.file - self.old_file
    if self.piece.type is PieceType.KING and abs(file_diff) == 2:
      is_king_side = file_diff == 2  # king moving two to the right
      self.castling_rook_move = Move(
        Globals.players[self.piece.player_color].find_rook(king_side=is_king_side),
        self.piece.rank,
        self.piece.file - 1 if is_king_side else self.piece.file + 1
      )
      self.castling_rook_move.apply()

  def unapply(self):
    if self.captured_piece:
      Globals.players[self.captured_piece.player_color].pieces[self.captured_piece.type].add(self.captured_piece)
    self.piece.rank = self.old_rank
    self.piece.file = self.old_file
    Globals.board[self.rank][self.file] = self.captured_piece
    Globals.board[self.old_rank][self.old_file] = self.piece
    self.piece.n_times_moved -= 1
    # handle castling special case
    if self.castling_rook_move:
      self.castling_rook_move.unapply()


def display_to_screen(display_pos):
  window_width, window_height = pg.display.get_window_size()
  width_scale = window_width / BOARD_PIXEL_WIDTH
  height_scale = window_height / BOARD_PIXEL_WIDTH
  return display_pos[0] / width_scale, display_pos[1] / height_scale


class Selected:
  def __init__(self, piece, display_pos):
    self.piece = piece
    self.update_screen_pos(display_pos)
    self.legal_moves = generate_legal_moves(piece)

  def __str__(self):
    return f"Selected(piece={self.piece}, screen_pos={self.screen_pos}, legal_moves={self.legal_moves})"

  def __repr__(self):
    return str(self)

  def update_screen_pos(self, display_pos):
    self.screen_pos = display_to_screen(display_pos)


def in_bounds(rank, file):
  return (0 <= rank < 8) and (0 <= file < 8)


def parse_piece_char(piece_char):
  return PieceType(piece_char.lower()), PlayerColor.WHITE if piece_char.isupper() else PlayerColor.BLACK


def init_castling_ability(castling_ability):
  # first assume that nobody can castle by setting the king and rook move counts to something nonzero
  for color in PlayerColor:
    for piece_type in [PieceType.KING, PieceType.ROOK]:
      for piece in Globals.players[color].pieces[piece_type]:
        piece.n_times_moved = 1
  if castling_ability != "-":
    for piece_char in castling_ability:
      piece_type, piece_color = parse_piece_char(piece_char)
      # king definitely hasn't moved
      Globals.players[piece_color].find(PieceType.KING).n_times_moved = 0
      # find and mark appropriate rook ("k"-side or "q"-side)
      Globals.players[piece_color].find_rook(king_side=piece_type is PieceType.KING).n_times_moved = 0


def init_state(fen):
  Globals.board = [[None for _ in range(8)] for _ in range(8)]
  piece_placement, side_to_move, castling_ability, en_passant_target_square, halfmove_clock, fullmove_counter = fen.split(" ")
  for inverse_rank, rank_line in enumerate(piece_placement.split("/")):
    rank = 7 - inverse_rank
    file = 0
    for piece_char in rank_line:
      if piece_char.isdigit():
        file += int(piece_char)
      else:
        piece_type, piece_color = parse_piece_char(piece_char)
        piece = Piece(piece_color, piece_type, rank, file)
        Globals.players[piece_color].pieces[piece_type].add(piece)
        Globals.board[rank][file] = piece
        file += 1
  Globals.active_player_color = PlayerColor.WHITE if side_to_move == "w" else PlayerColor.BLACK
  init_castling_ability(castling_ability)


class Globals:
  players = {
    PlayerColor.WHITE: PlayerState(PlayerColor.WHITE),
    PlayerColor.BLACK: PlayerState(PlayerColor.BLACK)
  }
  displayed_screen = None
  screen = None
  board = [[None for _ in range(8)] for _ in range(8)]
  selected = None
  active_player_color = PlayerColor.WHITE
  active_player_legal_moves = []
  move_history = []

  @classmethod
  def active_player(cls):
    return cls.players[cls.active_player_color]


def draw_squares():
  for rank in range(8):
    for file in range(8):
      square_type = (rank + file) % 2
      if Globals.move_history and (rank, file) == (Globals.move_history[-1].old_rank, Globals.move_history[-1].old_file):
        color = LAST_MOVE_COLORS[square_type]
      elif Globals.selected:
        if (rank, file) == (Globals.selected.piece.rank, Globals.selected.piece.file):
          color = SELECTED_SQUARE_COLOR
        elif Move(Globals.selected.piece, rank, file) in Globals.selected.legal_moves:
          color = LEGAL_MOVE_COLORS[square_type]
        else:
          color = BACKGROUND_COLORS[square_type]
      else:
        color = BACKGROUND_COLORS[square_type]
      pg.draw.rect(Globals.screen, color, Rect(get_screen_pos(rank, file), (SQUARE_WIDTH, SQUARE_WIDTH)))


def draw_pieces():
  for rank in range(8):
    for file in range(8):
      if Globals.selected and (rank, file) == (Globals.selected.piece.rank, Globals.selected.piece.file):
        Globals.screen.blit(Globals.selected.piece.surface, (
          Globals.selected.screen_pos[0] - (IMAGE_WIDTH // 2), Globals.selected.screen_pos[1] - (IMAGE_WIDTH // 2)
        ))
      elif piece := Globals.board[rank][file]:
        Globals.screen.blit(piece.surface, (
          piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
          (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
        ))


def get_square(display_pos):
  screen_pos = display_to_screen(display_pos)
  return int((BOARD_PIXEL_WIDTH - screen_pos[1]) / SQUARE_WIDTH), int(screen_pos[0] / SQUARE_WIDTH)


def get_screen_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def generate_pawn_moves(piece):
  moves = set()
  direction = 1 if piece.player_color is PlayerColor.WHITE else -1
  # one-square standard move
  rank_candidates = [piece.rank + (1 * direction)]
  # two-square opening move
  if piece.rank == piece.player_color.back_rank + direction:
    # can't move through pieces
    if not Globals.board[piece.rank + (1 * direction)][piece.file]:
      rank_candidates.append(piece.rank + (2 * direction))
  for new_rank in rank_candidates:
    if MoveType.get_type(piece.player_color, new_rank, piece.file) is MoveType.OPEN_SQUARE:
      moves.add(Move(piece, new_rank, piece.file))
  # capture moves
  for rank_offset, file_offset in [(direction, 1), (direction, -1)]:
    new_rank, new_file = piece.rank + rank_offset, piece.file + file_offset
    if MoveType.get_type(piece.player_color, new_rank, new_file) is MoveType.CAPTURE:
      moves.add(Move(piece, new_rank, new_file))
  # todo: en passant
  # todo: promotion
  return moves


def generate_slide_moves(piece, directions):
  moves = set()
  for rank_direction, file_direction in directions:
    collision = False
    distance = 1
    while not collision:
      new_rank, new_file = distance * rank_direction + piece.rank, distance * file_direction + piece.file
      move_type = MoveType.get_type(piece.player_color, new_rank, new_file)
      if move_type in (MoveType.SELF_OCCUPIED, MoveType.OUT_OF_BOUNDS):
        collision = True
      else:
        moves.add(Move(piece, new_rank, new_file))
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
        move_type = MoveType.get_type(piece.player_color, new_rank, new_file)
        if move_type in (MoveType.OPEN_SQUARE, MoveType.CAPTURE):
          moves.add(Move(piece, new_rank, new_file))
  return moves


def generate_king_moves(piece: Piece, filter_checks=True):
  moves = set()
  for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
    new_rank = rank_direction + piece.rank
    new_file = file_direction + piece.file
    move_type = MoveType.get_type(piece.player_color, new_rank, new_file)
    if move_type in (MoveType.OPEN_SQUARE, MoveType.CAPTURE):
      moves.add(Move(piece, new_rank, new_file))
  # can we castle?
  if piece.n_times_moved == 0:
    player = Globals.players[piece.player_color]
    for rook in player.pieces[PieceType.ROOK]:
      if rook.n_times_moved == 0:
        can_castle = True
        new_file = piece.file + 2 if rook.file - piece.file > 0 else piece.file - 2
        small_file, big_file = sorted([piece.file, rook.file])
        for file_between in range(small_file + 1, big_file):
          if Globals.board[piece.rank][file_between]:
            can_castle = False
            break
        if can_castle:
          if filter_checks:
            if player.in_check():
              can_castle = False
            else:
              # make a fake king move to the space between
              fake_move = Move(piece, piece.rank, piece.file + 1 if rook.file - piece.file > 0 else piece.file - 1)
              fake_move.apply()
              if player.in_check():
                # player would be castling through check
                can_castle = False
              fake_move.unapply()
          if can_castle:
            moves.add(Move(piece, piece.rank, new_file))
  return moves


def generate_legal_moves(piece, filter_checks=True):
  if piece.type is PieceType.PAWN:
    moves = generate_pawn_moves(piece)
  elif piece.type is PieceType.KNIGHT:
    moves = generate_knight_moves(piece)
  elif piece.type is PieceType.BISHOP:
    moves = generate_slide_moves(piece, BISHOP_DIRECTIONS)
  elif piece.type is PieceType.ROOK:
    moves = generate_slide_moves(piece, ROOK_DIRECTIONS)
  elif piece.type is PieceType.QUEEN:
    moves = generate_slide_moves(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS)
  else:  # piece.type is PieceType.KING:
    moves = generate_king_moves(piece, filter_checks)
  if filter_checks:
    player = Globals.players[piece.player_color]
    legal_moves = []
    for move in moves:
      move.apply()
      if filter_checks and player.in_check():
        # print(f"{move} not legal, puts {player.player_color} in check!")
        pass
      else:
        legal_moves.append(move)
      move.unapply()
    return legal_moves
  else:
    return moves


def generate_all_legal_moves(player, filter_checks=True):
  all_legal_moves = []
  for pieces in player.pieces.values():
    for piece in pieces:
      for move in generate_legal_moves(piece, filter_checks):
        all_legal_moves.append(move)
  return all_legal_moves


def undo_last_move():
  if Globals.move_history:
    move = Globals.move_history.pop()
    move.unapply()
    Globals.active_player_color = Globals.active_player_color.opponent
    Globals.active_player_legal_moves = generate_all_legal_moves(Globals.active_player())


def make_move(move):
  move.apply()
  Globals.move_history.append(move)
  Globals.active_player_color = Globals.active_player_color.opponent
  Globals.active_player_legal_moves = generate_all_legal_moves(Globals.active_player())


def evaluate_board(active_player_color):
  score = 0
  for player in Globals.players.values():
    perspective = 1 if player.player_color == active_player_color else -1
    for pieces in player.pieces.values():
      for piece in pieces:
        score += perspective * piece.type.score
  return score


def search_moves(active_player_color, depth, alpha, beta):
  if depth == 0:
    # todo: quiescence search
    return None, evaluate_board(active_player_color)
  moves = generate_all_legal_moves(Globals.players[active_player_color])
  if not moves:
    if Globals.active_player().in_check():
      return None, -math.inf
    else:
      return None, 0
  top_move = None
  for move in moves:
    # if move.rank == 5 and move.file == 0 and move.captured_piece:
    #   print(f"evaluating {move} ...")
    move.apply()
    _, score = search_moves(active_player_color.opponent, depth - 1, -beta, -alpha)
    # negate score to reflect opponent's perspective
    score = -score
    # if move.rank == 5 and move.file == 0 and move.captured_piece:
    #   print(f"evaluated score {score} for {move}")
    move.unapply()
    if score >= beta:
      # beta limit tells us opponent can prevent this scenario
      return None, beta
    if score > alpha:
      top_move = move
      alpha = score
  return top_move, alpha


def best_move(active_player_color):
  print(f"\ncalculating {active_player_color} move ...")
  start_time = time.time()
  move, score = search_moves(active_player_color, SEARCH_DEPTH, -math.inf, math.inf)
  print(f"evaluated score {score} in {time.time() - start_time} seconds for {move}")
  if move:
    return move
  else:
    move = Globals.active_player_legal_moves[0]
    print(f"{active_player_color} has no moves that avoid checkmate! just make first legal move: {move}")
    return move


def endgame():
  print(f"GAME OVER!")
  if Globals.active_player().in_check():
    print(f"CHECKMATE: {Globals.active_player_color.opponent}")
  else:
    print(f"STALEMATE")
  waiting = True
  print("Press any key to exit.")
  while waiting:
    for event in pg.event.get():
      if event.type == pg.KEYDOWN:
        waiting = False


def generate_castling_ability_fen():
  castling_ability = ""
  for color in PlayerColor:
    if Globals.players[color].find(PieceType.KING).n_times_moved == 0:
      for char, king_side in [("k", True), ("q", False)]:
        rook = Globals.players[color].find_rook(king_side)
        if rook and rook.n_times_moved == 0:
          castling_ability += char.upper() if color is PlayerColor.WHITE else char
  return castling_ability or "-"


def generate_fen():
  piece_placement_ranks = []
  for rank in range(7, -1, -1):
    n_empty_squares = 0
    fen_line = []
    for file in range(8):
      piece = Globals.board[rank][file]
      if piece:
        if n_empty_squares > 0:
          fen_line.append(str(n_empty_squares))
          n_empty_squares = 0
        fen_line.append(piece.fen())
      else:
        n_empty_squares += 1
    if n_empty_squares > 0:
      fen_line.append(str(n_empty_squares))
    piece_placement_ranks.append("".join(fen_line))
  return f"{'/'.join(piece_placement_ranks)} {Globals.active_player_color.abbr} {generate_castling_ability_fen()} - - -"


def handle_event(event, vs_human):
  if event.type == pg.QUIT:
    return False
  elif event.type == pg.MOUSEBUTTONDOWN:
    rank, file = get_square(event.pos)
    if in_bounds(rank, file):
      if piece := Globals.board[rank][file]:
        if piece.player_color == Globals.active_player_color:
          Globals.selected = Selected(piece, event.pos)
  elif event.type == pg.MOUSEBUTTONUP:
    if Globals.selected and event.pos:
      rank, file = get_square(event.pos)
      move = Move(Globals.selected.piece, rank, file)
      if move in Globals.selected.legal_moves:
        make_move(move)
        print(f"\nCURRENT BOARD FEN: {generate_fen()}")
      else:
        print(f"attempted move to ({rank}, {file}) is illegal for {Globals.selected}!")
      Globals.selected = None
  elif event.type == pg.MOUSEMOTION:
    if Globals.selected:
      Globals.selected.update_screen_pos(event.pos)
  elif event.type == pg.KEYDOWN:
    if event.key == pg.K_u:
      if vs_human:
        undo_last_move()
      else:
        # disable undo while computer is thinking
        if Globals.active_player_color is PlayerColor.WHITE:
          # undo last black + white moves, so white is still active
          undo_last_move()
          undo_last_move()
    if event.key == pg.K_f:
      print(f"\nCURRENT BOARD FEN: {generate_fen()}")
  return True


def main(fen, vs_human):
  pg.init()
  Globals.displayed_screen = set_mode((DISPLAY_WIDTH, DISPLAY_WIDTH), pg.RESIZABLE)
  Globals.screen = pg.Surface((BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH))
  init_state(fen)
  Globals.active_player_legal_moves = generate_all_legal_moves(Globals.active_player())
  running = True
  while running:
    if not Globals.active_player_legal_moves:
      endgame()
      running = False
    if Globals.active_player_color is PlayerColor.BLACK and not vs_human:
      move = best_move(Globals.active_player_color)
      make_move(move)
    else:
      for event in pg.event.get():
        if not handle_event(event, vs_human):
          running = False
    draw_squares()
    draw_pieces()
    Globals.displayed_screen.blit(pg.transform.scale(Globals.screen, pg.display.get_window_size()), (0, 0))
    pg.display.flip()
  pg.quit()


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--fen", default=START_FEN)
  parser.add_argument("--vs-human", action="store_true", default=False)
  args = parser.parse_args()
  main(args.fen, args.vs_human)
