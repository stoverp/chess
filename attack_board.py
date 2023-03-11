from core import empty_board_array
from board import Board
from enums import PieceType
from move_generator import ROOK_DIRECTIONS, BISHOP_DIRECTIONS


class AttackBoard:
  def __init__(self, player_state):
    self.player_state = player_state
    self.game_state = player_state.game_state
    self.full_board = empty_board_array(False)
    self.pawn_board = empty_board_array(False)

  def __getitem__(self, item):
    return self.full_board[item]

  def calculate_knight_attacks(self, knight):
    for far_rank in [True, False]:
      for rank_direction in [1, -1]:
        for file_direction in [1, -1]:
          rank = (2 if far_rank else 1) * rank_direction + knight.rank
          file = (1 if far_rank else 2) * file_direction + knight.file
          if self.empty_or_opponent_square(knight.player_color, rank, file):
            self.full_board[rank][file] = True

  def empty_or_opponent_square(self, player_color, rank, file):
    if Board.in_bounds(rank, file):
      piece_on_square = self.game_state.board[rank][file]
      return not piece_on_square or piece_on_square.player_color is player_color.opponent
    return False

  def calculate_king_attacks(self, king):
    for rank_direction, file_direction in ROOK_DIRECTIONS + BISHOP_DIRECTIONS:
      rank = rank_direction + king.rank
      file = file_direction + king.file
      if self.empty_or_opponent_square(king.player_color, rank, file):
        self.full_board[rank][file] = True

  def calculate_attacks(self, piece):
    if piece.type is PieceType.PAWN:
      self.calculate_pawn_attacks(piece)
    elif piece.type is PieceType.KNIGHT:
      self.calculate_knight_attacks(piece)
    elif piece.type is PieceType.BISHOP:
      self.calculate_slide_attacks(piece, BISHOP_DIRECTIONS)
    elif piece.type is PieceType.ROOK:
      self.calculate_slide_attacks(piece, ROOK_DIRECTIONS)
    elif piece.type is PieceType.QUEEN:
      self.calculate_slide_attacks(piece, ROOK_DIRECTIONS + BISHOP_DIRECTIONS)
    else:  # piece.type is PieceType.KING:
      self.calculate_king_attacks(piece)

  def calculate_slide_attacks(self, piece, directions):
    for rank_direction, file_direction in directions:
      collision = False
      distance = 1
      while not collision:
        rank = distance * rank_direction + piece.rank
        file = distance * file_direction + piece.file
        if not Board.in_bounds(rank, file):
          collision = True
        else:
          if self.empty_or_opponent_square(piece.player_color, rank, file):
            self.full_board[rank][file] = True
          if self.game_state.board[rank][file]:
            collision = True
        distance += 1

  def calculate_pawn_attacks(self, pawn):
    pawn_direction = pawn.player_color.pawn_direction
    rank = pawn.rank + pawn_direction
    for file in [pawn.file + 1, pawn.file - 1]:
      if self.empty_or_opponent_square(pawn.player_color, rank, file):
        self.full_board[rank][file] = True
        self.pawn_board[rank][file] = True

  def refresh(self):
    self.full_board = empty_board_array(False)
    self.pawn_board = empty_board_array(False)
    for piece in self.player_state.all_pieces():
      self.calculate_attacks(piece)

