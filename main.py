import re
from argparse import ArgumentParser

import yappi

import pygame as pg
import pygame.display

from core import san_to_index
from display import BoardDisplay
from engine import Engine
from enums import PlayerType
from game_state import GameState
from chess_logger import Logging
from flask import Flask
from book_processor import parse_move


app = Flask(__name__)


class Globals:
  game_state = None
  board_display = None
  engine = None


@app.route("/")
def home():
  return "Welcome to PNS Chess!\n"


@app.route("/san_move/<move_string>")
def make_san_move(move_string):
  move = parse_move(move_string, Globals.game_state)
  print(f"parsed move string {move_string} to {move}, making move ...")
  Globals.engine.make_move(move)
  Globals.board_display.refresh()
  pygame.display.update()
  return f"processed move: {move_string}\n"


@app.route("/move/<move_string>")
def make_uci_move(move_string):
  game_state = Globals.game_state
  engine = Globals.engine
  if match := re.match(r"([a-h])([1-8])([a-h])([1-8])", move_string):
    print(match.group(1), match.group(2), match.group(3), match.group(4))
    print(f"parsed move {move_string}, finding legal moves ...")
    legal_moves = game_state.generate_all_legal_moves(game_state.active_player_color)
    print("legal moves:", legal_moves)
    for move in legal_moves:
      if (san_to_index(match.group(2), match.group(1)), san_to_index(match.group(4), match.group(3))) == \
          ((move.old_rank, move.old_file), (move.rank, move.file)):
        print(f"making legal move: {move} ...")
        engine.make_move(move)
        # Globals.board_display.refresh()
        # pygame.display.update()
        move = game_state.best_move()
        engine.make_move(move)
        return f"made human move: {move_string}, computer move: {move.to_uci()}\n"
    return f"move {move_string} is not legal", 400
  else:
    return f"invalid move: {move_string}", 400


def main(search_depth, white_player_type, black_player_type, bonuses_file, fen, book_file):
  Globals.game_state = GameState(white_player_type, black_player_type, search_depth, bonuses_file, fen, book_file)
  # Globals.board_display = BoardDisplay(Globals.game_state)
  Globals.engine = Engine(Globals.game_state, Globals.board_display)
  Globals.engine.print_stats()
  # running = True
  # while running:
  #   if not game_state.active_player().legal_moves:
  #     engine.endgame()
  #     running = False
  #   if game_state.active_player().player_type is PlayerType.ROBOT:
  #     for event in pg.event.get():
  #       if event.type == pg.QUIT:
  #         running = False
  #     move = game_state.best_move()
  #     engine.make_move(move)
  #     engine.print_stats()
  #     pygame.display.update()
  #   else:
  #     for event in pg.event.get():
  #       if not engine.handle_event(event):
  #         running = False
  #   board_display.refresh()
  # Globals.board_display.refresh()
  app.run(debug=True, host="0.0.0.0") #, port=80)
  pg.quit()


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--search-depth", type=int, default=3)
  parser.add_argument("--white-player", type=PlayerType, default=PlayerType.HUMAN)
  parser.add_argument("--black-player", type=PlayerType, default=PlayerType.ROBOT)
  parser.add_argument("--square-bonuses-file", default="resources/piece_square_bonuses.txt")
  parser.add_argument("--fen")
  parser.add_argument("--book-file")
  parser.add_argument("--profile", action="store_true")
  parser.add_argument("--verbose", action="store_true")
  args = parser.parse_args()
  Logging.verbose = args.verbose
  if args.profile:
    yappi.start()
  main(args.search_depth, args.white_player, args.black_player, args.square_bonuses_file, args.fen, args.book_file)
  if args.profile:
    yappi.get_func_stats().print_all(columns={
      0: ("name", 36),
      1: ("ncall", 8),
      2: ("tsub", 8),
      3: ("ttot", 8),
      4: ("tavg", 8)
    })
