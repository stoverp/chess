from collections import defaultdict

from attack_board import AttackBoard
from enums import PieceType


class PlayerState:
  def __init__(self, player_color, player_type, game_state):
    self.player_color = player_color
    self.player_type = player_type
    self.game_state = game_state
    self.pieces = defaultdict(set)
    self.legal_moves = []
    self.attack_board = AttackBoard(self)

  def in_check(self):
    king = self.find(PieceType.KING)
    return self.game_state.players[self.player_color.opponent].attack_board[king.rank][king.file]

  def find_castling_rook(self, king_side):
    for rook in self.pieces[PieceType.ROOK]:
      if king_side:
        if rook.file == 7:
          return rook
      else:
        if rook.file == 0:
          return rook
    return None

  def find(self, piece_type):
    piece_set = self.find_all(piece_type)
    if not piece_set:
      return None
    return next(iter(piece_set))

  def find_all(self, piece_type):
    return self.pieces[piece_type]

  def opponent(self):
    return self.game_state.players[self.player_color.opponent]

  def refresh_legal_moves(self, filter_checks=True):
    self.legal_moves = self.game_state.generate_all_legal_moves(self.player_color, filter_checks)

  def refresh_attack_board(self):
    self.attack_board.refresh()

  def all_pieces(self):
    return [piece for piece_type in PieceType for piece in self.pieces[piece_type]]