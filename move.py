from enum import Enum, auto
from math import copysign

from board import Board
from core import index_to_san, file_to_san, rank_to_san
from enums import PieceType


class MoveType(Enum):
  OUT_OF_BOUNDS = auto()
  SELF_OCCUPIED = auto()
  CAPTURE = auto()
  OPEN_SQUARE = auto()

  @classmethod
  def legal_types(cls):
    return [MoveType.OPEN_SQUARE, MoveType.CAPTURE]


class Move:
  def __init__(self, piece, rank, file, game_state, promote_type=None, move_type=None, captured_piece=None,
        score_guess=None):
    self.piece = piece
    self.rank = rank
    self.file = file
    self.game_state = game_state
    self.promote_type = promote_type
    self.old_rank = piece.rank
    self.old_file = piece.file
    self.castling_rook_move = None
    self.move_type = move_type or self.get_type()
    self.captured_piece = captured_piece
    self.score_guess = score_guess
    if self.move_type in MoveType.legal_types():
      # we can find the captured piece and score guess if the move is legal
      if not self.captured_piece:
        self.captured_piece = game_state.board[rank][file]
      if not self.score_guess:
        self.score_guess = self.guess_score()
    self.en_passant_target_square = self.compute_en_passant()
    self.previous_en_passant_target_square = self.game_state.en_passant_target_square
    self.original_castling_fen = self.game_state.generate_castling_ability_fen()
    self.castling_fen_after_move = None
    self.evaluation = None
    self.san = None

  def __str__(self):
    return f"Move(piece={self.piece}, rank={self.rank}, file={self.file}, captured_piece={self.captured_piece}, old_rank={self.old_rank}, old_file={self.old_file}, promote_type={self.promote_type})"

  def __repr__(self):
    return str(self)

  def __eq__(self, other):
    if not other:
      return False
    return self.piece == other.piece and self.promote_type == other.promote_type and self.rank == other.rank and self.file == other.file

  def __hash__(self):
    return hash(repr(self))

  def to_san(self, player):
    if self.piece.type is PieceType.PAWN:
      san = self.to_pawn_san()
    else:
      san = self.to_non_pawn_san(player)
    return san + ('+' if player.opponent().in_check() else '')

  def to_json(self):
    return {
      'piece': self.piece.to_json(),
      'rank': self.rank,
      'file': self.file,
      'promote_type': self.promote_type,
      'old_rank': self.old_rank,
      'old_file': self.old_file,
      'move_type': self.move_type,
      'castling_rook_move': self.castling_rook_move.to_json() if self.castling_rook_move else None,
      'captured_piece': self.captured_piece.to_json() if self.captured_piece else None,
      'score_guess': self.score_guess
    }

  @staticmethod
  def from_json(json, game_state):
    return Move(
      game_state.board[json['old_rank']][json['old_file']],
      json['rank'],
      json['file'],
      game_state,
      json['promote_type'],
      json['move_type'],
      game_state.board[json['captured_piece']['rank']][json['captured_piece']['file']]
          if json['captured_piece'] else None,
      json['score_guess'])

  def get_type(self):
    if not Board.in_bounds(self.rank, self.file):
      return MoveType.OUT_OF_BOUNDS
    if piece_on_new_square := self.game_state.board[self.rank][self.file]:
      if self.piece.player_color == piece_on_new_square.player_color:
        return MoveType.SELF_OCCUPIED
      else:
        return MoveType.CAPTURE
    else:
      return MoveType.OPEN_SQUARE

  def apply(self):
    player = self.game_state.players[self.piece.player_color]
    if self.captured_piece:
      self.game_state.players[self.captured_piece.player_color].pieces[self.captured_piece.type].remove(self.captured_piece)
      # do this explicitly to handle en passant captures (new piece doesn't cover captured square)
      self.game_state.board[self.captured_piece.rank][self.captured_piece.file] = None
    # track en passant possibility
    self.game_state.en_passant_target_square = self.en_passant_target_square
    self.piece.rank = self.rank
    self.piece.file = self.file
    if self.promote_type:
      self.piece.update_type(self.promote_type, self.game_state.players[self.piece.player_color].pieces)
    self.game_state.board[self.old_rank][self.old_file] = None
    self.game_state.board[self.rank][self.file] = self.piece
    self.piece.n_times_moved += 1
    # handle castling special case
    file_diff = self.file - self.old_file
    if self.piece.type is PieceType.KING and abs(file_diff) == 2:
      is_king_side = file_diff == 2  # king moving two to the right
      self.castling_rook_move = Move(
        player.find_castling_rook(king_side=is_king_side),
        self.piece.rank,
        self.piece.file - 1 if is_king_side else self.piece.file + 1,
        self.game_state
      )
      self.castling_rook_move.apply()
    self.castling_fen_after_move = self.game_state.generate_castling_ability_fen()
    player.opponent().refresh_attack_board()
    # todo: doing this for SAN in-check notation only, do we need it?
    # player.refresh_attack_board()
    self.evaluation = self.game_state.board.evaluate(self)
    self.game_state.board.track(self)
    if not self.san:
      self.san = self.to_san(player)

  def unapply(self):
    if self.castling_rook_move:
      self.castling_rook_move.unapply()
    if self.promote_type:
      self.piece.update_type(PieceType.PAWN, self.game_state.players[self.piece.player_color].pieces)
    # revert en passant possibility
    self.game_state.en_passant_target_square = self.previous_en_passant_target_square
    # return piece to starting square
    self.piece.rank = self.old_rank
    self.piece.file = self.old_file
    self.game_state.board[self.rank][self.file] = None
    self.game_state.board[self.old_rank][self.old_file] = self.piece
    # restore captured piece
    if self.captured_piece:
      self.game_state.players[self.captured_piece.player_color].pieces[self.captured_piece.type].add(self.captured_piece)
      # do this explicitly to handle en passant captures (new piece doesn't cover captured square)
      self.game_state.board[self.captured_piece.rank][self.captured_piece.file] = self.captured_piece
    self.piece.n_times_moved -= 1
    self.game_state.players[self.piece.player_color].opponent().refresh_attack_board()
    # apply same update to key to revert move
    self.game_state.board.track(self, unapply=True)

  def guess_score(self):
    score_guess = 0
    if entry := self.game_state.ai.transposition_table.from_key(self.game_state.board.zobrist_key):
      if self == entry.move:
        score_guess += 10000
    if self.captured_piece:
      score_guess = 10 * self.captured_piece.type.score - self.piece.type.score
    if self.promote_type:
      score_guess += self.promote_type.score
    if self.game_state.players[self.piece.player_color.opponent].attack_board.pawn_board[self.rank][self.file]:
      score_guess -= self.piece.type.score
    return score_guess

  def compute_en_passant(self):
    if self.piece.type is PieceType.PAWN and abs(self.rank - self.old_rank) == 2:
      return self.rank - int(copysign(1, self.rank - self.old_rank)), self.file
    else:
      return None

  def to_pawn_san(self):
    return (file_to_san(self.old_file) if self.captured_piece else '') + \
           ('x' if self.captured_piece else '') + \
           index_to_san(self.rank, self.file) + \
           (('=' + self.promote_type.value.upper()) if self.promote_type else '')

  def to_non_pawn_san(self, player):
    n_legal_from_rank = 1
    n_legal_from_file = 1
    for legal_move in player.legal_moves:
      if legal_move.piece.type == self.piece.type and (self.rank, self.file) == (legal_move.rank, legal_move.file):
        if self.old_rank != legal_move.old_rank:
          n_legal_from_rank += 1
        if self.old_file != legal_move.old_file:
          n_legal_from_file += 1
    if n_legal_from_file > 1:
      from_san = file_to_san(self.old_file)
    elif n_legal_from_rank > 1:
      from_san = rank_to_san(self.old_rank)
    else:
      from_san = ''
    return self.piece.type.value.upper() + \
           from_san + \
           ('x' if self.captured_piece else '') + \
           index_to_san(self.rank, self.file)
