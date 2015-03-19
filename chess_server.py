# simple text-based protocol to communicate between chess clients

from twisted.internet  import reactor, protocol, endpoints
from twisted.protocols import basic

DEFAULT_PORT = 3333

# forward messages to other clients, keep track of users/seats/moves for future connections
class ChessServerProtocol(basic.LineReceiver):
   def __init__(self, factory):
      self.factory = factory
      self.name    = None

   def connectionMade(self):
      self.factory.clients.add(self)
      for name in self.factory.names:
         self.sendLine('NAME' + name)
      for name, color in self.factory.seats.iteritems():
         self.sendLine('SIT' + name + ':' + color)
      for move in self.factory.moves:
         self.sendLine('MOVE' + move)

   def connectionLost(self, reason):
      self.factory.clients.remove(self)
      if self.name:
         self.factory.names.remove(self.name)
         self.factory.send('RNAME' + self.name, self)

   def lineReceived(self, line):
      if line.startswith('NAME'):
         self.name = line[4:]
         self.factory.names.append(self.name)
      elif line.startswith('CNAME'):
         oldName, newName = line[5:].split(':')
         self.factory.names.remove(oldName)
         self.factory.names.append(newName)
      elif line.startswith('RNAME'):
         self.factory.names.remove(line[5:])
      elif line.startswith('SIT'):
         name, color = line[3:].split(':')
         self.factory.seats[name] = color
      elif line.startswith('MOVE'):
         self.factory.moves.append(line[4:])
      elif line.startswith('NEWGAME'):
         self.factory.moves = []
      self.factory.send(line, self)

class ChessServerFactory(protocol.Factory):
   def __init__(self):
      self.clients = set()
      self.names   = []
      self.seats   = {}
      self.moves   = []

   def buildProtocol(self, addr):
      return ChessServerProtocol(self)

   def send(self, line, source):
      for c in self.clients:
         if c != source:
            c.sendLine(line)

# simple test protocol for sending chats and moves
class ChessClient(basic.LineReceiver):
   def __init__(self, factory, parent):
      self.name    = None
      self.factory = factory
      self.parent  = parent
      self.users   = []

   def changeName(self, name):
      self.sendLine('CNAME' + self.name + ':' + name)
      self.name = name

   def sendChat(self, text):
      self.sendLine('CHAT' + text)

   def sendMove(self, move):
      self.sendLine('MOVE' + move)

   def sit(self, color):
      self.sendLine('SIT' + self.name + ':' + color)

   def newGame(self):
      self.sendLine('NEWGAME')

   def connectionMade(self):
      #print 'Connected'
      self.factory.clients.add(self)
      self.name = self.parent.getUser()
      self.sendLine('NAME' + self.name)
      if self.factory.onConnectionMade:
         self.factory.onConnectionMade.callback(self)

   def connectionLost(self, reason):
      self.factory.clients.remove(self)
      self.parent.removeUsers(self.users)

   def lineReceived(self, line):
      if line.startswith('NAME'):
         name = line[4:]
         self.parent.addUser(name)
         self.users.append(name)
      elif line.startswith('CNAME'):
         oldName, newName = line[5:].split(':')
         self.parent.removeUser(oldName)
         self.parent.addUser(newName)
         self.users.remove(oldName)
         self.users.append(newName)
      elif line.startswith('RNAME'):
         self.parent.removeUser(line[5:])
      elif line.startswith('MOVE'):
         self.parent.handleMove(line[4:])
      elif line.startswith('CHAT'):
         self.parent.addChatLine(line[4:])
      elif line.startswith('SIT'):
         self.parent.remoteSit(*line[3:].split(':'))
      elif line.startswith('NEWGAME'):
         self.parent.remoteNewGame()
      else:
         print 'Invalid server command:', line

# protocol.ReconnectingClientFactory
class ChessClientFactory(protocol.ClientFactory):
   def __init__(self, parent, view_only):
      self.parent    = parent
      self.view_only = view_only
      self.clients   = set()

      self.onConnectionMade = None

   def buildProtocol(self, addr):
      return ChessClient(self, self.parent)

   def clientConnectionFailed(self, connector, reason):
      print 'connection failed:', reason.getErrorMessage()

   def clientConnectionLost(self, connector, reason):
      #print 'connection lost:', reason.getErrorMessage()
      pass

   def __send(self, method, *args):
      for client in self.clients:
         reactor.callFromThread(getattr(client, method), *args)

   def changeName(self, name):
      self.__send('changeName', name)

   def sendChat(self, text):
      self.__send('sendChat', text)

   def sendMove(self, move):
      self.__send('sendMove', move)

   def sit(self, color):
      self.__send('sit', color)

   def newGame(self):
      self.__send('newGame')

class ChessNetwork:
   def __init__(self, frame):
      self.frame  = frame
      self.server = None
      self.client = None

   def connect(self, host, port, view_only, allow_running=False, connected=None):
      if not allow_running and (self.client is not None or self.server is not None):
         self.stop()
      self.client = ChessClientFactory(self.frame, view_only)
      if connected:
         self.client.onConnectionMade = connected
      self.clientPort = reactor.connectTCP(host, port, self.client)

   def serve(self, port):
      if self.client is not None or self.server is not None:
         self.stop()
      #print 'Running server on port:', port
      self.server     = endpoints.TCP4ServerEndpoint(reactor, port)
      self.serverPort = None
      d = self.server.listen(ChessServerFactory())
      d.addCallback(self.serving)
      self.connect('localhost', port, False, True)

   def serving(self, port):
      if self.server:
         self.serverPort = port
      else:
         port.stopListening()

   def stop(self):
      d = None
      if self.client:
         self.clientPort.disconnect()
         self.client = self.clientPort = None
      if self.server:
         if self.serverPort is not None:
            d = self.serverPort.stopListening()
         self.server = self.serverPort = None
      return d

   def changeName(self, name):
      if self.client:
         self.client.changeName(name)

   def sendChat(self, chat):
      if self.client:
         self.client.sendChat(chat)

   def sendMove(self, move):
      if self.client:
         self.client.sendMove(move)

   def sit(self, color):
      if self.client:
         self.client.sit(color)

   def newGame(self):
      if self.client:
         self.client.newGame()
