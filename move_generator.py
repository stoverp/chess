from sortedcontainers import SortedList

from enums import PieceType
from move import Move, MoveType


ROOK_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISHOP_DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

class MoveGenerator:
  def __init__(self, game_state):
    self.game_state = game_state

  def is_promoting_pawn(self, piece, new_rank):
    return piece.type is PieceType.PAWN and new_rank == piece.player_color.opponent.back_rank

  def include_promotion_moves(self, move):
    moves = set()
    if self.is_promoting_pawn(move.piece, move.rank):
      for promote_type in [PieceType.QUEEN, PieceType.KNIGHT]:
        moves.add(Move(move.piece, move.rank, move.file, self.game_state, promote_type=promote_type))
    else:
      moves.add(move)
    return moves

  def generate_pawn_moves(self, piece, captures_only=False):
    moves = set()
    pawn_direction = piece.player_color.pawn_direction
    # capture moves
    for rank_offset, file_offset in [(pawn_direction, 1), (pawn_direction, -1)]:
      move = Move(piece, piece.rank + rank_offset, piece.file + file_offset, self.game_state)
      if move.move_type is MoveType.CAPTURE:
        moves.update(self.include_promotion_moves(move))
    if captures_only:
      return moves
    # one-square standard move
    rank_candidates = [piece.rank + (1 * pawn_direction)]
    # two-square opening move
    if piece.rank == piece.player_color.back_rank + pawn_direction:
      # can't move through pieces
      if not self.game_state.board[piece.rank + (1 * pawn_direction)][piece.file]:
        rank_candidates.append(piece.rank + (2 * pawn_direction))
    for new_rank in rank_candidates:
      move = Move(piece, new_rank, piece.file, self.game_state)
      if move.move_type is MoveType.OPEN_SQUARE:
        moves.update(self.include_promotion_moves(move))
    # todo: en passant
    return moves

  def generate_slide_moves(self, piece, directions, captures_only=False):
    moves = set()
    for rank_direction, file_direction in directions:
      collision = False
      distance = 1
      while not collision:
        move = Move(piece, distance * rank_direction + piece.rank, distance * file_direction + piece.file, self.game_state)
        if move.move_type in (MoveType.SELF_OCCUPIED, MoveType.OUT_OF_BOUNDS):
          collision = True
        else:
          self.add_move_if_valid(move, moves, captures_only)
          if move.move_type is MoveType.CAPTURE:
            collision = True
        distance += 1
    return moves

  def add_move_if_valid(self, move, moves, captures_only):
    if move.move_type is MoveType.CAPTURE:
      moves.add(move)
    elif not captures_only and move.move_type is MoveType.OPEN_SQUARE:
      moves.add(move)

  def generate_knight_moves(self, piece, captures_only=False):
    moves = set()
    for far_rank in [True, False]:
      for rank_direction in [1, -1]:
        for file_direction in [1, -1]:
          move = Move(
            piece,
            (2 if far_rank else 1) * rank_direction + piece.rank,
            (1 if far_rank else 2) * file_direction + piece.file,
            self.game_state)
          self.add_move_if_valid(move, moves, captures_only)
    return moves

  def castling_moves(self, king, filter_checks):
    moves = set()
    if king.n_times_moved == 0:
      player = self.game_state.players[king.player_color]
      for rook in player.pieces[PieceType.ROOK]:
        if rook.n_times_moved == 0:
          can_castle = True
          new_file = king.file + 2 if rook.file - king.file > 0 else king.file - 2
          small_file, big_file = sorted([king.file, rook.file])
          for file_between in range(small_file + 1, big_file):
            if self.game_state.board[king.rank][file_between]:
              can_castle = False
              break
          if can_castle:
            if filter_checks:
              if player.in_check():
                can_castle = False
              else:
                # make a fake king move to the space between
                fake_move = Move(
                  king,
                  king.rank,
                  king.file + 1 if rook.file - king.file > 0 else king.file - 1,
                  self.game_state)
                fake_move.apply()
                if player.in_check():
                  # player would be castling through check
                  can_castle = False
                fake_move.unapply()
            if can_castle:
              moves.add(Move(king, king.rank, new_file, self.game_state))
    return moves

  def generate_king_moves(self, king, filter_checks=True, captures_only=False):
    moves = set()
    for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
      move = Move(king, rank_direction + king.rank, file_direction + king.file, self.game_state)
      self.add_move_if_valid(move, moves, captures_only)
    moves.update(self.castling_moves(king, filter_checks))
    return moves

  def generate_legal_moves(self, piece, filter_checks=True, captures_only=False):
    if piece.type is PieceType.PAWN:
      moves = self.generate_pawn_moves(piece, captures_only)
    elif piece.type is PieceType.KNIGHT:
      moves = self.generate_knight_moves(piece, captures_only)
    elif piece.type is PieceType.BISHOP:
      moves = self.generate_slide_moves(piece, BISHOP_DIRECTIONS, captures_only)
    elif piece.type is PieceType.ROOK:
      moves = self.generate_slide_moves(piece, ROOK_DIRECTIONS, captures_only)
    elif piece.type is PieceType.QUEEN:
      moves = self.generate_slide_moves(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS, captures_only)
    else:  # piece.type is PieceType.KING:
      moves = self.generate_king_moves(piece, filter_checks, captures_only)
    if filter_checks:
      player = self.game_state.players[piece.player_color]
      legal_moves = []
      for move in moves:
        move.apply()
        if filter_checks and player.in_check():
          # print(f"{move} not legal, puts {player.player_color} in check!")
          pass
        else:
          legal_moves.append(move)
        move.unapply()
      return legal_moves
    else:
      return moves

  def generate_and_mark_all_legal_moves(self, filter_checks=True, captures_only=False):
    # todo: try going back to this approach; it's cleaner and attack maps currently aren't handling stuff like pins
    # player.reset_attack_maps()
    player = self.game_state.active_player()
    # keep move list in sorted order by score guess
    all_legal_moves = SortedList(key=lambda t: t[0])
    for pieces in player.pieces.values():
      for piece in pieces:
        for move in self.generate_legal_moves(piece, filter_checks, captures_only):
          # if piece.type is not PieceType.PAWN or move.move_type is MoveType.CAPTURE:
          #   player.attack_board[move.rank][move.file] = True
          all_legal_moves.add((move.score_guess, move))
    # return high scores first
    return [move for score_guess, move in reversed(all_legal_moves)]