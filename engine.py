import pygame as pg

from core import Board
from display import display_coords_to_screen, get_square
from enums import PieceType, PlayerType, PlayerColor
from move import Move
from logging import Logging


class SelectedPiece:
  def __init__(self, piece, display_pos, game_state):
    self.piece = piece
    self.update_screen_pos(display_pos)
    self.legal_moves = game_state.move_generator.generate_legal_moves(piece)

  def __str__(self):
    return f"Selected(piece={self.piece}, screen_pos={self.screen_pos}, legal_moves={self.legal_moves})"

  def __repr__(self):
    return str(self)

  def update_screen_pos(self, display_pos):
    self.screen_pos = display_coords_to_screen(display_pos)

  def lookup_legal_move(self, move):
    for legal_move in self.legal_moves:
      if move == legal_move:
        return legal_move
    return None


class Engine:
  def __init__(self, game_state, board_display):
    self.game_state = game_state
    self.board_display = board_display

  def make_move(self, move):
    move.apply()
    self.game_state.move_history.append(move)
    # Globals.active_player().refresh_legal_moves()
    self.game_state.active_player_color = self.game_state.active_player_color.opponent
    self.game_state.active_player().refresh_legal_moves()
    # todo: this call is just to update the last player's attack map, so it's correct for the opponent
    self.game_state.active_player().opponent().refresh_attack_board()
    if Logging.verbose:
      self.print_stats()

  def undo_last_move(self):
    if self.game_state.move_history:
      move = self.game_state.move_history.pop()
      move.unapply()
      # todo: next line might be unnecessary
      # self.active_player().refresh_legal_moves()
      self.game_state.active_player().refresh_attack_board()
      self.game_state.active_player_color = self.game_state.active_player_color.opponent
      self.game_state.active_player().refresh_legal_moves()
      print(f"zobrist key after undo move: {self.game_state.board.zobrist_key}")

  def print_stats(self):
    print("\nCURRENT STATE")
    print(f"\tzobrist key: {self.game_state.board.zobrist_key}")
    print(f"\tfen string: {self.game_state.generate_fen()}")
    print(f"\ttranspositions evaluated: {self.game_state.ai.transposition_table.n_transpositions_evaluated}")

  def get_user_promote_type(self):
    # todo: prompt for piece type
    return PieceType.QUEEN

  # todo: this probably shouldn't be exposed to clients
  # figure out where to initialize the event listener, and keep this method with it
  # right now, the event listener loop is in main.py
  def handle_event(self, event):
    if event.type == pg.QUIT:
      return False
    elif event.type == pg.MOUSEBUTTONDOWN:
      rank, file = get_square(event.pos)
      if Board.in_bounds(rank, file):
        if piece := self.game_state.board[rank][file]:
          if piece.player_color == self.game_state.active_player_color:
            self.game_state.selected_piece = SelectedPiece(piece, event.pos, self.game_state)
    elif event.type == pg.MOUSEBUTTONUP:
      if self.game_state.selected_piece and event.pos:
        rank, file = get_square(event.pos)
        if self.game_state.move_generator.is_promoting_pawn(self.game_state.selected_piece.piece, rank):
          move = Move(self.game_state.selected_piece.piece, rank, file, self.game_state,
            promote_type=self.get_user_promote_type())
        else:
          move = Move(self.game_state.selected_piece.piece, rank, file, self.game_state)
        if legal_move := self.game_state.selected_piece.lookup_legal_move(move):
          self.make_move(legal_move)
        else:
          Logging.debug(f"attempted move to ({rank}, {file}) is illegal for {self.game_state.selected_piece}!")
        self.game_state.selected_piece = None
    elif event.type == pg.MOUSEMOTION:
      if self.game_state.selected_piece:
        self.game_state.selected_piece.update_screen_pos(event.pos)
    elif event.type == pg.KEYDOWN:
      if event.unicode.lower() == "u":
        # disable undo while computer is thinking
        if self.game_state.active_player().player_type is PlayerType.HUMAN:
          if self.game_state.active_player().opponent().player_type is PlayerType.ROBOT:
            # undo last robot + human moves, so human is still active
            self.undo_last_move()
            self.undo_last_move()
          else:
            self.undo_last_move()
      elif event.unicode.lower() == "f":
        print(f"\nCURRENT BOARD FEN: {self.game_state.generate_fen()}")
      elif event.unicode.lower() == "w":
        self.board_display.toggle_attack_display(PlayerColor.WHITE)
      elif event.unicode.lower() == "b":
        self.board_display.toggle_attack_display(PlayerColor.BLACK)
      elif event.unicode == "P":
        self.board_display.toggle_pawn_attack_display(PlayerColor.WHITE)
      elif event.unicode == "p":
        self.board_display.toggle_pawn_attack_display(PlayerColor.BLACK)
    return True

