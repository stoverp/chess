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
from sortedcontainers import SortedList


SEARCH_DEPTH = 4

LIGHT_SQUARES = 0
DARK_SQUARES = 1
BACKGROUND_COLORS = [(242, 210, 133), (115, 99, 61)]
SELECTED_SQUARE_COLOR = (252, 186, 3)
LEGAL_MOVE_COLORS = [(235, 127, 132), (115, 61, 63)]
LAST_MOVE_COLORS = [(127, 235, 226), (61, 113, 115)]
ATTACKING_COLORS = [(235, 127, 201), (115, 61, 98)]

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
  def pawn_direction(self):
    return 1 if self is PlayerColor.WHITE else -1

  @property
  def opponent(self):
    return PlayerColor.BLACK if self is PlayerColor.WHITE else PlayerColor.WHITE


class PlayerState:
  def __init__(self, player_color):
    self.player_color = player_color
    self.pieces = defaultdict(set)
    self.legal_moves = []
    self.attack_board = clear_board(False)
    self.pawn_attack_board = clear_board(False)

  def in_check(self):
    king = self.find(PieceType.KING)
    return Globals.players[self.player_color.opponent].attack_board[king.rank][king.file]

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

  def opponent(self):
    return Globals.players[self.player_color.opponent]

  def refresh_legal_moves(self, filter_checks=True):
    self.legal_moves = generate_and_mark_all_legal_moves(self, filter_checks)

  def calculate_attack_boards(self):
    self.attack_board = clear_board(False)
    self.pawn_attack_board = clear_board(False)
    for piece in self.all_pieces():
      calculate_attacks(piece, self.attack_board, self.pawn_attack_board)

  def all_pieces(self):
    return [piece for piece_type in PieceType for piece in self.pieces[piece_type]]


class MoveType(Enum):
  OUT_OF_BOUNDS = auto()
  SELF_OCCUPIED = auto()
  CAPTURE = auto()
  OPEN_SQUARE = auto()

  @classmethod
  def legal_types(cls):
    return [MoveType.OPEN_SQUARE, MoveType.CAPTURE]


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
    self.surface = self.load_image()

  def __str__(self):
    return f"Piece(player_color={self.player_color}, type={self.type}, rank={self.rank}, file={self.file})"

  def __repr__(self):
    return str(self)

  def load_image(self):
    return load(f"images/Chess_{self.type.value}{self.player_color.image_abbr}t60.png")

  def fen(self):
    abbr = self.type.value
    return abbr.upper() if self.player_color is PlayerColor.WHITE else abbr

  def update_type(self, new_type):
    pieces = Globals.players[self.player_color].pieces
    pieces[self.type].remove(self)
    self.type = new_type
    self.surface = self.load_image()
    pieces[new_type].add(self)


