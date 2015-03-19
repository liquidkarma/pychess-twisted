import time
import traceback

WHITE  = 0
BLACK  = 1
COLORS = ['white', 'black']

STATE_NONE  = 0
STATE_CHECK = 1
STATE_MATE  = 2
STATE_STALE = 3
STATE_TIME  = 4

# any common gui routines
class ChessGUI:
   def __init__(self):
      pass

def movelabels(piece, capture, check, oldpos, newpos):
   # simple format for clients
   simple = chr(ord('A') + oldpos[0]) + \
            chr(ord('8') - oldpos[1]) + \
            chr(ord('A') + newpos[0]) + \
            chr(ord('8') - newpos[1])

   # SAN
   # TODO:
   # pawn promotion: =<NEW PIECE>
   # two moves per line (white followed by black)
   if piece.abbreviation == 'K' and abs(oldpos[0] - newpos[0]) == 2:
      if oldpos[0] < newpos[0]:
         label = 'O-O'
      else:
         label = 'O-O-O'
   else:
      frompos = chr(ord('a') + oldpos[0]) + chr(ord('8') - oldpos[1])
      topos   = chr(ord('a') + newpos[0]) + chr(ord('8') - newpos[1])
      label   = piece.abbreviation + frompos + capture + topos + check

   return simple, label

def decodemove(move):
   if len(move) != 4:
      raise TypeError, 'Invalid move'
   sx = ord(move[0]) - ord('A')
   sy = ord('8') - ord(move[1])
   dx = ord(move[2]) - ord('A')
   dy = ord('8') - ord(move[3])
   return sx, sy, dx, dy

class Piece:
   def __init__(self, board, color, coords, piece, abbreviation):
      self.board        = board
      self.color        = color
      self.coords       = coords
      self.abbreviation = abbreviation
      self.sprite       = board.ui.make_sprite(self, piece + '_' + COLORS[color], coords)

   def canMove(self):
      return self.board.running and \
             (self.board.sitColor is None or self.board.sitColor == self.board.color) and \
             self.color == self.board.color

   def remove(self):
      self.sprite.remove()

   def update(self, x, y):
      pass

   def checkMove(self, x, y):
      return (x != self.coords[0] or y != self.coords[1]) and self.isValidMove(x, y) and not self.inCheck(x, y)

   def inCheck(self, x, y):
      oldpos = self.board.pos(self.coords[0], self.coords[1])
      newpos = self.board.pos(x, y)

      oldcoords = self.coords
      oldpiece  = self.board.board[newpos]

      self.board.board[oldpos] = None
      self.board.board[newpos] = self
      self.coords = [x, y]

      in_check = self.board.inCheck(self.color)

      self.board.board[oldpos] = self
      self.board.board[newpos] = oldpiece
      self.coords = oldcoords

      return in_check

   def isValidMove(self, x, y):
      raise NotImplementedError

   def getPossibleMoves(self):
      raise NotImplementedError

   def hasValidMove(self):
      for move in self.getPossibleMoves():
         if self.checkMove(*move):
            return True
      return False

   def addMove(self, x, y, moves):
      if x >= 0 and x < self.board.width and y >= 0 and y < self.board.height:
         pos = self.board[(x, y)]
         if pos is None or pos.color != self.color:
            moves.append((x, y))

   def addMoves(self, xDelta, yDelta, moves):
      x = self.coords[0] + xDelta
      y = self.coords[1] + yDelta
      while x >= 0 and x < self.board.width and y >= 0 and y < self.board.height:
         pos = self.board[(x, y)]
         if pos is None:
            moves.append((x, y))
         else:
            if pos.color != self.color:
               moves.append((x, y))
            break
         x += xDelta
         y += yDelta

   def makeMove(self, newpos, local=False):
      self.board.makeMove(self, self.coords, newpos, local=local)
      self.coords = newpos

