import re
from argparse import ArgumentParser

import pygame as pg

from engine import Engine
from enums import PlayerType, PlayerColor, PieceType
from game_state import GameState
from display import BoardDisplay


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


def endgame(game_state, board_display):
  print(f"GAME OVER!")
  if game_state.active_player().in_check():
    print(f"CHECKMATE: {game_state.active_player_color.opponent}")
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
      board_display.refresh()


def main(square_bonuses_file, search_depth, white_player_type, black_player_type, fen):
  bonuses = read_square_bonuses(square_bonuses_file)
  game_state = GameState(white_player_type, black_player_type, search_depth, bonuses, fen)
  board_display = BoardDisplay(game_state)
  engine = Engine(game_state, board_display)
  running = True
  while running:
    if not game_state.active_player().legal_moves:
      endgame(game_state, board_display)
      running = False
    if game_state.active_player().player_type is PlayerType.ROBOT:
      move = game_state.best_move()
      engine.make_move(move)
    else:
      for event in pg.event.get():
        if not engine.handle_event(event):
          running = False
    board_display.refresh()
  pg.quit()


# todo: fix queen sac on main line
if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--square-bonuses-file", default="resources/piece_square_bonuses.txt")
  parser.add_argument("--fen")
  parser.add_argument("--search-depth", type=int, default=3)
  parser.add_argument("--white-player", type=PlayerType, default=PlayerType.HUMAN)
  parser.add_argument("--black-player", type=PlayerType, default=PlayerType.ROBOT)
  args = parser.parse_args()
  main(args.square_bonuses_file, args.search_depth, args.white_player, args.black_player, args.fen)