class Move:
  def __init__(self, piece, rank, file, promote_type=None):
    self.piece = piece
    self.rank = rank
    self.file = file
    self.promote_type = promote_type
    self.old_rank = piece.rank
    self.old_file = piece.file
    self.move_type = self.get_type()
    self.castling_rook_move = None
    if self.move_type in MoveType.legal_types():
      self.captured_piece = Globals.board[rank][file]
      self.guess_score()

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

  def get_type(self):
    if not in_bounds(self.rank, self.file):
      return MoveType.OUT_OF_BOUNDS
    if piece_on_new_square := Globals.board[self.rank][self.file]:
      if self.piece.player_color == piece_on_new_square.player_color:
        return MoveType.SELF_OCCUPIED
      else:
        return MoveType.CAPTURE
    else:
      return MoveType.OPEN_SQUARE

  def apply(self):
    player = Globals.players[self.piece.player_color]
    if self.captured_piece:
      Globals.players[self.captured_piece.player_color].pieces[self.captured_piece.type].remove(self.captured_piece)
    self.piece.rank = self.rank
    self.piece.file = self.file
    if self.promote_type:
      self.piece.update_type(self.promote_type)
    Globals.board[self.old_rank][self.old_file] = None
    Globals.board[self.rank][self.file] = self.piece
    self.piece.n_times_moved += 1
    # handle castling special case
    file_diff = self.file - self.old_file
    if self.piece.type is PieceType.KING and abs(file_diff) == 2:
      is_king_side = file_diff == 2  # king moving two to the right
      self.castling_rook_move = Move(
        player.find_rook(king_side=is_king_side),
        self.piece.rank,
        self.piece.file - 1 if is_king_side else self.piece.file + 1
      )
      self.castling_rook_move.apply()
    player.opponent().calculate_attack_boards()

  def unapply(self):
    if self.captured_piece:
      Globals.players[self.captured_piece.player_color].pieces[self.captured_piece.type].add(self.captured_piece)
    self.piece.rank = self.old_rank
    self.piece.file = self.old_file
    if self.promote_type:
      self.piece.update_type(PieceType.PAWN)
    Globals.board[self.rank][self.file] = self.captured_piece
    Globals.board[self.old_rank][self.old_file] = self.piece
    self.piece.n_times_moved -= 1
    if self.castling_rook_move:
      self.castling_rook_move.unapply()

  def guess_score(self):
    self.score_guess = 0
    if self.captured_piece:
      self.score_guess = 10 * self.captured_piece.type.score - self.piece.type.score
    if self.promote_type:
      self.score_guess += self.promote_type.score
    if Globals.players[self.piece.player_color.opponent].pawn_attack_board[self.rank][self.file]:
      self.score_guess -= self.piece.type.score


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


def clear_board(default_value=None):
  return [[default_value for _ in range(8)] for _ in range(8)]


def calculate_knight_attacks(knight, attack_board):
  for far_rank in [True, False]:
    for rank_direction in [1, -1]:
      for file_direction in [1, -1]:
        rank = (2 if far_rank else 1) * rank_direction + knight.rank
        file = (1 if far_rank else 2) * file_direction + knight.file
        if empty_or_opponent_square(knight.player_color, rank, file):
          attack_board[rank][file] = True


def empty_or_opponent_square(player_color, rank, file):
  if in_bounds(rank, file):
    piece_on_square = Globals.board[rank][file]
    return not piece_on_square or piece_on_square.player_color is player_color.opponent
  return False


def calculate_king_attacks(king, attack_board):
  for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
    rank = rank_direction + king.rank
    file = file_direction + king.file
    if empty_or_opponent_square(king.player_color, rank, file):
      attack_board[rank][file] = True


def calculate_attacks(piece, attack_board, pawn_attack_board):
  if piece.type is PieceType.PAWN:
    calculate_pawn_attacks(piece, attack_board, pawn_attack_board)
  elif piece.type is PieceType.KNIGHT:
    calculate_knight_attacks(piece, attack_board)
  elif piece.type is PieceType.BISHOP:
    calculate_slide_attacks(piece, BISHOP_DIRECTIONS, attack_board)
  elif piece.type is PieceType.ROOK:
    calculate_slide_attacks(piece, ROOK_DIRECTIONS, attack_board)
  elif piece.type is PieceType.QUEEN:
    calculate_slide_attacks(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS, attack_board)
  else:  # piece.type is PieceType.KING:
    calculate_king_attacks(piece, attack_board)


def calculate_slide_attacks(piece, directions, attack_board):
  for rank_direction, file_direction in directions:
    collision = False
    distance = 1
    while not collision:
      rank = distance * rank_direction + piece.rank
      file = distance * file_direction + piece.file
      if not in_bounds(rank, file):
        collision = True
      else:
        if empty_or_opponent_square(piece.player_color, rank, file):
          attack_board[rank][file] = True
        if Globals.board[rank][file]:
          collision = True
      distance += 1


def calculate_pawn_attacks(pawn, attack_board, pawn_attack_board):
  pawn_direction = pawn.player_color.pawn_direction
  rank = pawn.rank + pawn_direction
  for file in [pawn.file + 1, pawn.file - 1]:
    if empty_or_opponent_square(pawn.player_color, rank, file):
      attack_board[rank][file] = True
      pawn_attack_board[rank][file] = True