class Pawn(Piece):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'pawn', '')

      self.firstMove = True
      self.enPassant = False

   def update(self, x, y):
      deltax = abs(x - self.coords[0])
      deltay = abs(y - self.coords[1])

      if deltax == 1 and self.board[(x, y)] is None and self.board[(x, self.coords[1])] is not None:
         self.board.remove(x, self.coords[1])

      if self.firstMove and deltay == 2:
         self.enPassant = True
      else:
         self.enPassant = False

      self.firstMove = False

      if y == 0 or y == 7:
         self.board.promote(x, y)

   def isValidMove(self, x, y):
      deltax = abs(x - self.coords[0])
      deltay = y - self.coords[1]

      if (self.color == BLACK and deltay > 0) or (self.color == WHITE and deltay < 0):
         ady = abs(deltay)
         pos = self.board[(x, y)]
         if deltax == 0 and pos is None:
            if ady == 2 and self.firstMove and self.board[(x, self.coords[1] + deltay / 2)] is None:
               return True
            elif ady == 1:
               return True
         elif deltax == 1 and ady == 1:
            if pos is not None and pos.color != self.color:
               return True
            elif pos is None:
               # en passant
               pos = self.board[(x, self.coords[1])]
               if pos is not None and pos.abbreviation == '' and pos.color != self.color and pos.enPassant:
                  return True

      return False

   def __checkMove(self, x, y, moves, is_clear, ex=None, ey=None):
      if x >= 0 and x < self.board.width and y >= 0 and y < self.board.height:
         pos = self.board[(x, y)]
         if (is_clear and pos is None) or (not is_clear and pos is not None):
            invalid = False
            if ex is not None and ey is not None:
               pos = self.board[(ex, ey)]
               if pos is None or pos.abbreviation != '' or pos.color == self.color or not pos.enPassant:
                  invalid = True
            if not invalid:
               moves.append((x, y))

   def getPossibleMoves(self):
      moves = []
      if self.color == BLACK:
         ydelta = 1
      else:
         ydelta = -1

      self.__checkMove(self.coords[0], self.coords[1] + ydelta, moves, True)
      if self.firstMove and len(moves) == 1:
         self.__checkMove(self.coords[0], self.coords[1] + ydelta + ydelta, moves, True)
      # check en passant
      self.__checkMove(self.coords[0] - 1, self.coords[1] + ydelta, moves, True, self.coords[0] - 1, self.coords[1])
      self.__checkMove(self.coords[0] + 1, self.coords[1] + ydelta, moves, True, self.coords[0] + 1, self.coords[1])
      # regular kill moves
      self.__checkMove(self.coords[0] - 1, self.coords[1] + ydelta, moves, False)
      self.__checkMove(self.coords[0] + 1, self.coords[1] + ydelta, moves, False)

      return moves

class Rook(Piece):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'rook', 'R')

      self.firstMove = True

   def update(self, x, y):
      self.firstMove = False

   def isValidMove(self, x, y):
      if x == self.coords[0] or y == self.coords[1]:
         if x != self.coords[0]:
            if x > self.coords[0]:
               step = 1
            else:
               step = -1
            for dx in xrange(self.coords[0] + step, x, step):
               if self.board[(dx, self.coords[1])] is not None:
                  return False
         else:
            if y > self.coords[1]:
               step = 1
            else:
               step = -1
            for dy in xrange(self.coords[1] + step, y, step):
               if self.board[(self.coords[0], dy)] is not None:
                  return False

         pos = self.board[(x, y)]
         if pos is None or pos.color != self.color:
            return True
      return False

   def getPossibleMoves(self):
      moves = []
      self.addMoves( 1,  0, moves);
      self.addMoves(-1,  0, moves);
      self.addMoves( 0,  1, moves);
      self.addMoves( 0, -1, moves);
      return moves;

class Knight(Piece):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'knight', 'N')

   def isValidMove(self, x, y):
      deltax = abs(x - self.coords[0])
      deltay = abs(y - self.coords[1])
      if (deltax == 2 and deltay == 1) or (deltax == 1 and deltay == 2):
         pos = self.board[(x, y)]
         if pos is None or pos.color != self.color:
            return True
      return False

   def getPossibleMoves(self):
      moves = []
      x = self.coords[0]
      y = self.coords[1]
      self.addMove(x - 2, y - 1, moves);
      self.addMove(x - 2, y + 1, moves);
      self.addMove(x + 2, y - 1, moves);
      self.addMove(x + 2, y + 1, moves);
      self.addMove(x - 1, y + 2, moves);
      self.addMove(x - 1, y - 2, moves);
      self.addMove(x + 1, y + 2, moves);
      self.addMove(x + 1, y - 2, moves);
      return moves

