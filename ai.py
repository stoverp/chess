import math
import time

from transpositions import TranspositionTable, EvalType


class AI:
  def __init__(self, search_depth, game_state):
    self.search_depth = search_depth
    self.game_state = game_state
    self.transposition_table = TranspositionTable()
    self.n_moves_searched = 0

  def evaluate_board(self, active_player_color):
    score = 0
    for player in self.game_state.players.values():
      perspective = 1 if player.player_color == active_player_color else -1
      for pieces in player.pieces.values():
        for piece in pieces:
          score += perspective * piece.type.score
          square_bonus = self.game_state.lookup_bonus(piece.type, player.player_color, piece.rank, piece.file)
          score += perspective * square_bonus
    return score

  def quiesce(self, active_player_color, alpha, beta):
    score = self.evaluate_board(active_player_color)
    if score >= beta:
      return None, beta
    alpha = max(alpha, score)
    moves = self.game_state.generate_all_legal_moves(filter_checks=True, captures_only=True)
    top_move = None
    for move in moves:
      self.n_moves_searched += 1
      move.apply()
      _, score = self.quiesce(active_player_color.opponent, -beta, -alpha)
      # negate score to reflect opponent's perspective
      score = -score
      move.unapply()
      if score >= beta:
        # beta limit tells us opponent can prevent this scenario
        return None, beta
      if score > alpha:
        top_move = move
        alpha = score
    return top_move, alpha

  def search_moves(self, active_player_color, depth, alpha, beta):
    if entry := self.transposition_table.lookup(self.game_state.board.zobrist_key, depth, alpha, beta):
      return entry.move, entry.score
    if depth == 0:
      return self.quiesce(active_player_color, alpha, beta)
    moves = self.game_state.generate_all_legal_moves(filter_checks=True)
    if not moves:
      if self.game_state.active_player().in_check():
        return None, -math.inf
      else:
        return None, 0
    top_move = None
    eval_type = EvalType.UPPER_BOUND
    for move in moves:
      self.n_moves_searched += 1
      move.apply()
      _, score = self.search_moves(active_player_color.opponent, depth - 1, -beta, -alpha)
      # negate score to reflect opponent's perspective
      score = -score
      move.unapply()
      if score >= beta:
        self.transposition_table.store(self.game_state.board.zobrist_key, depth, beta,
          EvalType.LOWER_BOUND, move)
        # beta limit tells us opponent can prevent this scenario
        return None, beta
      if score > alpha:
        eval_type = EvalType.EXACT
        top_move = move
        alpha = score
    self.transposition_table.store(self.game_state.board.zobrist_key, depth, alpha, eval_type,
      top_move)
    return top_move, alpha

  def best_move(self):
    self.n_moves_searched = 0
    print(f"\ncalculating {self.game_state.active_player_color} move ...")
    start_time = time.time()
    move, score = self.search_moves(self.game_state.active_player_color, self.search_depth, -math.inf, math.inf)
    print(
      f"evaluated score {score} by searching {self.n_moves_searched} moves in {time.time() - start_time} seconds:\n\t{move}")
    if move:
      return move
    else:
      move = self.game_state.active_player().legal_moves[0]
      print(f"{self.game_state.active_player_color} has no moves that avoid checkmate! just make first legal move: {move}")
      return move