def init_state(fen):
  Globals.board = clear_board()
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
  for player in Globals.players.values():
    player.calculate_attack_boards()


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
  move_history = []
  n_moves_searched = 0
  display_player_attacking = None
  display_pawn_attacks = None

  @classmethod
  def active_player(cls):
    return cls.players[cls.active_player_color]


def draw_squares():
  last_move = Globals.move_history[-1] if Globals.move_history else None
  for rank in range(8):
    for file in range(8):
      square_type = (rank + file) % 2
      if last_move and (rank, file) in [(last_move.old_rank, last_move.old_file), (last_move.rank, last_move.file)]:
        color = LAST_MOVE_COLORS[square_type]
      elif Globals.selected:
        if (rank, file) == (Globals.selected.piece.rank, Globals.selected.piece.file):
          color = SELECTED_SQUARE_COLOR
        elif Move(Globals.selected.piece, rank, file) in Globals.selected.legal_moves:
          color = LEGAL_MOVE_COLORS[square_type]
        else:
          color = BACKGROUND_COLORS[square_type]
      elif Globals.display_player_attacking and \
          Globals.players[Globals.display_player_attacking].attack_board[rank][file]:
        color = ATTACKING_COLORS[square_type]
      elif Globals.display_pawn_attacks and \
          Globals.players[Globals.display_pawn_attacks].pawn_attack_board[rank][file]:
        color = ATTACKING_COLORS[square_type]
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


def is_promoting_pawn(piece, new_rank):
  return piece.type is PieceType.PAWN and new_rank == piece.player_color.opponent.back_rank


def include_promotion_moves(move):
  moves = set()
  if is_promoting_pawn(move.piece, move.rank):
    for promote_type in [PieceType.QUEEN, PieceType.KNIGHT]:
      moves.add(Move(move.piece, move.rank, move.file, promote_type=promote_type))
  else:
    moves.add(move)
  return moves


def generate_pawn_moves(piece, captures_only=False):
  moves = set()
  pawn_direction = piece.player_color.pawn_direction
  # capture moves
  for rank_offset, file_offset in [(pawn_direction, 1), (pawn_direction, -1)]:
    move = Move(piece, piece.rank + rank_offset, piece.file + file_offset)
    if move.move_type is MoveType.CAPTURE:
      moves.update(include_promotion_moves(move))
  if captures_only:
    return moves
  # one-square standard move
  rank_candidates = [piece.rank + (1 * pawn_direction)]
  # two-square opening move
  if piece.rank == piece.player_color.back_rank + pawn_direction:
    # can't move through pieces
    if not Globals.board[piece.rank + (1 * pawn_direction)][piece.file]:
      rank_candidates.append(piece.rank + (2 * pawn_direction))
  for new_rank in rank_candidates:
    move = Move(piece, new_rank, piece.file)
    if move.move_type is MoveType.OPEN_SQUARE:
      moves.update(include_promotion_moves(move))
  # todo: en passant
  return moves


def generate_slide_moves(piece, directions, captures_only=False):
  moves = set()
  for rank_direction, file_direction in directions:
    collision = False
    distance = 1
    while not collision:
      move = Move(piece, distance * rank_direction + piece.rank, distance * file_direction + piece.file)
      if move.move_type in (MoveType.SELF_OCCUPIED, MoveType.OUT_OF_BOUNDS):
        collision = True
      else:
        add_move_if_valid(move, moves, captures_only)
        if move.move_type is MoveType.CAPTURE:
          collision = True
      distance += 1
  return moves


def add_move_if_valid(move, moves, captures_only):
  if move.move_type is MoveType.CAPTURE:
    moves.add(move)
  elif not captures_only and move.move_type is MoveType.OPEN_SQUARE:
    moves.add(move)


