class Logging:
  verbose = False


def debug(message):
  if Logging.verbose:
    print(message)
