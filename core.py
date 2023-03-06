import re

from enums import PlayerColor, PieceType
from zobrist import Zobrist


# todo: split classes into their own files
class Piece:
  def __init__(self, player_color, type, rank, file):
    self.player_color = player_color
    self.type = type
    self.rank = rank
    self.file = file
    self.n_times_moved = 0

  def __str__(self):
    return f"Piece(player_color={self.player_color}, type={self.type}, rank={self.rank}, file={self.file})"

  def __repr__(self):
    return str(self)

  def to_json(self):
    return {
      'player_color': self.player_color,
      'type': self.type,
      'rank': self.rank,
      'file': self.file,
    }

  def fen(self):
    abbr = self.type.value
    return abbr.upper() if self.player_color is PlayerColor.WHITE else abbr

  def update_type(self, new_type, player_pieces):
    player_pieces[self.type].remove(self)
    self.type = new_type
    player_pieces[new_type].add(self)


class Board:
  def __init__(self, bonuses_file, game_state):
    self.bonuses = self.read_square_bonuses(bonuses_file) if bonuses_file else None
    self.game_state = game_state
    self.squares = empty_board_array()
    self.zobrist_key = Zobrist.init_key()
    self.evaluation = None

  def __getitem__(self, item):
    return self.squares[item]

  def __setitem__(self, key, value):
    self.squares[key] = value

  def flip_board(self, board):
    flipped_board = []
    for rank in reversed(board):
      flipped_board.append(rank)
    return flipped_board

  def read_square_bonuses(self, square_bonuses_file):
    current_piece = None
    piece_bonuses = dict()
    with open(square_bonuses_file, "r") as f:
      for line in f.readlines():
        text = line.strip()
        if not text:
          continue
        if text.isalpha():
          current_piece = PieceType(text)
          piece_bonuses[current_piece] = []
        else:
          rank = [int(v) for v in re.split(r",\s*", text)]
          piece_bonuses[current_piece].append(rank)
    piece_bonuses_for_color = dict()
    for piece, bonus_board in piece_bonuses.items():
      piece_bonuses_for_color[piece] = dict()
      piece_bonuses_for_color[piece][PlayerColor.BLACK] = piece_bonuses[piece]
      piece_bonuses_for_color[piece][PlayerColor.WHITE] = self.flip_board(piece_bonuses[piece])
    return piece_bonuses_for_color

  def lookup_bonus(self, piece_type, player_color, rank, file):
    if not self.bonuses:
      return 0
    return self.bonuses[piece_type][player_color][rank][file]

  def track(self, move, unapply=False):
    self.zobrist_key = Zobrist.update_key(self.zobrist_key, move)
    self.evaluation += (-1 if unapply else 1) * move.evaluation

  # evaluate board score for white (take negative for black)
  def full_evaluation(self):
    score = 0
    for player in self.game_state.players.values():
      for pieces in player.pieces.values():
        for piece in pieces:
          score += self.piece_evaluation(piece)
    self.evaluation = score

  def piecewise_evaluation(self, piece_type, player_color, rank, file):
    score = 0
    perspective = 1 if player_color == PlayerColor.WHITE else -1
    score += perspective * piece_type.score
    square_bonus = self.lookup_bonus(piece_type, player_color, rank, file)
    score += perspective * square_bonus
    return score

  def piece_evaluation(self, piece):
    if not piece:
      return 0
    return self.piecewise_evaluation(piece.type, piece.player_color, piece.rank, piece.file)

  def evaluate(self, move):
    return self.piece_evaluation(move.piece) - \
           self.piecewise_evaluation(move.piece.type, move.piece.player_color, move.old_rank, move.old_file) - \
           self.piece_evaluation(move.captured_piece)

  @classmethod
  def in_bounds(cls, rank, file):
    return (0 <= rank < 8) and (0 <= file < 8)


def empty_board_array(default_value=None):
  return [[default_value for _ in range(8)] for _ in range(8)]


def san_to_index(rank_string, file_string):
  rank = int(rank_string) - 1 if rank_string else None
  file = ord(file_string) - ord('a') if file_string else None
  return rank, file


def index_to_san(rank, file):
  return f"{chr(ord('a') + file)}{rank + 1}"
