from enums import PlayerColor


class Piece:
  def __init__(self, player_color, type, rank, file):
    self.player_color = player_color
    self.type = type
    self.rank = rank
    self.file = file
    self.n_times_moved = 0

  def __str__(self):
    return f"Piece(player_color={self.player_color}, type={self.type}, rank={self.rank}, file={self.file})"

  def __repr__(self):
    return str(self)

  def to_json(self):
    return {
      'player_color': self.player_color,
      'type': self.type,
      'rank': self.rank,
      'file': self.file,
    }

  def fen(self):
    abbr = self.type.value
    return abbr.upper() if self.player_color is PlayerColor.WHITE else abbr

  def update_type(self, new_type, player_pieces):
    player_pieces[self.type].remove(self)
    self.type = new_type
    player_pieces[new_type].add(self)