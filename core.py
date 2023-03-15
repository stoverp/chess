def empty_board_array(default_value=None):
  return [[default_value for _ in range(8)] for _ in range(8)]


def san_to_index(rank_string, file_string):
  rank = int(rank_string) - 1 if rank_string else None
  file = ord(file_string) - ord('a') if file_string else None
  return rank, file


def file_to_san(file):
  return chr(ord('a') + file) if file is not None else ''


def rank_to_san(rank):
  return str(rank + 1) if rank is not None else ''


def index_to_san(rank, file):
  return f"{file_to_san(file)}{rank_to_san(rank)}"
