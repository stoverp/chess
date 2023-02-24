import random
from collections import defaultdict
from enums import PlayerColor, PieceType


def random_64bits():
  return random.getrandbits(64)


class Zobrist:
  random.seed(2361912)
  pieces = defaultdict(dict)
  for color in PlayerColor:
    for piece_type in PieceType:
      pieces[color][piece_type] = [[random_64bits() for _ in range(8)] for _ in range(8)]
  black_to_move = random_64bits()
  castling_rights = [random_64bits() for _ in range(12)]
  en_passant_file = [random_64bits() for _ in range(9)]

  @classmethod
  def init_key(cls):
    key = 0
    for color in PlayerColor:
      for piece_type in PieceType:
        for rank in range(8):
          for file in range(8):
            key ^= cls.pieces[color][piece_type][rank][file]
    for v in cls.castling_rights:
      key ^= v
    for v in cls.en_passant_file:
      key ^= v
    return key

  @classmethod
  def get_piece_hash(cls, piece, rank, file):
    return cls.pieces[piece.player_color][piece.type][rank][file]

  @classmethod
  def update_key(cls, original_key, move):
    key = original_key
    # remove old piece position
    key ^= Zobrist.get_piece_hash(move.piece, move.old_rank, move.old_file)
    if move.captured_piece:
      # remove captured piece
      key ^= Zobrist.get_piece_hash(move.captured_piece, move.captured_piece.rank, move.captured_piece.file)
    # add new piece position
    key ^= Zobrist.get_piece_hash(move.piece, move.rank, move.file)
    key ^= Zobrist.black_to_move
    # todo: handle castling rights and en passant
    return key
