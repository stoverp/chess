import os
from collections import defaultdict

import pygame as pg
from pygame.display import set_mode
from pygame.image import load
from pygame.rect import Rect

from core import rank_to_san, file_to_san
from enums import PieceType, PlayerColor
from move import Move

BACKGROUND_COLORS = [(235, 236, 208), (119, 149, 86)]
SELECTED_SQUARE_COLOR = (252, 186, 3)
LEGAL_MOVE_COLORS = [(235, 127, 132), (115, 61, 63)]
LAST_MOVE_COLORS = [(127, 235, 226), (61, 113, 115)]
ATTACKING_COLORS = [(235, 127, 201), (115, 61, 98)]

# todo: limit window resizing to preserve aspect ratio
DISPLAY_WIDTH = 1120
BOARD_PIXEL_WIDTH = 560
SQUARE_WIDTH = BOARD_PIXEL_WIDTH // 8
IMAGE_WIDTH = 60
IMAGE_CORNER_OFFSET = (SQUARE_WIDTH - IMAGE_WIDTH) // 2

os.environ['SDL_VIDEO_WINDOW_POS'] = "100, 100"


class PieceSprites:
  sprites = defaultdict(dict)
  for piece_type in PieceType:
    for color in PlayerColor:
      sprites[piece_type][color] = load(f"images/Chess_{piece_type.value}{color.image_abbr}t60.png")

  @classmethod
  def surface(cls, piece):
    return cls.sprites[piece.type][piece.player_color]


class BoardDisplay:
  def __init__(self, game_state):
    pg.init()
    self.game_state = game_state
    self.displayed_screen = set_mode((DISPLAY_WIDTH, DISPLAY_WIDTH), pg.RESIZABLE)
    self.screen = pg.Surface((BOARD_PIXEL_WIDTH, BOARD_PIXEL_WIDTH))
    self.display_player_attacking = None
    self.display_pawn_attacks = None
    self.font = pg.font.SysFont(None, 18)

  def refresh(self):
    self.draw_squares()
    self.draw_coordinates()
    self.draw_pieces()
    self.displayed_screen.blit(pg.transform.scale(self.screen, pg.display.get_window_size()), (0, 0))
    pg.display.flip()

  def draw_squares(self):
    last_move = self.game_state.move_history[-1] if self.game_state.move_history else None
    for rank in range(8):
      for file in range(8):
        square_type = (rank + file + 1) % 2
        if self.game_state.selected_piece:
          if (rank, file) == (self.game_state.selected_piece.piece.rank, self.game_state.selected_piece.piece.file):
            color = SELECTED_SQUARE_COLOR
          elif Move(self.game_state.selected_piece.piece, rank, file, self.game_state) in self.game_state.selected_piece.legal_moves:
            color = LEGAL_MOVE_COLORS[square_type]
          else:
            color = BACKGROUND_COLORS[square_type]
        elif last_move and (rank, file) in [(last_move.old_rank, last_move.old_file), (last_move.rank, last_move.file)]:
          color = LAST_MOVE_COLORS[square_type]
        elif self.display_player_attacking and \
            self.game_state.players[self.display_player_attacking].attack_board[rank][file]:
          color = ATTACKING_COLORS[square_type]
        elif self.display_pawn_attacks and \
            self.game_state.players[self.display_pawn_attacks].attack_board.pawn_board[rank][file]:
          color = ATTACKING_COLORS[square_type]
        else:
          color = BACKGROUND_COLORS[square_type]
        pg.draw.rect(self.screen, color, Rect(get_screen_pos(rank, file), (SQUARE_WIDTH, SQUARE_WIDTH)))

  def draw_pieces(self):
    for rank in range(8):
      for file in range(8):
        if self.game_state.selected_piece and (rank, file) == (self.game_state.selected_piece.piece.rank, self.game_state.selected_piece.piece.file):
          self.screen.blit(PieceSprites.surface(self.game_state.selected_piece.piece), (
            self.game_state.selected_piece.screen_pos[0] - (IMAGE_WIDTH // 2), self.game_state.selected_piece.screen_pos[1] - (IMAGE_WIDTH // 2)
          ))
        elif piece := self.game_state.board[rank][file]:
          self.screen.blit(PieceSprites.surface(piece), (
            piece.file * SQUARE_WIDTH + IMAGE_CORNER_OFFSET,
            (7 - piece.rank) * SQUARE_WIDTH + IMAGE_CORNER_OFFSET
          ))

  def toggle_attack_display(self, player_color):
    if self.display_player_attacking is player_color:
      self.display_player_attacking = None
    else:
      self.display_pawn_attacks = None
      self.display_player_attacking = player_color
      print(f"\nDISPLAYING {player_color.name.upper()} ATTACK MAP.")

  def toggle_pawn_attack_display(self, player_color):
    if self.display_pawn_attacks is player_color:
      self.display_pawn_attacks = None
    else:
      self.display_player_attacking = None
      self.display_pawn_attacks = player_color
      print(f"\nDISPLAYING {player_color.name.upper()} PAWN ATTACK MAP.")

  def draw_coordinates(self):
    for rank in range(8):
      x, y = get_screen_pos(rank, 0)
      self.screen.blit(self.font.render(rank_to_san(rank), True, BACKGROUND_COLORS[rank % 2]),
        (x + 5, y + 5))
    for file in range(8):
      x, y = get_screen_pos(0, file)
      self.screen.blit(self.font.render(file_to_san(file), True, BACKGROUND_COLORS[file % 2]),
        (x + SQUARE_WIDTH - 12, y + SQUARE_WIDTH - 15))

def get_square(display_pos):
  screen_pos = display_coords_to_screen(display_pos)
  return int((BOARD_PIXEL_WIDTH - screen_pos[1]) / SQUARE_WIDTH), int(screen_pos[0] / SQUARE_WIDTH)


def get_screen_pos(rank, file):
  return file * SQUARE_WIDTH, (7 - rank) * SQUARE_WIDTH


def display_coords_to_screen(display_pos):
  window_width, window_height = pg.display.get_window_size()
  width_scale = window_width / BOARD_PIXEL_WIDTH
  height_scale = window_height / BOARD_PIXEL_WIDTH
  return display_pos[0] / width_scale, display_pos[1] / height_scale