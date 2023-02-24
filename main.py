import os
import os
import re
from argparse import ArgumentParser
from collections import defaultdict

import pygame as pg
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect

from ai import AI
from core import Board
from enums import PlayerType, PlayerColor, PieceType
from game_state import GameState
from move import Move

LIGHT_SQUARES = 0
DARK_SQUARES = 1
BACKGROUND_COLORS = [(235, 236, 208), (119, 149, 86)]
SELECTED_SQUARE_COLOR = (252, 186, 3)
LEGAL_MOVE_COLORS = [(235, 127, 132), (115, 61, 63)]
LAST_MOVE_COLORS = [(127, 235, 226), (61, 113, 115)]
ATTACKING_COLORS = [(235, 127, 201), (115, 61, 98)]

# todo: limit window resizing to preserve aspect ratio
DISPLAY_WIDTH = 1120
BOARD_PIXEL_WIDTH = 560
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

os.environ['SDL_VIDEO_WINDOW_POS'] = "300, 100"


class PieceSprites:
  sprites = defaultdict(dict)
  for piece_type in PieceType:
    for color in PlayerColor:
      sprites[piece_type][color] = load(f"images/Chess_{piece_type.value}{color.image_abbr}t60.png")

  @classmethod
  def surface(cls, piece):
    return cls.sprites[piece.type][piece.player_color]


class Selected:
  def __init__(self, piece, display_pos):
    self.piece = piece
    self.update_screen_pos(display_pos)
    self.legal_moves = Globals.game_state.move_generator.generate_legal_moves(piece)

  def __str__(self):
    return f"Selected(piece={self.piece}, screen_pos={self.screen_pos}, legal_moves={self.legal_moves})"

  def __repr__(self):
    return str(self)

  def update_screen_pos(self, display_pos):
    self.screen_pos = display_to_screen(display_pos)


def display_to_screen(display_pos):
  window_width, window_height = pg.display.get_window_size()
  width_scale = window_width / BOARD_PIXEL_WIDTH
  height_scale = window_height / BOARD_PIXEL_WIDTH
  return display_pos[0] / width_scale, display_pos[1] / height_scale


# todo: consider replacing by passing around local state, after modularization
class Globals:
  game_state = None
  # todo: break out display stuff into components
  displayed_screen = None
  screen = None
  selected = None
  display_player_attacking = None
  display_pawn_attacks = None


def draw_squares():
  last_move = Globals.game_state.move_history[-1] if Globals.game_state.move_history else None
  for rank in range(8):
    for file in range(8):
      square_type = (rank + file) % 2
      if last_move and (rank, file) in [(last_move.old_rank, last_move.old_file), (last_move.rank, last_move.file)]:
        color = LAST_MOVE_COLORS[square_type]
      elif Globals.selected:
        if (rank, file) == (Globals.selected.piece.rank, Globals.selected.piece.file):
          color = SELECTED_SQUARE_COLOR
        elif Move(Globals.selected.piece, rank, file, Globals.game_state) in Globals.selected.legal_moves:
          color = LEGAL_MOVE_COLORS[square_type]
        else:
          color = BACKGROUND_COLORS[square_type]
      elif Globals.display_player_attacking and \
          Globals.game_state.players[Globals.display_player_attacking].attack_board[rank][file]:
        color = ATTACKING_COLORS[square_type]
      elif Globals.display_pawn_attacks and \
          Globals.game_state.players[Globals.display_pawn_attacks].pawn_attack_board[rank][file]:
        color = ATTACKING_COLORS[square_type]
      else:
        color = BACKGROUND_COLORS[square_type]
      pg.draw.rect(Globals.screen, color, Rect(get_screen_pos(rank, file), (SQUARE_WIDTH, SQUARE_WIDTH)))


