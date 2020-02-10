import sys
import PyQt5.QtCore
import PyQt5.QtWidgets

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtCore

import socket
import threading
import time
import json

import queue

currentBackgroundThread = None
receive_thread = None

isRunning = True
isConnected = False

dataQueue = queue.Queue()
screenName = "client-Error";

def receiveThread(socket_):

    while True:
        try:
            data = socket_.recv(2)
            message_len = int.from_bytes(data, "big")
            message = socket_.recv(message_len).decode("utf-8")
            dataQueue.put( message, block=True, timeout=None )
        except Exception as e:
            print(e, "unable to receive message from server.")

def backgroundThread():
    print('Starting backgroundThread')

    global isRunning, isConnected, receive_thread

    socket_inst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while isRunning:
        if not isConnected:
            try:
                socket_inst.connect(("localhost", 8225))
                receive_thread = threading.Thread(target=receiveThread, args=(socket_inst,))
                receive_thread.start()
                isConnected = True;
            except Exception as e:
                print(e, "unable to connection to server")
        else:
            time.sleep(1)



class ChatClient(QWidget):

    def __init__(self):
        super().__init__()

        self.chatOutput = 0
        self.userInput = 0

        self.initUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.timerEvent)
        self.timer.start(100)

    def timerEvent(self):

        # get the data from the que and run the required task
        jsonDataStr = ""
        jsonDict = {}

        try:
            jsonDataStr = dataQueue.get(block=True, timeout=0.09)
        except:
            pass

        print ("Helloo world")

        # if no data was received.
        if jsonDataStr is None or jsonDataStr == "":
            return

        # convert the json str into a dict :).
        try:
            jsonDict = json.loads( jsonDataStr )
            print ( jsonDict )
        except Exception as e:
            print (e)

        try:
            # do things with the data
            id = jsonDict["ID"]
            if id == 1:     # (inbound only) receive all users list
                self.SetUsersList( jsonDict["users"] )
            elif id == 2:   # (outbound only) send screen name to server
                pass        # Not needed here.
            elif id == 4:   # send and receive PMs
                pass
            elif id == 5:   # send and receive public messages
                pass
            elif id == 6:   # receive screen name assigned buy server.
                self.SetScreenName( jsonDict["name"] )
        except Exception as e:
            print(e)

    def SetUsersList(self, users):
        # refresh the current users list
        self.clientList.clear()
        self.clientList.addItems( users )

    def SetScreenName(self, uname):

        global screenName
        screenName = uname

    def OnSendMessage(self):
        entry = self.userInput.text()
        print('OnSendMessage: '+entry)

        self.userInput.setText('')

    def OnSetMessageTarget(self):
        entry = self.clientList.currentRow()
        print('OnSetMessageTarget: '+str(entry))

    def OnChangeName(self):
        entry = self.userName.text()
        print('OnChangeName: ' + entry)

    def initUI(self):
        self.userInput = QLineEdit(self)
        self.userInput.setGeometry(10, 360, 580, 30)
        self.userInput.returnPressed.connect(self.OnSendMessage)

        self.chatOutput = QPlainTextEdit(self)
        self.chatOutput.setGeometry(10, 10, 400, 335)
        self.chatOutput.setReadOnly(True)

        self.privateChatLabel = QLabel(self)
        self.privateChatLabel.setGeometry(420, 15, 150, 10)
        self.privateChatLabel.setText('Private Chat')

        self.clientList = QListWidget(self)
        self.clientList.setGeometry(420, 30, 170, 200)
        self.clientList.clicked.connect(self.OnSetMessageTarget)
        self.clientList.addItem('None')
        self.clientList.setCurrentRow(0)

        self.changeNameLabel = QLabel(self)
        self.changeNameLabel.setGeometry(420, 300, 150, 10)
        self.changeNameLabel.setText('User\'s Name')

        self.userName = QLineEdit(self)
        self.userName.setGeometry(420, 315, 170, 30)
        self.userName.returnPressed.connect(self.OnChangeName)
        self.userName.setText('Change Name')

        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Chat Client')
        self.show()

    def closeEvent(self, event):
        global isRunning
        isRunning = False

        if currentBackgroundThread is not None:
            currentBackgroundThread.join()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = ChatClient()

    currentBackgroundThread = threading.Thread(target=backgroundThread, args=())
    currentBackgroundThread.start()

    sys.exit(app.exec_())