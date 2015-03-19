#!/usr/bin/env trial

from twisted.internet import reactor, defer
from twisted.trial    import unittest
from twisted.test     import proto_helpers

import chess_game
import chess_server

class TestFrame:
   def __init__(self, name):
      self.name  = name
      self.users = []
      self.chats = []
      self.seats = {}
      self.move  = None

   def getUser(self):
      return self.name

   def removeUsers(self, users):
      for user in users:
         self.users.remove(user)

   def removeUser(self, user):
      self.users.remove(user)

   def addUser(self, user):
      self.users.append(user)

   def addChatLine(self, line):
      self.chats.append(line)

   def remoteSit(self, user, color):
      self.seats[user] = color

   def remoteNewGame(self):
      self.move = None

   def handleMove(self, move):
      self.move = move

class ChessServerTestCase(unittest.TestCase):
   def setUp(self):
      self.server_frame = TestFrame('name1')
      self.server       = chess_server.ChessNetwork(self.server_frame)
      self.server.serve(3333)

      # pacify trial
      connected = defer.Deferred()

      self.client_frame = TestFrame('name2')
      self.client       = chess_server.ChessNetwork(self.client_frame)
      self.client.connect('localhost', 3333, False, connected=connected)

      return connected

   def tearDown(self):
      self.client.stop()
      return self.server.stop()

   def test_chat(self):
      d = defer.Deferred()
      self.client.sendChat(self.client_frame.getUser() + '> hello world')
      d.addCallback(lambda x: (
         self.assertEqual(len(self.server_frame.chats), 1),
         self.assertEqual(self.server_frame.chats[0], 'name2> hello world')
      ))
      reactor.callLater(1, d.callback, None)
      return d

   def test_sit(self):
      d = defer.Deferred()
      self.client.sit('black')
      d.addCallback(lambda x: (
         self.assertEqual(len(self.server_frame.seats), 1),
         self.assertEqual(self.server_frame.seats['name2'], 'black')
      ))
      reactor.callLater(1, d.callback, None)
      return d

   def test_changename(self):
      d = defer.Deferred()
      d.addCallback(self._check_name_0)
      reactor.callLater(1, d.callback, None)
      return d

   def _check_name_0(self, unused):
      self.assertEqual(len(self.server_frame.users), 1)
      self.assertEqual(len(self.client_frame.users), 1)

      self.assertEqual(self.server_frame.users[0], 'name2')
      self.assertEqual(self.client_frame.users[0], 'name1')

      d = defer.Deferred()
      self.client.changeName('name3')
      d.addCallback(self._check_name_1)
      reactor.callLater(1, d.callback, None)
      return d

   def _check_name_1(self, unused):
      self.assertEqual(len(self.server_frame.users), 1)
      self.assertEqual(self.server_frame.users[0], 'name3')

      del self.server_frame.chats[:]

      d = defer.Deferred()
      self.client.sendChat(self.server_frame.users[0] + '> hello world')
      d.addCallback(self._check_name_2)
      reactor.callLater(1, d.callback, None)
      return d

   def _check_name_2(self, unused):
      self.assertEqual(len(self.server_frame.chats), 1)
      self.assertEqual(self.server_frame.chats[0], 'name3> hello world')

      d = defer.Deferred()
      self.client.changeName('name2')
      d.addCallback(self._check_name_3)
      reactor.callLater(1, d.callback, None)
      return d

   def _check_name_3(self, unused):
      self.assertEqual(len(self.server_frame.users), 1)
      self.assertEqual(self.server_frame.users[0], 'name2')

      del self.server_frame.chats[:]

      d = defer.Deferred()
      self.client.sendChat(self.server_frame.users[0] + '> hello world')
      d.addCallback(self._check_name_4)
      reactor.callLater(1, d.callback, None)
      return d

   def _check_name_4(self, unused):
      self.assertEqual(len(self.server_frame.chats), 1)
      self.assertEqual(self.server_frame.chats[0], 'name2> hello world')

   def test_moves(self):
      d = defer.Deferred()
      self.client.sendMove('A1A2')
      d.addCallback(self._check_move_newgame)

   def _check_move_newgame(self):
      self.assertEqual(self.server_frame.move, 'A1A2')
      d = defer.Deferred()
      self.client.newGame()
      d.addCallback(lambda x:
         self.assertIsNone(self.server_frame.move)
      )
      reactor.callLater(1, d.callback, None)
      return d

class FakePiece:
   def __init__(self, abbreviation):
      self.abbreviation = abbreviation

class ChessGameTestCase(unittest.TestCase):
   def test_movelabel(self):
      oldpos = (0, 6)
      newpos = (0, 5)
      simple, san = chess_game.movelabels(FakePiece(''), '', '', oldpos, newpos)
      self.assertEqual(simple, 'A2A3')

      sx, sy, dx, dy = chess_game.decodemove('A2A3')
      self.assertEqual(sx, 0)
      self.assertEqual(sy, 6)
      self.assertEqual(dx, 0)
      self.assertEqual(dy, 5)