def generate_knight_moves(piece, captures_only=False):
  moves = set()
  for far_rank in [True, False]:
    for rank_direction in [1, -1]:
      for file_direction in [1, -1]:
        move = Move(
          piece,
          (2 if far_rank else 1) * rank_direction + piece.rank,
          (1 if far_rank else 2) * file_direction + piece.file
        )
        add_move_if_valid(move, moves, captures_only)
  return moves


def castling_moves(king, filter_checks):
  moves = set()
  if king.n_times_moved == 0:
    player = Globals.players[king.player_color]
    for rook in player.pieces[PieceType.ROOK]:
      if rook.n_times_moved == 0:
        can_castle = True
        new_file = king.file + 2 if rook.file - king.file > 0 else king.file - 2
        small_file, big_file = sorted([king.file, rook.file])
        for file_between in range(small_file + 1, big_file):
          if Globals.board[king.rank][file_between]:
            can_castle = False
            break
        if can_castle:
          if filter_checks:
            if player.in_check():
              can_castle = False
            else:
              # make a fake king move to the space between
              fake_move = Move(king, king.rank, king.file + 1 if rook.file - king.file > 0 else king.file - 1)
              fake_move.apply()
              if player.in_check():
                # player would be castling through check
                can_castle = False
              fake_move.unapply()
          if can_castle:
            moves.add(Move(king, king.rank, new_file))
  return moves


def generate_king_moves(king: Piece, filter_checks=True, captures_only=False):
  moves = set()
  for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
    move = Move(king, rank_direction + king.rank, file_direction + king.file)
    add_move_if_valid(move, moves, captures_only)
  moves.update(castling_moves(king, filter_checks))
  return moves


def generate_legal_moves(piece, filter_checks=True, captures_only=False):
  if piece.type is PieceType.PAWN:
    moves = generate_pawn_moves(piece, captures_only)
  elif piece.type is PieceType.KNIGHT:
    moves = generate_knight_moves(piece, captures_only)
  elif piece.type is PieceType.BISHOP:
    moves = generate_slide_moves(piece, BISHOP_DIRECTIONS, captures_only)
  elif piece.type is PieceType.ROOK:
    moves = generate_slide_moves(piece, ROOK_DIRECTIONS, captures_only)
  elif piece.type is PieceType.QUEEN:
    moves = generate_slide_moves(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS, captures_only)
  else:  # piece.type is PieceType.KING:
    moves = generate_king_moves(piece, filter_checks, captures_only)
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


def generate_and_mark_all_legal_moves(player, filter_checks=True, captures_only=False):
  # player.reset_attack_maps()
  # keep move list in sorted order by score guess
  all_legal_moves = SortedList(key=lambda t: t[0])
  for pieces in player.pieces.values():
    for piece in pieces:
      for move in generate_legal_moves(piece, filter_checks, captures_only):
        # if piece.type is not PieceType.PAWN or move.move_type is MoveType.CAPTURE:
        #   player.attack_board[move.rank][move.file] = True
        all_legal_moves.add((move.score_guess, move))
  # return high scores first
  return [move for score_guess, move in reversed(all_legal_moves)]


def make_move(move):
  move.apply()
  Globals.move_history.append(move)
  # todo: this call is just to update the last player's attack map, so it's correct for the opponent
  # Globals.active_player().refresh_legal_moves()
  Globals.active_player().calculate_attack_boards()
  Globals.active_player_color = Globals.active_player_color.opponent
  Globals.active_player().refresh_legal_moves()


def undo_last_move():
  if Globals.move_history:
    move = Globals.move_history.pop()
    move.unapply()
    # todo: next line might be unnecessary
    # Globals.active_player().refresh_legal_moves()
    Globals.active_player().calculate_attack_boards()
    Globals.active_player_color = Globals.active_player_color.opponent
    Globals.active_player().refresh_legal_moves()


def evaluate_board(active_player_color):
  score = 0
  for player in Globals.players.values():
    perspective = 1 if player.player_color == active_player_color else -1
    for pieces in player.pieces.values():
      for piece in pieces:
        score += perspective * piece.type.score
  return score


