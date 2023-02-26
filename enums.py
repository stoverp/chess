from enum import Enum


class PlayerType(str, Enum):
  HUMAN = 'human'
  ROBOT = 'robot'


class PlayerColor(str, Enum):
  WHITE = 'white'
  BLACK = 'black'

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


class PieceType(Enum):
  PAWN = 'p', 100
  KNIGHT = 'n', 300
  BISHOP = 'b', 320
  ROOK = 'r', 500
  QUEEN = 'q', 900
  KING = 'k', 0

  def __new__(cls, value, score):
    obj = object.__new__(cls)
    obj._value_ = value
    obj.score = score
    return obj

  @property
  def san_format(self):
    return self.value.upper()


piece_types_by_san_format = dict((pt.san_format, pt) for pt in PieceType)
