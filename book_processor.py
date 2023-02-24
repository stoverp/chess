import re
from argparse import ArgumentParser


def parse_move(move_string):
  pass


def main(file):
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
      for move_tuple in move_tuples:
        move_number, white_move, black_move = move_tuple
        print(move_number, white_move, black_move)
        move = parse_move(white_move)


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()
  main(args.file)
