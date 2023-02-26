import re
from argparse import ArgumentParser

import pygame as pg

from display import BoardDisplay
from engine import Engine
from enums import PlayerType, piece_types_by_san_format, PieceType
from game_state import GameState


def san_to_index(rank_string, file_string):
  rank = int(rank_string) - 1 if rank_string else None
  file = ord(file_string) - ord('a') if file_string else None
  return rank, file


def parse_move(move_string, game_state):
  if match := re.match(rf"([{''.join(piece_types_by_san_format.keys())}]?)(\w?)(\d?)x?(\w)(\d)\+?", move_string):
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
        waiting = False
      board_display.refresh()


def main(file):
  game_state = GameState(PlayerType.HUMAN, PlayerType.HUMAN)
  board_display = BoardDisplay(game_state)
  engine = Engine(game_state, board_display)
  n_games = 0
  with open(file, "r") as f:
    for line in f.readlines():
      text = line.strip()
      if not text or text.startswith("["):
        continue
      elif text.startswith("1."):
        # print()
        n_games += 1
        if n_games > 1:
          break
      move_tuples = re.findall(r"(\d+)\.([\w\-+]+) ([\w\-+]+)", text)
      # print(text)
      # print(move_tuples)
      for move_number, white_move_string, black_move_string in move_tuples:
        print(f"MOVE #{move_number}")
        white_move = parse_move(white_move_string, game_state)
        print(f"found white move for string {white_move_string}: {white_move}")
        engine.make_move(white_move)
        wait_for_key(board_display)
        black_move = parse_move(black_move_string, game_state)
        print(f"found black move for string {black_move_string}: {black_move}")
        engine.make_move(black_move)
        wait_for_key(board_display)


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()
  main(args.file)
