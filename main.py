from argparse import ArgumentParser

import pygame as pg
import pygame.display

from display import BoardDisplay
from engine import Engine
from enums import PlayerType
from game_state import GameState
from logging import Logging


def main(search_depth, white_player_type, black_player_type, bonuses_file, fen, book_file):
  game_state = GameState(white_player_type, black_player_type, search_depth, bonuses_file, fen, book_file)
  board_display = BoardDisplay(game_state)
  engine = Engine(game_state, board_display)
  running = True
  engine.print_stats()
  while running:
    if not game_state.active_player().legal_moves:
      engine.endgame()
      running = False
    if game_state.active_player().player_type is PlayerType.ROBOT:
      move = game_state.best_move()
      engine.make_move(move)
      engine.print_stats()
      pygame.display.update()
    else:
      for event in pg.event.get():
        if not engine.handle_event(event):
          running = False
    board_display.refresh()
  pg.quit()


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--search-depth", type=int, default=3)
  parser.add_argument("--white-player", type=PlayerType, default=PlayerType.HUMAN)
  parser.add_argument("--black-player", type=PlayerType, default=PlayerType.ROBOT)
  parser.add_argument("--square-bonuses-file", default="resources/piece_square_bonuses.txt")
  parser.add_argument("--fen")
  # todo: book size causing OOM; limit book size
  parser.add_argument("--book-file")
  parser.add_argument("--verbose", action="store_true")
  args = parser.parse_args()
  Logging.verbose = args.verbose
  main(args.search_depth, args.white_player, args.black_player, args.square_bonuses_file, args.fen, args.book_file)
