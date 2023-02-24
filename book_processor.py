import re
from argparse import ArgumentParser

from enums import PlayerType, PieceType, piece_types_by_san_format
from game_state import GameState


def parse_move(move_string, game_state):
  piece_type = piece_types_by_san_format.get(move_string[0], None)
  legal_moves = []
  if piece_type:
    for piece in game_state.active_player().find_all(piece_type):
      legal_moves.extend(game_state.generate_legal_moves(piece))
  else:
    legal_moves = game_state.generate_all_legal_moves()
  if match := re.match(r"(\w?)(\d?)x?(\w)(\d)\+?", move_string):
    from_file, from_rank, to_file, to_rank = match.groups()
    print(f"{from_file}, {from_rank}, {to_file}, {to_rank}")
  else:
    raise(Exception(f"invalid move string: {move_string}"))


def main(file):
  game_state = GameState(PlayerType.HUMAN, PlayerType.HUMAN)
  n_games = 0
  with open(file, "r") as f:
    for line in f.readlines():
      text = line.strip()
      if not text or text.startswith("["):
        continue
      elif text.startswith("1."):
        print()
        n_games += 1
        if n_games > 1:
          break
      move_tuples = re.findall(r"(\d+)\.([\w\-+]+) ([\w\-+]+)", text)
      print(text)
      print(move_tuples)
      for move_number, white_move_string, black_move_string in move_tuples:
        print(move_number, white_move_string, black_move_string)
        white_move = parse_move(white_move_string, game_state)
        black_move = parse_move(black_move_string, game_state)


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()
  main(args.file)
