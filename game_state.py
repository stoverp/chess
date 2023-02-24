from ai import AI
from core import Board, Piece
from enums import PlayerColor, PieceType
from move_generator import MoveGenerator
from player_state import PlayerState


START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class GameState:
  def __init__(self, white_player_type, black_player_type, search_depth=1, bonuses=None, fen=START_FEN):
    self.players = {
      PlayerColor.WHITE: PlayerState(PlayerColor.WHITE, white_player_type, self),
      PlayerColor.BLACK: PlayerState(PlayerColor.BLACK, black_player_type, self)
    }
    self.board = Board()
    self.bonuses = bonuses
    self.active_player_color = PlayerColor.WHITE
    if not fen:
      fen = START_FEN
    self.init_from_fen(fen)
    # todo: handle zobrist key for custom board state
    for player in self.players.values():
      player.refresh_attack_board()
    self.move_history = []
    self.move_generator = MoveGenerator(self)
    self.ai = AI(search_depth, self)
    self.active_player().refresh_legal_moves()

  def init_from_fen(self, fen):
    piece_placement, side_to_move, castling_ability, en_passant_target_square, halfmove_clock, fullmove_counter = \
      fen.split(" ")
    for inverse_rank, rank_line in enumerate(piece_placement.split("/")):
      rank = 7 - inverse_rank
      file = 0
      for piece_char in rank_line:
        if piece_char.isdigit():
          file += int(piece_char)
        else:
          piece_type, piece_color = self.parse_piece_char(piece_char)
          piece = Piece(piece_color, piece_type, rank, file)
          self.players[piece_color].pieces[piece_type].add(piece)
          self.board[rank][file] = piece
          file += 1
    self.active_player_color = PlayerColor.WHITE if side_to_move == "w" else PlayerColor.BLACK
    self.init_castling_ability(castling_ability)

  def init_castling_ability(self, castling_ability):
    # first assume that nobody can castle by setting the king and rook move counts to something nonzero
    for color in PlayerColor:
      for piece_type in [PieceType.KING, PieceType.ROOK]:
        for piece in self.players[color].pieces[piece_type]:
          piece.n_times_moved = 1
    if castling_ability != "-":
      for piece_char in castling_ability:
        piece_type, piece_color = self.parse_piece_char(piece_char)
        # king definitely hasn't moved
        self.players[piece_color].find(PieceType.KING).n_times_moved = 0
        # find and mark appropriate rook ("k"-side or "q"-side)
        self.players[piece_color].find_rook(king_side=piece_type is PieceType.KING).n_times_moved = 0

  def parse_piece_char(self, piece_char):
    return PieceType(piece_char.lower()), PlayerColor.WHITE if piece_char.isupper() else PlayerColor.BLACK

  def active_player(self):
    return self.players[self.active_player_color]

  def generate_legal_moves(self, piece, filter_checks=True, captures_only=False):
    return self.move_generator.generate_legal_moves(piece, filter_checks, captures_only)

  def generate_all_legal_moves(self, filter_checks=True, captures_only=False):
    return self.move_generator.generate_and_mark_all_legal_moves(filter_checks, captures_only)

  def best_move(self):
    return self.ai.best_move()

  def lookup_bonus(self, piece_type, player_color, rank, file):
    if not self.bonuses:
      return 0
    return self.bonuses[piece_type][player_color][rank][file]