def draw_pieces():
  for rank in range(8):
    for file in range(8):
      if Globals.selected and (rank, file) == (Globals.selected.piece.rank, Globals.selected.piece.file):
        Globals.screen.blit(PieceSprites.surface(Globals.selected.piece), (
          Globals.selected.screen_pos[0] - (IMAGE_WIDTH // 2), Globals.selected.screen_pos[1] - (IMAGE_WIDTH // 2)
        ))
      elif piece := Globals.game_state.board[rank][file]:
        Globals.screen.blit(PieceSprites.surface(piece), (
          piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
          (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
        ))


def get_square(display_pos):
  screen_pos = display_to_screen(display_pos)
  return int((BOARD_PIXEL_WIDTH - screen_pos[1]) / SQUARE_WIDTH), int(screen_pos[0] / SQUARE_WIDTH)


def get_screen_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def print_stats():
  print("\nCURRENT STATE")
  print(f"\tzobrist key: {Globals.game_state.board.zobrist_key}")
  print(f"\tfen string: {generate_fen()}")
  print(f"\ttranspositions evaluated: {Globals.game_state.ai.transposition_table.n_transpositions_evaluated}")


def make_move(move):
  move.apply()
  Globals.game_state.move_history.append(move)
  # todo: this call is just to update the last player's attack map, so it's correct for the opponent
  # Globals.active_player().refresh_legal_moves()
  Globals.game_state.active_player().refresh_attack_board()
  Globals.game_state.active_player_color = Globals.game_state.active_player_color.opponent
  Globals.game_state.active_player().refresh_legal_moves()
  print_stats()


def undo_last_move():
  if Globals.game_state.move_history:
    move = Globals.game_state.move_history.pop()
    move.unapply()
    # todo: next line might be unnecessary
    # Globals.active_player().refresh_legal_moves()
    Globals.game_state.active_player().refresh_attack_board()
    Globals.game_state.active_player_color = Globals.game_state.active_player_color.opponent
    Globals.game_state.active_player().refresh_legal_moves()
    print(f"zobrist key after undo move: {Globals.game_state.zobrist_key}")


def endgame():
  print(f"GAME OVER!")
  if Globals.game_state.active_player().in_check():
    print(f"CHECKMATE: {Globals.game_state.active_player_color.opponent}")
  else:
    print(f"STALEMATE")
  waiting = True
  print("Press any key to exit.")
  while waiting:
    for event in pg.event.get():
      if event.type == pg.KEYDOWN:
        waiting = False
      if event.type == pg.QUIT:
        waiting = False
      refresh_display()


def generate_castling_ability_fen():
  castling_ability = ""
  for color in PlayerColor:
    if Globals.game_state.players[color].find(PieceType.KING).n_times_moved == 0:
      for char, king_side in [("k", True), ("q", False)]:
        rook = Globals.game_state.players[color].find_rook(king_side)
        if rook and rook.n_times_moved == 0:
          castling_ability += char.upper() if color is PlayerColor.WHITE else char
  return castling_ability or "-"


def generate_fen():
  piece_placement_ranks = []
  for rank in range(7, -1, -1):
    n_empty_squares = 0
    fen_line = []
    for file in range(8):
      piece = Globals.game_state.board[rank][file]
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
  return f"{'/'.join(piece_placement_ranks)} {Globals.game_state.active_player_color.abbr} {generate_castling_ability_fen()} - - -"


def get_user_promote_type():
  # todo: prompt for piece type
  return PieceType.QUEEN


def toggle_attack_display(player_color):
  if Globals.display_player_attacking is player_color:
    Globals.display_player_attacking = None
  else:
    Globals.display_pawn_attacks = None
    Globals.display_player_attacking = player_color
    print(f"\nDISPLAYING {player_color.name.upper()} ATTACK MAP.")


def toggle_pawn_attack_display(player_color):
  if Globals.display_pawn_attacks is player_color:
    Globals.display_pawn_attacks = None
  else:
    Globals.display_player_attacking = None
    Globals.display_pawn_attacks = player_color
    print(f"\nDISPLAYING {player_color.name.upper()} PAWN ATTACK MAP.")


def handle_event(event):
  if event.type == pg.QUIT:
    return False
  elif event.type == pg.MOUSEBUTTONDOWN:
    rank, file = get_square(event.pos)
    if Board.in_bounds(rank, file):
      if piece := Globals.game_state.board[rank][file]:
        if piece.player_color == Globals.game_state.active_player_color:
          Globals.selected = Selected(piece, event.pos)
  elif event.type == pg.MOUSEBUTTONUP:
    if Globals.selected and event.pos:
      rank, file = get_square(event.pos)
      if Globals.game_state.move_generator.is_promoting_pawn(Globals.selected.piece, rank):
        move = Move(Globals.selected.piece, rank, file, Globals.game_state, promote_type=get_user_promote_type())
      else:
        move = Move(Globals.selected.piece, rank, file, Globals.game_state)
      if move in Globals.selected.legal_moves:
        make_move(move)
      else:
        print(f"attempted move to ({rank}, {file}) is illegal for {Globals.selected}!")
      Globals.selected = None
  elif event.type == pg.MOUSEMOTION:
    if Globals.selected:
      Globals.selected.update_screen_pos(event.pos)
  elif event.type == pg.KEYDOWN:
    if event.unicode.lower() == "u":
      # disable undo while computer is thinking
      if Globals.game_state.active_player().player_type is PlayerType.HUMAN:
        if Globals.game_state.active_player().opponent().player_type is PlayerType.ROBOT:
          # undo last robot + human moves, so human is still active
          undo_last_move()
          undo_last_move()
        else:
          undo_last_move()
    elif event.unicode.lower() == "f":
      print(f"\nCURRENT BOARD FEN: {generate_fen()}")
    elif event.unicode.lower() == "w":
      toggle_attack_display(PlayerColor.WHITE)
    elif event.unicode.lower() == "b":
      toggle_attack_display(PlayerColor.BLACK)
    elif event.unicode == "P":
      toggle_pawn_attack_display(PlayerColor.WHITE)
    elif event.unicode == "p":
      toggle_pawn_attack_display(PlayerColor.BLACK)
  return True


def refresh_display():
  draw_squares()
  draw_pieces()
  Globals.displayed_screen.blit(pg.transform.scale(Globals.screen, pg.display.get_window_size()), (0, 0))
  pg.display.flip()


def flip_board(board):
  flipped_board = []
  for rank in reversed(board):
    flipped_board.append(rank)
  return flipped_board


def read_square_bonuses(square_bonuses_file):
  current_piece = None
  piece_bonuses = dict()
  with open(square_bonuses_file, "r") as f:
    for line in f.readlines():
      text = line.strip()
      if not text:
        continue
      if text.isalpha():
        current_piece = PieceType(text)
        piece_bonuses[current_piece] = []
      else:
        rank = [int(v) for v in re.split(r",\s*", text)]
        piece_bonuses[current_piece].append(rank)
  piece_bonuses_for_color = dict()
  for piece, bonus_board in piece_bonuses.items():
    piece_bonuses_for_color[piece] = dict()
    piece_bonuses_for_color[piece][PlayerColor.BLACK] = piece_bonuses[piece]
    piece_bonuses_for_color[piece][PlayerColor.WHITE] = flip_board(piece_bonuses[piece])
  return piece_bonuses_for_color


def main(square_bonuses_file, search_depth, fen, white_player_type, black_player_type):
  pg.init()
  Globals.displayed_screen = set_mode((DISPLAY_WIDTH, DISPLAY_WIDTH), pg.RESIZABLE)
  Globals.screen = pg.Surface((BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH))
  bonuses = read_square_bonuses(square_bonuses_file)
  Globals.game_state = GameState(search_depth, fen, white_player_type, black_player_type, bonuses)
  running = True
  while running:
    if not Globals.game_state.active_player().legal_moves:
      endgame()
      running = False
    if Globals.game_state.active_player().player_type is PlayerType.ROBOT:
      move = Globals.game_state.best_move()
      make_move(move)
    else:
      for event in pg.event.get():
        if not handle_event(event):
          running = False
    refresh_display()
  pg.quit()


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--square-bonuses-file", default="resources/piece_square_bonuses.txt")
  parser.add_argument("--fen", default=START_FEN)
  parser.add_argument("--search-depth", type=int, default=3)
  parser.add_argument("--white-player", type=PlayerType, default=PlayerType.HUMAN)
  parser.add_argument("--black-player", type=PlayerType, default=PlayerType.ROBOT)
  args = parser.parse_args()
  main(args.square_bonuses_file, args.search_depth, args.fen, args.white_player, args.black_player)
