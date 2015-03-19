#!/usr/bin/env python

import os
import sys
import time
import traceback

import Tkinter as tk
import tkFileDialog
import tkMessageBox
import tkSimpleDialog

from twisted.internet import tksupport, reactor

import chess_images
import chess_game
import chess_server

MARGIN = 10

def getuser():
   for env in ['LOGNAME', 'USERNAME', 'USER']:
      user = os.getenv(env)
      if user is not None:
         break
   if user is None:
      try:
         import pwd
         user = pwd.getpwuid(os.getuid())[0]
      except:
         user = None
   if user is None:
      user = os.getlogin()
   return user

class Highlight:
   def __init__(self, x, y, width, height, canvas, sprite):
      x = x - width / 2
      y = y - height / 2
      border = 2
      self.tag    = canvas.create_rectangle((x, y, x + width, y + height), outline='yellow', width=border)
      self.canvas = canvas

      canvas.tag_raise(sprite.tag)

   def hide(self):
      self.canvas.delete(self.tag)

class TkSprite:
   def __init__(self, gui, model, image, coords, canvas):
      self.gui     = gui
      self.model   = model
      self.image   = tk.PhotoImage(data=image)
      self.width   = self.image.width()
      self.height  = self.image.height()
      self.canvas  = canvas
      self.current = None
      self.suggest = None

      self.x, self.y = self.__make_coords(coords[0], coords[1])
      self.tag = canvas.create_image(self.x, self.y, image=self.image)
      canvas.tag_bind(self.tag, '<Button-1>'       , self.select)
      canvas.tag_bind(self.tag, '<ButtonRelease-1>', self.deselect)
      canvas.tag_bind(self.tag, '<B1-Motion>'      , self.drag)

   def __make_coords(self, x, y):
      x = MARGIN + self.width  / 2 + (x * self.width)
      y = MARGIN + self.height / 2 + (y * self.height)
      return x, y

   def remove(self):
      if self.tag:
         if self.current:
            self.current.hide()
            self.current = None
         if self.suggest:
            self.suggest.hide()
            self.suggest = None
         self.canvas.delete(self.tag)
         self.tag = None

   def move(self, x, y, local=False):
      self.model.update(x, y)
      self.x, self.y = self.__make_coords(x, y)
      self.model.makeMove((x, y), local=local)
      self.canvas.coords(self.tag, (self.x, self.y))

   def select(self, e):
      if self.model.canMove():
         self.current = Highlight(self.x, self.y, self.width, self.height, self.canvas, self)

   def deselect(self, e):
      if self.model.canMove():
         if self.suggest:
            self.suggest.hide()
            self.suggest = None
         if self.current:
            self.current.hide()
            self.current = None
         dx = (e.x - MARGIN) / self.width
         dy = (e.y - MARGIN) / self.height
         if self.model.checkMove(dx, dy):
            self.move(dx, dy)
         else:
            self.canvas.coords(self.tag, (self.x, self.y))

   def drag(self, e):
      if self.model.canMove():
         if self.suggest:
            self.suggest.hide()
            self.suggest = None
         dx = (e.x - MARGIN) / self.width
         dy = (e.y - MARGIN) / self.height
         if self.model.checkMove(dx, dy):
            x, y = self.__make_coords(dx, dy)
            self.suggest = Highlight(x, y, self.width, self.height, self.canvas, self)
         self.canvas.coords(self.tag, (e.x, e.y))

