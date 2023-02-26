from enum import Enum, auto

from core import Board
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
  def __init__(self, piece, rank, file, game_state, promote_type=None):
    self.piece = piece
    self.rank = rank
    self.file = file
    self.game_state = game_state
    self.promote_type = promote_type
    self.old_rank = piece.rank
    self.old_file = piece.file
    self.move_type = self.get_type()
    self.castling_rook_move = None
    self.score_guess = 0
    if self.move_type in MoveType.legal_types():
      self.captured_piece = game_state.board[rank][file]
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
      'captured_piece': self.piece.to_json() if self.piece else None,
      'score_guess': self.score_guess
    }

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
        player.find_rook(king_side=is_king_side),
        self.piece.rank,
        self.piece.file - 1 if is_king_side else self.piece.file + 1,
        self.game_state
      )
      self.castling_rook_move.apply()
    player.opponent().refresh_attack_board()
    self.game_state.board.update_zobrist_key(self)

  def unapply(self):
    if self.captured_piece:
      self.game_state.players[self.captured_piece.player_color].pieces[self.captured_piece.type].add(self.captured_piece)
    self.piece.rank = self.old_rank
    self.piece.file = self.old_file
    if self.promote_type:
      self.piece.update_type(PieceType.PAWN, self.game_state.players[self.piece.player_color].pieces)
    self.game_state.board[self.rank][self.file] = self.captured_piece
    self.game_state.board[self.old_rank][self.old_file] = self.piece
    self.piece.n_times_moved -= 1
    if self.castling_rook_move:
      self.castling_rook_move.unapply()
    # apply same update to key to revert move
    # todo: verify this works
    self.game_state.board.update_zobrist_key(self)

  def guess_score(self):
    self.score_guess = 0
    if entry := self.game_state.ai.transposition_table.from_key(self.game_state.board.zobrist_key):
      if self == entry.move:
        self.score_guess += 10000
    if self.captured_piece:
      self.score_guess = 10 * self.captured_piece.type.score - self.piece.type.score
    if self.promote_type:
      self.score_guess += self.promote_type.score
    if self.game_state.players[self.piece.player_color.opponent].attack_board.pawn_board[self.rank][self.file]:
      self.score_guess -= self.piece.type.score