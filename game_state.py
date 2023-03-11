import json
import re

from ai import AI
from core import san_to_index, index_to_san
from board import Board
from piece import Piece
from enums import PlayerColor, PieceType
from move import Move
from move_generator import MoveGenerator
from player_state import PlayerState

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class GameState:
  def __init__(self, white_player_type, black_player_type, search_depth=1, bonuses_file=None, fen=START_FEN, book_file=None):
    self.players = {
      PlayerColor.WHITE: PlayerState(PlayerColor.WHITE, white_player_type, self),
      PlayerColor.BLACK: PlayerState(PlayerColor.BLACK, black_player_type, self)
    }
    self.board = Board(bonuses_file, self)
    self.active_player_color = PlayerColor.WHITE
    self.selected_piece = None
    self.en_passant_target_square = None
    if not fen:
      fen = START_FEN
    self.init_from_fen(fen)
    self.opening_book = self.read_opening_book(book_file) if book_file else None
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
    self.init_en_passant_target_square(en_passant_target_square)
    self.board.full_evaluation()

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
        self.players[piece_color].find_castling_rook(king_side=piece_type is PieceType.KING).n_times_moved = 0

  def generate_castling_ability_fen(self):
    castling_ability = ""
    for color in PlayerColor:
      if self.players[color].find(PieceType.KING).n_times_moved == 0:
        for char, king_side in [("k", True), ("q", False)]:
          rook = self.players[color].find_castling_rook(king_side)
          if rook and rook.n_times_moved == 0:
            castling_ability += char.upper() if color is PlayerColor.WHITE else char
    return castling_ability or "-"

  def generate_en_passant_fen(self):
    return index_to_san(*self.en_passant_target_square) if self.en_passant_target_square else '-'

  def generate_fen(self):
    piece_placement_ranks = []
    for rank in range(7, -1, -1):
      n_empty_squares = 0
      fen_line = []
      for file in range(8):
        piece = self.board[rank][file]
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
    return f"{'/'.join(piece_placement_ranks)} {self.active_player_color.abbr} {self.generate_castling_ability_fen()} {self.generate_en_passant_fen()} - -"

  def parse_piece_char(self, piece_char):
    return PieceType(piece_char.lower()), PlayerColor.WHITE if piece_char.isupper() else PlayerColor.BLACK

  def read_opening_book(self, book_file):
    print(f"loading opening book from '{book_file}' ...")
    opening_book = dict()
    with open(book_file, "r") as f:
      for key_string, moves in json.load(f).items():
        opening_book[int(key_string)] = [move_dict for move_dict in moves]
    return opening_book

  def active_player(self):
    return self.players[self.active_player_color]

  def generate_legal_moves(self, piece, filter_checks=True, captures_only=False):
    return self.move_generator.generate_legal_moves(piece, filter_checks, captures_only)

  def generate_all_legal_moves(self, active_player_color, filter_checks=True, captures_only=False):
    return self.move_generator.generate_and_mark_all_legal_moves(active_player_color, filter_checks, captures_only)

  def best_move(self):
    return self.ai.best_move()

  def opening_moves(self):
    moves = []
    if not self.opening_book:
      return moves
    for opening_move_json in self.opening_book.get(self.board.zobrist_key, []):
      moves.append(Move.from_json(opening_move_json, self))
    return moves

  def init_en_passant_target_square(self, square):
    if square != "-":
      self.en_passant_target_square = san_to_index(square[0], square[1])

