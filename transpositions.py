from enum import Enum


class EvalType(Enum):
  EXACT = 1
  LOWER_BOUND = 2
  UPPER_BOUND = 3


class TranspositionEntry:
  def __init__(self, zobrist_key, depth, score, eval_type, move):
    self.zobrist_key = zobrist_key
    self.depth = depth
    self.score = score
    self.eval_type = eval_type
    self.move = move


class TranspositionTable:
  def __init__(self):
    self.entries = dict()
    self.n_transpositions_evaluated = 0

  def store(self, zobrist_key, depth, score, eval_type, move):
    self.entries[zobrist_key] = TranspositionEntry(zobrist_key, depth, score, eval_type, move)

  def lookup(self, zobrist_key, depth, alpha, beta):
    if zobrist_key not in self.entries:
      return None
    entry = self.entries[zobrist_key]
    if entry.depth < depth:
      return None
    if entry.eval_type is EvalType.EXACT:
      self.n_transpositions_evaluated += 1
      # print(f"found exact score in tranposition table: {entry.score}")
      return entry
    elif entry.eval_type is EvalType.UPPER_BOUND and entry.score <= alpha:
      self.n_transpositions_evaluated += 1
      # print(f"found upper bound score in tranposition table: {entry.score}")
      return entry
    elif entry.eval_type is EvalType.LOWER_BOUND and entry.score >= beta:
      self.n_transpositions_evaluated += 1
      # print(f"found lower bound score in tranposition table: {entry.score}")
      return entry
    else:
      return None

  def from_key(self, zobrist_key):
    return self.entries.get(zobrist_key, None)