class Bishop(Piece):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'bishop', 'B')

   def isValidMove(self, x, y):
      deltax = x - self.coords[0]
      deltay = y - self.coords[1]
      if abs(deltax) == abs(deltay):
         if deltax > 0:
            xstep = 1
         else:
            xstep = -1
         if deltay > 0:
            ystep = 1
         else:
            ystep = -1
         dx = self.coords[0] + xstep
         dy = self.coords[1] + ystep
         while dx != x and dy != y:
            pos = self.board[(dx, dy)]
            if pos is not None:
               return False
            dx += xstep
            dy += ystep
         pos = self.board[(x, y)]
         if pos is None or pos.color != self.color:
            return True

      return False

   def getPossibleMoves(self):
      moves = []
      self.addMoves( 1,  1, moves);
      self.addMoves(-1,  1, moves);
      self.addMoves(-1, -1, moves);
      self.addMoves( 1, -1, moves);
      return moves

class Queen(Bishop, Rook):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'queen', 'Q')

   def isValidMove(self, x, y):
      return Bishop.isValidMove(self, x, y) or Rook.isValidMove(self, x, y)

   def getPossibleMoves(self):
      return Bishop.getPossibleMoves(self) + Rook.getPossibleMoves(self)

class King(Piece):
   def __init__(self, board, color, coords):
      Piece.__init__(self, board, color, coords, 'king', 'K')

      self.hasBeenInCheck = False
      self.firstMove = True

   def update(self, x, y):
      deltax = x - self.coords[0]
      if abs(deltax) == 2 and self.firstMove:
         if deltax < 0:
            endx = 0
         else:
            endx = self.board.width - 1
         pos = self.board[(endx, y)]
         if pos is not None and pos.abbreviation == 'R':
            if deltax < 0:
               pos.sprite.move(x + 1, y, local=True)
            else:
               pos.sprite.move(x - 1, y, local=True)
      self.firstMove = False

   def isValidMove(self, x, y):
      deltax = abs(x - self.coords[0])
      deltay = abs(y - self.coords[1])
      if deltax <= 1 and deltay <= 1:
         pos = self.board[(x, y)]
         if pos is None or pos.color != self.color:
            return True
      elif deltax == 2 and deltay == 0 and not self.hasBeenInCheck and self.firstMove:
         # castle
         deltax = x - self.coords[0]
         if deltax < 0:
            endx = 0
         else:
            endx = self.board.width - 1
         pos = self.board[(endx, y)]
         if pos is not None and pos.abbreviation == 'R' and pos.firstMove:
            if deltax < 0:
               step = -1
            else:
               step = 1
            isValid = True
            for dx in xrange(self.coords[0] + step, endx, step):
               if self.board[(dx, self.coords[1])] is not None:
                  isValid = False
                  break
            if isValid and not self.inCheck(self.coords[0] + step, self.coords[1]):
               return True
      return False

   def __checkCastle(self, x, y, endx, step, moves):
      rook = self.board[(endx, y)]
      if root is not None and root.abbreviation == 'R' and rook.firstMove:
         for dx in xrange(x, endx, step):
            pos = self.board[(dx, y)]
            if pos is not None:
               return False
         moves.append((x + step + step, y))
      return True

   def getPossibleMoves(self):
      moves = []
      x = self.coords[0]
      y = self.coords[1]
      self.addMove(x + 1, y    , moves);
      self.addMove(x - 1, y    , moves);
      self.addMove(x    , y + 1, moves);
      self.addMove(x    , y - 1, moves);
      self.addMove(x + 1, y + 1, moves);
      self.addMove(x - 1, y + 1, moves);
      self.addMove(x + 1, y - 1, moves);
      self.addMove(x - 1, y - 1, moves);
      if self.firstMove and not self.hasBeenInCheck:
         # castles
         self.__checkCastle(x, y, 0, -1, moves)
         self.__checkCastle(x, y, self.board.width - 1, 1, moves)
      return moves

