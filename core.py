from enums import PlayerColor, PieceType
from zobrist import Zobrist


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
  def __init__(self):
    self.squares = empty_board_array()
    self.zobrist_key = Zobrist.init_key()

  def __getitem__(self, item):
    return self.squares[item]

  def __setitem__(self, key, value):
    self.squares[key] = value

  def update_zobrist_key(self, move):
    self.zobrist_key = Zobrist.update_key(self.zobrist_key, move)

  @classmethod
  def in_bounds(cls, rank, file):
    return (0 <= rank < 8) and (0 <= file < 8)


def empty_board_array(default_value=None):
  return [[default_value for _ in range(8)] for _ in range(8)]