class ChessTkGUI(chess_game.ChessGUI):
   def __init__(self, frame, canvas, clock):
      self.frame  = frame
      self.canvas = canvas
      self.clock  = clock

   def make_sprite(self, model, name, coords):
      return TkSprite(self, model, getattr(chess_images, name), coords, self.canvas)

   def timer(self, func):
      self.canvas.after(1000, func)

   def set_clock(self, seconds):
      self.clock.set(seconds)

   def set_turn(self, color):
      self.frame.setTurn(color)

   def add_move(self, move):
      self.frame.addMove(move)

   def in_check(self, color):
      self.frame.showCheck(color)

   def finish(self, state):
      if state == chess_game.STATE_MATE:
         self.frame.status.set('Checkmate!')
         tkMessageBox.showinfo('Checkmate!', 'Checkmate! Game over!')
      elif state == chess_game.STATE_STALE:
         self.frame.status.set('Stalemate!')
         tkMessageBox.showinfo('Stalemate!', 'Stalemate! Game over!')
      elif state == chess_game.STATE_TIME:
         self.frame.status.set('Timeout!')
         tkMessageBox.showinfo('Timeout!', 'Out of time! Game over!')
      else:
         self.frame.status.set('Idle')

class ConnectDialog(tkSimpleDialog.Dialog):
   def body(self, master):
      tk.Label(master, text="Host:").grid(row=0)
      tk.Label(master, text="Port:").grid(row=1)

      self.view = tk.IntVar()

      self.e1 = tk.Entry(master)
      self.e2 = tk.Entry(master)
      self.e3 = tk.Checkbutton(master, text='View only', variable=self.view)

      self.e2.insert(0, str(chess_server.DEFAULT_PORT))

      self.e1.grid(row=0, column=1)
      self.e2.grid(row=1, column=1)
      self.e3.grid(row=3, column=0, columnspan=2)
      return self.e1 # initial focus

   def validate(self):
      if len(self.e1.get()) == 0:
         tkMessageBox.showwarning('Invalid Host', 'Please specify a host.')
         return 0
      else:
         try:
            port = int(self.e2.get())
         except:
            tkMessageBox.showwarning('Invalid Port', 'Please specify a valid port.')
            return 0
      return 1

   def apply(self):
      host = self.e1.get()
      port = int(self.e2.get())
      self.result = host, port, self.view.get()

class ServerDialog(tkSimpleDialog.Dialog):
   def body(self, master):
      tk.Label(master, text="Port:").grid(row=0)
      self.e1 = tk.Entry(master)
      self.e1.insert(0, str(chess_server.DEFAULT_PORT))
      self.e1.grid(row=0, column=1)
      return self.e1 # initial focus

   def validate(self):
      try:
         port = int(self.e1.get())
         return 1
      except:
         tkMessageBox.showwarning('Invalid Port', 'Please specify a valid port.')
      return 0

   def apply(self):
      self.result = int(self.e1.get())

class StatusBar(tk.Frame):
   def __init__(self, master):
      tk.Frame.__init__(self, master)
      #self.label = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W)
      self.label = tk.Label(self, bd=1, anchor=tk.W)
      self.label.pack(fill=tk.X)

   def set(self, format, *args):
      self.label.config(text=format % args)
      self.label.update_idletasks()

   def clear(self):
      self.label.config(text="")
      self.label.update_idletasks()