class ChessBoard:
   def __init__(self, ui):
      self.ui         = ui
      self.color      = WHITE
      self.sitColor   = None
      self.checkColor = None
      self.kings      = []
      self.width      = 8
      self.height     = 8
      self.board      = [None] * (self.width * self.height)
      self.running    = False
      self.timer      = None
      self.startTime  = 0

      self.standardBoard()

      self.piece_width  = self.board[0].sprite.width
      self.piece_height = self.board[0].sprite.height

   def pos(self, x, y):
      return y * self.width + x

   def __getitem__(self, p):
      return self.board[self.pos(p[0], p[1])]

   # reset board
   def __reset(self):
      for i in xrange(len(self.board)):
         if self.board[i] is not None:
            self.board[i].remove()
            self.board[i] = None
      self.kings = []

   def standardBoard(self):
      self.__reset()
      pieces = [
         (0, 0, Rook, BLACK), (1, 0, Knight, BLACK), (2, 0, Bishop, BLACK), (3, 0, Queen, BLACK), (4, 0, King, BLACK),
            (5, 0, Bishop, BLACK), (6, 0, Knight, BLACK), (7, 0, Rook, BLACK),
         (0, 7, Rook, WHITE), (1, 7, Knight, WHITE), (2, 7, Bishop, WHITE), (3, 7, Queen, WHITE), (4, 7, King, WHITE),
            (5, 7, Bishop, WHITE), (6, 7, Knight, WHITE), (7, 7, Rook, WHITE),
      ]
      for piece in pieces:
         _piece = piece[2](self, piece[3], [piece[0], piece[1]])
         self.board[self.pos(piece[0], piece[1])] = _piece
         if piece[2] == King:
            self.kings.append(_piece)
      for i in xrange(8):
         self.board[self.pos(i, 1)] = Pawn(self, BLACK, [i, 1])
         self.board[self.pos(i, 6)] = Pawn(self, WHITE, [i, 6])

   def tick(self):
      if self.running:
         self.ui.timer(self.onTimer)

   def onTimer(self):
      if self.running:
         seconds = str(int(time.time() - self.startTime))
         self.ui.set_clock(seconds)
         self.tick()

   def start(self):
      self.color      = WHITE
      self.checkColor = None
      self.running    = True
      self.startTime  = time.time()
      self.tick()
      self.ui.set_turn(COLORS[self.color])

   def stop(self):
      self.running = False

   # pawn promotion
   def promote(self, x, y):
      pos   = self.pos(x, y)
      piece = self.board[pos]
      if piece is not None and piece.abbreviation == '':
         piece.remove()
         self.board[pos] = Queen(self, piece.color, [x, y])

   def remove(self, x, y):
      pos   = self.pos(x, y)
      piece = self.board[pos]
      if piece is not None:
         piece.remove()
         self.board[pos] = None

   def makeMove(self, piece, oldpos, newpos, local=False):
      pos_old = self.pos(oldpos[0], oldpos[1])
      pos_new = self.pos(newpos[0], newpos[1])
      if self.board[pos_new] is not None:
         self.board[pos_new].remove()
         capture = 'x'
      else:
         if piece.abbreviation == '' and abs(oldpos[0] - newpos[0]) == 1 and abs(oldpos[1] - newpos[1]) == 1:
            capture = 'x'
         else:
            capture = ''
      self.board[pos_new] = self.board[pos_old]
      self.board[pos_old] = None
      if not local:
         state = self.__checkGameState()
         if state == STATE_MATE:
            check = '#'
         elif state == STATE_CHECK:
            check = '+'
         else:
            check = ''
         self.ui.add_move(movelabels(piece, capture, check, oldpos, newpos))
         self.color = (self.color + 1) % 2
         self.ui.set_turn(COLORS[self.color])
         if state not in [STATE_NONE, STATE_CHECK]:
            self.finish(state)
         elif state == STATE_CHECK:
            self.ui.in_check(COLORS[self.color])

   def finish(self, state):
      self.stop()
      self.ui.finish(state)

   def __hasValidMove(self, color):
      for piece in self.board:
         if piece is not None and piece.color == color and piece.hasValidMove():
            return True
      return False

   def __checkDirection(self, x, y, color, xDelta, yDelta, pieces):
      x += xDelta
      y += yDelta
      while x >= 0 and x < self.width and y >= 0 and y < self.height:
         piece = self.board[self.pos(x, y)]
         if piece is not None:
            if piece.color != color and piece.abbreviation in pieces:
               return True
            else:
               return False
         x += xDelta
         y += yDelta
      return False

   def __checkKnight(self, x, y, color):
      if x >= 0 and x < self.width and y >= 0 and y < self.height:
         piece = self.board[self.pos(x, y)]
         if piece is not None and piece.abbreviation == 'N' and piece.color != color:
            return True
      return False

   def __isChecked(self, king, otherKing):
      x     = king.coords[0]
      y     = king.coords[1]
      color = king.color

      if color == BLACK and y < 6:
         yDelta = 1
      else:
         yDelta = -1

      # check for close pawns
      if x > 0:
         piece = self.board[self.pos(x - 1, y + yDelta)]
         if piece is not None and piece.abbreviation == '' and piece.color != color:
            return True
      if x < 7:
         piece = self.board[self.pos(x + 1, y + yDelta)]
         if piece is not None and piece.abbreviation == '' and piece.color != color:
            return True

      # check cardinal directions and diagonals
      if self.__checkDirection(x, y, color, 1, 0, ['R', 'Q']) or \
         self.__checkDirection(x, y, color, -1, 0, ['R', 'Q']) or \
         self.__checkDirection(x, y, color, 0, 1, ['R', 'Q']) or \
         self.__checkDirection(x, y, color, 0, -1, ['R', 'Q']) or \
         self.__checkDirection(x, y, color, 1, 1, ['B', 'Q']) or \
         self.__checkDirection(x, y, color, -1, 1, ['B', 'Q']) or \
         self.__checkDirection(x, y, color, -1, -1, ['B', 'Q']) or \
         self.__checkDirection(x, y, color, 1, -1, ['B', 'Q']):
            return True

      # check king proximity
      deltax = abs(x - otherKing.coords[0])
      deltay = abs(y - otherKing.coords[1])
      if deltax <= 1 and deltay <= 1:
         return True

      # check knights
      if self.__checkKnight(x - 2, y - 1, color) or \
         self.__checkKnight(x - 2, y + 1, color) or \
         self.__checkKnight(x + 2, y - 1, color) or \
         self.__checkKnight(x + 2, y + 1, color) or \
         self.__checkKnight(x - 1, y - 2, color) or \
         self.__checkKnight(x - 1, y + 2, color) or \
         self.__checkKnight(x + 1, y - 2, color) or \
         self.__checkKnight(x + 1, y + 2, color):
            return True

      return False

   def __checkGameState(self):
      state = STATE_NONE
      if self.__isChecked(self.kings[0], self.kings[1]):
         self.checkColor = self.kings[0].color
         self.kings[0].hasBeenInCheck = True
      elif self.__isChecked(self.kings[1], self.kings[0]):
         self.checkColor = self.kings[1].color
         self.kings[1].hasBeenInCheck = True
      else:
         self.checkColor = None
      if self.checkColor is not None:
         if not self.__hasValidMove(self.checkColor):
            if self.checkColor == self.color:
               state = STATE_MATE
            else:
               state = STATE_STALE
         else:
            state = STATE_CHECK
      return state

   def inCheck(self, color):
      if self.kings[0].color == color:
         return self.__isChecked(self.kings[0], self.kings[1])
      else:
         return self.__isChecked(self.kings[1], self.kings[0])

   def handleMove(self, move):
      try:
         sx, sy, dx, dy = decodemove(move)
         for coord in [sx, dx]:
            if coord < 0 or coord >= self.width:
               raise TypeError, 'Invalid coord: %d' % coord
         for coord in [sy, dy]:
            if coord < 0 or coord >= self.height:
               raise TypeError, 'Invalid coord: %d' % coord
         pos = self.board[self.pos(sx, sy)]
         if pos is not None:
            pos.sprite.move(dx, dy)
         else:
            raise TypeError, 'Invalid move position: %d, %d' % (sx, sy)
      except:
         #traceback.print_exc()
         print 'Invalid move:', move

   def savepgn(self, fn, moves):
      # PGN: http://en.wikipedia.org/wiki/Portable_Game_Notation
      f = open(fn, 'w')
      # TODO: STR:
      f.write('[Event "Match Name"]\n')
      f.write('[Site "City, Region COUNTRY"]\n') # Format: City, Region COUNTRY
      f.write('[Date "2000.01.01"]\n')  # Format: YYYY.MM.DD
      f.write('[Round "1"]\n')
      f.write('[White "Last1, First1"]\n')  # Format: last name, first name
      f.write('[Black "Last2, First2"]\n')
      f.write('[Result "1/2-1/2"]\n')  # "1-0" (White), "0-1" (Black), "1/2-1/2" (Draw), "*" (other/ongoing)
      for item in moves:
         f.write(item + '\n')
      # TODO: any result other than * should be repeated at end
      f.close()