def quiesce(active_player_color, alpha, beta):
  score = evaluate_board(active_player_color)
  if score >= beta:
    return None, beta
  alpha = max(alpha, score)
  moves = generate_and_mark_all_legal_moves(Globals.players[active_player_color],
    filter_checks=True, captures_only=True)
  top_move = None
  for move in moves:
    Globals.n_moves_searched += 1
    move.apply()
    _, score = quiesce(active_player_color.opponent, -beta, -alpha)
    # negate score to reflect opponent's perspective
    score = -score
    move.unapply()
    if score >= beta:
      # beta limit tells us opponent can prevent this scenario
      return None, beta
    if score > alpha:
      top_move = move
      alpha = score
  return top_move, alpha


def search_moves(active_player_color, depth, alpha, beta):
  if depth == 0:
    return quiesce(active_player_color, alpha, beta)
    # return None, evaluate_board(active_player_color)
  moves = generate_and_mark_all_legal_moves(Globals.players[active_player_color], filter_checks=True)
  if not moves:
    if Globals.active_player().in_check():
      return None, -math.inf
    else:
      return None, 0
  top_move = None
  for move in moves:
    # if move.rank == 5 and move.file == 0 and move.captured_piece:
    #   print(f"evaluating {move} ...")
    Globals.n_moves_searched += 1
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
  Globals.n_moves_searched = 0
  print(f"\ncalculating {active_player_color} move ...")
  start_time = time.time()
  move, score = search_moves(active_player_color, SEARCH_DEPTH, -math.inf, math.inf)
  print(f"evaluated score {score} by searching {Globals.n_moves_searched} moves in {time.time() - start_time} seconds for {move}")
  if move:
    return move
  else:
    move = Globals.active_player().legal_moves[0]
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
      if event.type == pg.QUIT:
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


def get_user_promote_type():
  # todo: prompt for piece type
  return PieceType.QUEEN


def toggle_attack_display(player_color):
  if Globals.display_player_attacking is player_color:
    Globals.display_player_attacking = None
  else:
    Globals.display_pawn_attacks = None
    Globals.display_player_attacking = player_color
    print(f"\nDISPLAYING {player_color.name.upper()} ATTACK MAP.")


def toggle_pawn_attack_display(player_color):
  if Globals.display_pawn_attacks is player_color:
    Globals.display_pawn_attacks = None
  else:
    Globals.display_player_attacking = None
    Globals.display_pawn_attacks = player_color
    print(f"\nDISPLAYING {player_color.name.upper()} PAWN ATTACK MAP.")


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
      if is_promoting_pawn(Globals.selected.piece, rank):
        move = Move(Globals.selected.piece, rank, file, promote_type=get_user_promote_type())
      else:
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
    if event.unicode.lower() == "u":
      if vs_human:
        undo_last_move()
      else:
        # disable undo while computer is thinking
        if Globals.active_player_color is PlayerColor.WHITE:
          # undo last black + white moves, so white is still active
          undo_last_move()
          undo_last_move()
    elif event.unicode.lower() == "f":
      print(f"\nCURRENT BOARD FEN: {generate_fen()}")
    elif event.unicode.lower() == "w":
      toggle_attack_display(PlayerColor.WHITE)
    elif event.unicode.lower() == "b":
      toggle_attack_display(PlayerColor.BLACK)
    elif event.unicode == "P":
      toggle_pawn_attack_display(PlayerColor.WHITE)
    elif event.unicode == "p":
      toggle_pawn_attack_display(PlayerColor.BLACK)
  return True


def main(fen, vs_human):
  pg.init()
  Globals.displayed_screen = set_mode((DISPLAY_WIDTH, DISPLAY_WIDTH), pg.RESIZABLE)
  Globals.screen = pg.Surface((BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH))
  init_state(fen)
  Globals.active_player().refresh_legal_moves()
  running = True
  while running:
    if not Globals.active_player().legal_moves:
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