class Application(tk.Frame):
   def __toggleButtons(self, state=tk.DISABLED):
      self.localGame.config(state=state)
      self.sitWhite.config(state=state)
      self.sitBlack.config(state=state)

   def startLocalGame(self):
      self.status.set('Running')
      self.__toggleButtons()
      self.board.sitColor = None
      self.board.start()

   def startWhite(self):
      self.status.set('Running')
      self.__toggleButtons()
      self.board.sitColor = chess_game.WHITE
      self.board.start()
      color = chess_game.COLORS[chess_game.WHITE]
      self.showSit(self.getUser(), color)
      self.net.sit(color)

   def startBlack(self):
      self.status.set('Running')
      self.__toggleButtons()
      self.board.sitColor = chess_game.BLACK
      self.board.start()
      color = chess_game.COLORS[chess_game.BLACK]
      self.showSit(self.getUser(), color)
      self.net.sit(color)

   def remoteSit(self, name, color):
      if self.board.sitColor is None:
         if color == 'white':
            self.sitWhite.config(state=tk.DISABLED)
         else:
            self.sitBlack.config(state=tk.DISABLED)
      else:
         # make sure we sit opposite opponent
         self.__toggleButtons()
         self.board.sitColor = (chess_game.COLORS.index(color) + 1) % 2
      self.showSit(name, color)

   def remoteNewGame(self):
      # TODO: ask if we should proceed?
      self.__reset()

   def createWidgets(self):
      self.localGame = tk.Button(self)
      self.localGame['text'] = 'Local Game'
      self.localGame['command'] = self.startLocalGame
      self.localGame.grid(row=0, column=0)

      self.sitWhite = tk.Button(self)
      self.sitWhite['text'] = 'Sit White'
      self.sitWhite['command'] = self.startWhite
      self.sitWhite.grid(row=0, column=1)

      self.sitBlack = tk.Button(self)
      self.sitBlack['text'] = 'Sit Black'
      self.sitBlack['command'] = self.startBlack
      self.sitBlack.grid(row=0, column=2)

      self.movesLabel = tk.Label(self, text='Moves')
      self.movesLabel.grid(row=0, column=3)

      self.canvas = tk.Canvas(self, width=450, height=450)
      self.canvas.grid(row=1, columnspan=3, sticky=tk.N+tk.S+tk.E+tk.W)

      photo = tk.PhotoImage(data=chess_images.board_yellow)
      self.board = self.canvas.create_image(MARGIN + photo.width() / 2, MARGIN + photo.height() / 2, image=photo)
      self.board_image = photo

      self.clock = tk.StringVar()
      self.gui   = ChessTkGUI(self, self.canvas, self.clock)
      self.board = chess_game.ChessBoard(self.gui)

      self.lastRemoteMove = None

      # grid labels
      x = MARGIN + self.board.piece_width / 2
      y = photo.height() + self.board.piece_height / 2
      for i in xrange(8):
         self.canvas.create_text(x, y, text=chr(ord('A') + i))
         x += self.board.piece_width
      x = photo.width() + self.board.piece_width / 2
      y = MARGIN + self.board.piece_height / 2
      for i in xrange(8):
         self.canvas.create_text(x, y, text=chr(ord('8') - i))
         y += self.board.piece_height

      self.yScrollMoves = tk.Scrollbar(self, orient=tk.VERTICAL)
      self.yScrollMoves.grid(row=1, column=4, sticky=tk.N+tk.S)
      self.xScrollMoves = tk.Scrollbar(self, orient=tk.HORIZONTAL)
      self.xScrollMoves.grid(row=2, column=3, sticky=tk.E+tk.W)
      self.moves = tk.Listbox(self, xscrollcommand=self.xScrollMoves.set, yscrollcommand=self.yScrollMoves.set)
      self.moves.grid(row=1, column=3, sticky=tk.N+tk.S+tk.E+tk.W)
      self.xScrollMoves['command'] = self.moves.xview
      self.yScrollMoves['command'] = self.moves.yview

      self.net = chess_server.ChessNetwork(self)

      self.chatLabel = tk.Label(self, text='Chat:')
      self.chatLabel.grid(row=3, column=0, sticky=tk.W)

      self.usersLabel = tk.Label(self, text='Users')
      self.usersLabel.grid(row=3, column=3)

      self.chatLines = tk.Text(self, height=1, state=tk.DISABLED)
      self.chatLines.grid(row=4, columnspan=3, sticky=tk.N+tk.S+tk.E+tk.W)

      self.chatText = tk.StringVar()
      self.chatEntry = tk.Entry(self, textvariable=self.chatText)
      self.chatEntry.grid(row=5, columnspan=3, sticky=tk.E+tk.W)
      self.chatEntry.bind('<Return>', self.sendChat)

      self.yScrollUsers = tk.Scrollbar(self, orient=tk.VERTICAL)
      self.yScrollUsers.grid(row=4, column=4, rowspan=1, sticky=tk.N+tk.S)
      self.xScrollUsers = tk.Scrollbar(self, orient=tk.HORIZONTAL)
      self.xScrollUsers.grid(row=5, column=3, sticky=tk.E+tk.W)
      self.users = tk.Listbox(self, xscrollcommand=self.xScrollUsers.set, yscrollcommand=self.yScrollUsers.set)
      self.users.grid(row=4, column=3, rowspan=1, sticky=tk.N+tk.S+tk.E+tk.W)
      self.xScrollUsers['command'] = self.users.xview
      self.yScrollUsers['command'] = self.users.yview

      self.status = StatusBar(self)
      #self.status.pack(side=tk.BOTTOM, fill=tk.X)
      self.status.grid(row=6, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
      self.status.set('Idle')

      self.clockLabelLabel = tk.Label(self, text='Time:')
      self.clockLabelLabel.grid(row=6, column=1, sticky=tk.E)
      self.clockLabel = tk.Label(self, textvariable=self.clock)
      self.clockLabel.grid(row=6, column=2, sticky=tk.W)

      self.user = tk.StringVar()
      self.userLabel = tk.Label(self, textvariable=self.user)
      self.userLabel.grid(row=6, column=3)
      self.user.set('User: ' + getuser())

      top = self.winfo_toplevel()
      self.menuBar = tk.Menu(top)
      top['menu'] = self.menuBar

      self.subMenu = tk.Menu(self.menuBar)
      self.menuBar.add_cascade(label='File', menu=self.subMenu)
      self.subMenu.add_command(label='New Game', underline=0, command=self.__newGame, accelerator='Ctrl+N')
      self.subMenu.add_command(label='Save Moves', underline=0, command=self.__saveGame, accelerator='Ctrl+S')
      self.subMenu.add_command(label='Quit', command=self.quit, accelerator='Ctrl+X')

      self.netMenu = tk.Menu(self.menuBar)
      self.menuBar.add_cascade(label='Networking', menu=self.netMenu)
      self.netMenu.add_command(label='Connect', underline=0, command=self.__connect, accelerator='Ctrl+C')
      self.netMenu.add_command(label='Start Server', command=self.__startServer, accelerator='Ctrl+R')
      self.netMenu.add_command(label='Change User Name', underline=7, command=self.__changeName, accelerator='Ctrl+U')

      self.subMenu = tk.Menu(self.menuBar)
      self.menuBar.add_cascade(label='Help', menu=self.subMenu)
      self.subMenu.add_command(label='About', command=self.__aboutHandler)

      self.bind_all('<Control-n>', self.__newGame)
      self.bind_all('<Control-s>', self.__saveGame)
      self.bind_all('<Control-x>', self.exit)
      self.bind_all('<Control-c>', self.__connect)
      self.bind_all('<Control-r>', self.__startServer)
      self.bind_all('<Control-u>', self.__changeName)

   def __aboutHandler(self):
      tkMessageBox.showinfo('pychess-twisted', 'A python chess implementation using the twisted networking framework.')

   def __reset(self):
      self.board.stop()
      self.board.standardBoard()
      self.clock.set('')
      self.lastRemoteMove = None
      if self.moves.size() > 0:
         self.moves.delete(0, tk.END)
      # TODO: allow players to change colors
      if self.board.sitColor is None:
         self.__toggleButtons(tk.NORMAL)
         self.status.set('Idle')
      else:
         self.board.start()

   def __newGame(self, e=None):
      self.__reset()
      self.net.newGame()

   def __saveGame(self, e=None):
      if self.moves.size() > 0:
         fn = tkFileDialog.asksaveasfilename(defaultextension='pgn')
         if fn is not None and len(fn) > 0:
            try:
               self.board.savepgn(fn, self.moves.get(0, tk.END))
               tkMessageBox.showinfo('Moves Saved', 'Moves saved successfully to: ' + fn)
            except:
               traceback.print_exc()
               tkMessageBox.showerror('Save Error', 'Error saving moves to file: ' + fn)
      else:
         tkMessageBox.showerror('Save Error', 'No moves available to save')

   def exit(self, e=None):
      self.quit()

   def __disableNetMenus(self):
      self.netMenu.entryconfig('Connect', state=tk.DISABLED)
      self.netMenu.entryconfig('Start Server', state=tk.DISABLED)

   def __connect(self, e=None):
      dlg = ConnectDialog(self)
      if dlg.result is not None:
         host, port, view = dlg.result
         self.net.connect(host, port, view)
         self.__disableNetMenus()

   def __startServer(self, e=None):
      dlg = ServerDialog(self)
      port = dlg.result
      if port is not None:
         self.net.serve(port)
         self.__disableNetMenus()

   def __changeName(self, e=None):
      newuser = tkSimpleDialog.askstring('Change User Name', 'User name:', initialvalue=self.getUser())
      if newuser is not None and len(newuser) > 0:
         self.user.set('User: ' + newuser)
         self.net.changeName(newuser)

   def addMove(self, move):
      self.moves.insert(tk.END, move[1])
      self.moves.see(tk.END)
      self.sendMove(move[0])

   def showSit(self, name, color):
      self.addChatLine('*** %s sat %s' % (name, color))

   def showCheck(self, color):
      self.addChatLine('*** %s in check!' % color)

   def addChatLine(self, text):
      self.chatLines.config(state=tk.NORMAL)
      self.chatLines.insert(tk.END, text + '\n')
      self.chatLines.see(tk.END)
      self.chatLines.config(state=tk.DISABLED)

   def sendChat(self, e):
      chat = self.chatText.get()
      if len(chat) > 0:
         chat = self.getUser() + '> ' + chat
         self.addChatLine(chat)
         self.net.sendChat(chat)
         self.chatText.set('')

   def getUser(self):
      return self.user.get()[6:]

   def addUser(self, user):
      self.users.insert(tk.END, user)
      self.users.see(tk.END)

   # remove first match
   def removeUser(self, user):
      if self.users is not None and self.users.size() > 0:
         index = 0
         for _user in self.users.get(0, tk.END):
            if _user == user:
               self.users.delete(index)
               break
            index += 1

   # remove all matches
   def removeUsers(self, users):
      if self.users is not None and self.users.size() > 0:
         index = 0
         for user in self.users.get(0, tk.END):
            if user in users:
               self.users.delete(index)
            else:
               index += 1

   def sendMove(self, move):
      if move != self.lastRemoteMove:
         self.net.sendMove(move)

   def handleMove(self, move):
      self.lastRemoteMove = move
      self.board.handleMove(move)

   def setTurn(self, color):
      self.status.set(color + ' turn')

   def quit(self):
      #print 'Quit'
      self.shutdown()

   def shutdown(self, destroy=True):
      #print 'Shutting down'
      self.users = None
      reactor.callWhenRunning(reactor.stop)
      self.board.stop()
      self.net.stop()
      if destroy:
         self.master.destroy()

   def __init__(self, master=None):
      tk.Frame.__init__(self, master)
      self.pack()
      #self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
      self.createWidgets()
      master.protocol('WM_DELETE_WINDOW', self.shutdown)

if __name__ == '__main__':
   root = tk.Tk()
   tksupport.install(root) # twisted tk support

   app = Application(master=root)
   app.master.title('pychess-twisted')
   app.master.minsize(600, 400)

   # bring app to front
   #app.master.attributes('-topmost', 1)
   app.master.lift()
   if sys.platform == 'darwin':
      os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

   # delegate mainloop to twisted
   #app.mainloop()
   reactor.run()
   #app.shutdown(False)
   #root.destroy()
