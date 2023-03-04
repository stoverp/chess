class Logging:
  verbose = False

  @classmethod
  def debug(cls, message):
    if Logging.verbose:
      print(message)
