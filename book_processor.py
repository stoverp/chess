import json
import os
import re
from argparse import ArgumentParser
from collections import defaultdict

import pygame as pg

from display import BoardDisplay
from engine import Engine
from enums import PlayerType, piece_types_by_san_format, PieceType, PlayerColor
from game_state import GameState


def san_to_index(rank_string, file_string):
  rank = int(rank_string) - 1 if rank_string else None
  file = ord(file_string) - ord('a') if file_string else None
  return rank, file


def parse_move(move_string, game_state):
  # todo: handle en passant and promotion
  if move_string.startswith('O-O'):
    # castling! king-side is 'O-O', queen-side is 'O-O-O'
    king = game_state.active_player().find(PieceType.KING)
    rook = game_state.active_player().find_rook(king_side=move_string == 'O-O')
    for move in game_state.generate_legal_moves(king):
      if move.castling_rook_move and move.castling_rook_move.piece == rook:
        return move
    raise Exception(f"can't find valid move for move string: {move_string}")
  elif match := re.match(rf"([{''.join(piece_types_by_san_format.keys())}]?)([a-h]?)(\d?)x?([a-h])(\d)\+?", move_string):
    piece_type = piece_types_by_san_format.get(match.group(1)) if match.group(1) else None
    from_rank, from_file = san_to_index(match.group(3), match.group(2))
    to_rank, to_file = san_to_index(match.group(5), match.group(4))
    legal_moves = []
    if piece_type:
      for piece in game_state.active_player().find_all(piece_type):
        legal_moves.extend(game_state.generate_legal_moves(piece))
    else:
      legal_moves = game_state.generate_all_legal_moves()
    candidates = []
    for move in legal_moves:
      if (to_rank, to_file) == (move.rank, move.file):
        if not from_rank or from_rank == move.old_rank:
          if not from_file or from_file == move.old_file:
            candidates.append(move)
    if len(candidates) == 0:
      raise Exception(f"can't find valid move for move string: {move_string}")
    elif len(candidates) > 1:
      print(f"move string {move_string} has more than one candidate: {candidates}")
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


def make_move(player_color, move_string, game_state, engine, board_display, openings):
  move = parse_move(move_string, game_state)
  print(f"found {player_color} move for string {move_string}:\n\t{move}")
  openings[game_state.board.zobrist_key].append(move)
  engine.make_move(move)
  # return wait_for_key(board_display)
  return True


def start_game():
  game_state = GameState(PlayerType.HUMAN, PlayerType.HUMAN)
  board_display = BoardDisplay(game_state)
  engine = Engine(game_state, board_display)
  return game_state, board_display, engine


def process_games(file):

  openings = defaultdict(list)
  n_games = 0
  with open(file, "r") as f:
    for line in f.readlines():
      text = line.strip()
      if not text or text.startswith("["):
        continue
      elif text.startswith("1."):
        n_games += 1
        game_state, board_display, engine = start_game()
        if n_games > 3:
          return openings
      move_tuples = re.findall(r"(\d+)\.([\w\-+]+) ([\w\-+]+)", text)
      for move_number, white_move_string, black_move_string in move_tuples:
        print(f"\nMOVE #{move_number}")
        if not make_move(PlayerColor.WHITE, white_move_string, game_state, engine, board_display, openings):
          pg.quit()
          return openings
        if not make_move(PlayerColor.BLACK, black_move_string, game_state, engine, board_display, openings):
          pg.quit()
          return openings
  return openings


def to_json(openings):
  result = dict()
  for key, moves in openings.items():
    result[key] = [move.to_json() for move in moves]
  return result


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()
  openings = process_games(args.file)
  json_openings = to_json(openings)
  output_file = os.path.splitext(args.file)[0] + ".json"
  with open(output_file, "w") as f:
    json.dump(json_openings, f, default=lambda x: x.value, indent=2)
