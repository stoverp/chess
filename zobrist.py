import random
from collections import defaultdict
from enums import PlayerColor, PieceType


def random_64bits():
  return random.getrandbits(64)

EN_PASSANT_DISALLOWED_INDEX = 8

class Zobrist:
  random.seed(2361912)
  pieces = defaultdict(dict)
  for color in PlayerColor:
    for piece_type in PieceType:
      pieces[color][piece_type] = [[random_64bits() for _ in range(8)] for _ in range(8)]
  black_to_move = random_64bits()
  castling_rights = [random_64bits() for _ in range(16)]
  # 8 files + one more to represent "en passant disallowed"
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
    key ^= Zobrist.en_passant_file_hash(move.previous_en_passant_target_square)
    key ^= Zobrist.en_passant_file_hash(move.en_passant_target_square)
    key ^= Zobrist.castling_hash(move.original_castling_fen)
    key ^= Zobrist.castling_hash(move.castling_fen_after_move)
    return key

  @classmethod
  def en_passant_file_hash(cls, square):
    return Zobrist.en_passant_file[square[1]] if square is not None else \
      Zobrist.en_passant_file[EN_PASSANT_DISALLOWED_INDEX]

  @classmethod
  def castling_hash(cls, castle_fen):
    if castle_fen == "-":
      return Zobrist.castling_rights[0]
    fen_index = 0
    result = 0
    for right_index, right in enumerate("KQkq"):
      if castle_fen[fen_index] == right:
        result += 2 ** right_index
        fen_index += 1
        if fen_index == len(castle_fen):
          return Zobrist.castling_rights[result]
    return Zobrist.castling_rights[result]
