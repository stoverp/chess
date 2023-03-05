import copy
import json
import os
import re
import time
from argparse import ArgumentParser
from collections import defaultdict

import pygame as pg

from core import san_to_index
from display import BoardDisplay
from engine import Engine
from enums import PlayerType, piece_types_by_san_format, PieceType, PlayerColor
from game_state import GameState
from logging import Logging


def find_legal_castles(king_side, game_state):
  king = game_state.active_player().find(PieceType.KING)
  rook = game_state.active_player().find_castling_rook(king_side=king_side)
  for move in game_state.generate_legal_moves(king):
    if move.castling_rook_move and move.castling_rook_move.piece == rook:
      return move
  return None


def parse_move(move_string, game_state):
  Logging.debug(f"evaluating {move_string} ...")
  piece_type_abbrs = ''.join(piece_types_by_san_format.keys())
  if move_string.startswith('O-O'):
    # castling! king-side is 'O-O', queen-side is 'O-O-O'
    move = find_legal_castles(move_string == 'O-O', game_state)
    if not move:
      # find_legal_castles(move_string == 'O-O', game_state)
      raise Exception(f"can't find valid move for move string: {move_string}")
    else:
      return move
  elif match := re.match(rf"([{piece_type_abbrs}]?)([a-h]?)(\d?)x?([a-h])(\d)\+?(=[{piece_type_abbrs}])?", move_string):
    piece_type = piece_types_by_san_format.get(match.group(1), None)
    from_rank, from_file = san_to_index(match.group(3), match.group(2))
    to_rank, to_file = san_to_index(match.group(5), match.group(4))
    promote_type = piece_types_by_san_format[match.group(6)[-1]] if match.group(6) else None
    legal_moves = []
    if piece_type:
      for piece in game_state.active_player().find_all(piece_type):
        legal_moves.extend(game_state.generate_legal_moves(piece))
    else:
      legal_moves = game_state.generate_all_legal_moves(game_state.active_player_color)
    candidates = []
    for move in legal_moves:
      if (to_rank, to_file) == (move.rank, move.file):
        if (from_rank is None) or (from_rank == move.old_rank):
          if (from_file is None) or (from_file == move.old_file):
            if promote_type is None or promote_type == move.promote_type:
              candidates.append(move)
    if len(candidates) == 0:
      game_state.generate_all_legal_moves(game_state.active_player_color)
      raise Exception(f"can't find valid move for move string: {move_string}")
    elif len(candidates) > 1:
      Logging.debug(f"move string {move_string} has more than one candidate: {candidates}")
      for candidate in candidates:
        if candidate.piece.type is PieceType.PAWN:
          return candidate
    return candidates[0]
  else:
    raise Exception(f"invalid move string: {move_string}")


def wait_for_key(board_display):
  waiting = True
  while waiting:
    for event in pg.event.get():
      if event.type == pg.KEYDOWN:
        waiting = False
      if event.type == pg.QUIT:
        return False
      board_display.refresh()
  return True


def make_move(player_color, move_string, game_state, engine, openings, board_display, pause=False):
  if pause:
    if not wait_for_key(board_display):
      return False
  move = parse_move(move_string, game_state)
  Logging.debug(f"found {player_color} move for string {move_string}:\n\t{move}")
  openings[game_state.board.zobrist_key].append((move_string, copy.deepcopy(move)))
  engine.make_move(move)
  # engine.print_stats()
  return True


def start_game(pause_at_move, interactive):
  game_state = GameState(PlayerType.HUMAN, PlayerType.HUMAN)
  board_display = BoardDisplay(game_state) if (pause_at_move is not None or interactive) else None
  engine = Engine(game_state, board_display)
  return game_state, board_display, engine


def process_games(file, game, limit, pause_at_move, interactive):
  openings = defaultdict(list)
  skipped_games = 0
  n_games = 0
  with open(file, "r") as f:
    for line in f.readlines():
      try:
        text = line.strip()
        if not text or text.startswith("["):
          continue
        elif text.startswith("1."):
          n_games += 1
          if n_games > limit:
            break
          print(f"\nCURRENT TIME: {time.time() - start_time} SECONDS")
          print("=======")
          print(f"GAME #{n_games}")
          print("=======\n")
          game_state, board_display, engine = start_game(pause_at_move, interactive)
          # engine.print_stats()
        if game is None or n_games >= game:
          print(text)
          move_tuples = re.findall(r"(\d+)\.([\w\-+=]+) ([\w\-+=]+)", text)
          for move_number_string, white_move_string, black_move_string in move_tuples:
            move_number = int(move_number_string)
            Logging.debug(f"\nMOVE #{move_number}")
            pause = interactive or (pause_at_move is not None and move_number >= pause_at_move)
            if not make_move(PlayerColor.WHITE, white_move_string, game_state, engine, openings, board_display, pause):
              pg.quit()
              return openings
            if not make_move(PlayerColor.BLACK, black_move_string, game_state, engine, openings, board_display, pause):
              pg.quit()
              return openings
      except Exception as e:
        print(e)
        skipped_games += 1
  return skipped_games, openings


def to_json(openings):
  result = defaultdict(list)
  for key, moves in openings.items():
    for move_string, move in moves:
      json_move = move.to_json()
      json_move["move_string"] = move_string
      result[key].append(json_move)
  return result


# todo: fix additional cases in Kasparov book
if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  parser.add_argument("--game", type=int)
  parser.add_argument("--limit", type=int)
  parser.add_argument("--pause-at-move", type=int)
  parser.add_argument("--interactive", action="store_true")
  parser.add_argument("--verbose", action="store_true")
  parser.add_argument("--repeat-forever", action="store_true")
  args = parser.parse_args()
  Logging.verbose = args.verbose
  start_time = time.time()
  if args.repeat_forever:
    while True:
      _, openings = process_games(args.file, args.game, args.limit, args.pause_at_move, args.interactive)
  else:
    skipped_games, openings = process_games(args.file, args.game, args.limit, args.pause_at_move, args.interactive)
  print(f"\nFINISHED PROCESSING GAMES. SKIPPED {skipped_games} GAMES.")
  json_openings = to_json(openings)
  output_file = os.path.splitext(args.file)[0] + ".json"
  with open(output_file, "w") as f:
    json.dump(json_openings, f, default=lambda x: x.value, indent=2)
  print(f"\n--- COMPLETED IN {time.time() - start_time} SECONDS ---")
