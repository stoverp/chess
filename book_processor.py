import re
from argparse import ArgumentParser

from enums import PlayerType, piece_types_by_san_format
from game_state import GameState


def san_to_index(rank_string, file_string):
  rank = int(rank_string) - 1 if rank_string else None
  file = ord(file_string) - ord('a') if file_string else None
  return rank, file


def parse_move(move_string, game_state):
  piece_type = piece_types_by_san_format.get(move_string[0], None)
  legal_moves = []
  if piece_type:
    for piece in game_state.active_player().find_all(piece_type):
      legal_moves.extend(game_state.generate_legal_moves(piece))
  else:
    legal_moves = game_state.generate_all_legal_moves()
  if match := re.match(r"(\w?)(\d?)x?(\w)(\d)\+?", move_string):
    # from_file, from_rank, to_file, to_rank = [int(v) if v.isnumeric() else None for v in match.groups()]
    from_rank, from_file = san_to_index(match.group(2), match.group(1))
    to_rank, to_file = san_to_index(match.group(4), match.group(3))
    print(f"{from_file}, {from_rank}, {to_file}, {to_rank}")
    for move in legal_moves:
      if (to_rank, to_file) == (move.rank, move.file):
        if not from_rank or from_rank == move.old_rank:
          if not from_file or from_file == move.old_file:
            return move
    raise Exception(f"can't find valid move for move string: {move_string}")
  else:
    raise Exception(f"invalid move string: {move_string}")


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
        print(f"found white move: {white_move}")
        white_move.apply()
        black_move = parse_move(black_move_string, game_state)
        black_move.apply()


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()
  main(args.file)
