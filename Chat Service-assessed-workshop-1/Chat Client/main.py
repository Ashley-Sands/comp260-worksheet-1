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
currentChatter = "All"

host = "localhost"
port = 8225

class GlobalData:

    def __init__(self):
        self.socket_inst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clear = False;

    def NewSocketInst(self):

        if not self.clear:
            return

        if self.socket_inst is not None:
            self.socket_inst.close()    # make sure the old socket has been closed!

        self.socket_inst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


globalData = GlobalData()
globalDataLock = threading.Lock();

isRunning = True
isConnected = False

dataQueue = queue.Queue()
screenName = "client-Error";

def receiveThread(socket):
    global  isConnected
    print('Starting ReceiveThread')
    while isConnected:

        try:
            # receive the first 2 bytes containing the data length
            data = socket.recv(2)
            message_len = int.from_bytes(data, "big")
            # decode the message and add it to the sync queue ready to be printed in the display :)
            message = socket.recv(message_len).decode("utf-8")
            dataQueue.put( message, block=True, timeout=None )

        except Exception as e:
            print(e, "unable to receive message from server.")
            isConnected = False
            globalData.clear = True

        time.sleep(1);

    print('Ending ReceiveThread')


def backgroundThread():
    print('Starting backgroundThread')

    global isRunning, isConnected, receive_thread

    while isRunning:
        if not isConnected:
            try:
                # Lock?

                globalData.NewSocketInst()
                globalData.socket_inst.connect((host, port))
                isConnected = True
                receive_thread = threading.Thread(target=receiveThread, args=(globalData.socket_inst,))
                receive_thread.start()
            except Exception as e:
                print(e, "unable to connection to server")
                time.sleep(1)
        else:
            time.sleep(1)

    print('Ending backgroundThread')


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

        while not dataQueue.empty():
            # get the data from the que and run the required task
            jsonDataStr = ""
            jsonDict = {}

            try:
                jsonDataStr = dataQueue.get(block=False, timeout=0.09)
            except:
                break;

            print("Got Data", jsonDataStr)

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
                    self.AddMessage( jsonDict["msg"] )
                elif id == 5:   # send and receive public messages
                    self.AddMessage( jsonDict["msg"])
                elif id == 6:   # receive screen name assigned buy server.
                    self.SetScreenName( jsonDict["name"] )
            except Exception as e:
                print(e)

    def SendMessage(self, data):

        try:
            jsonData = json.dumps(data)
        except:
            print("Bad data to json..", type(data))
            return

        messageLen = len(jsonData).to_bytes(2, "big")

        try:
            globalData.socket_inst.send( messageLen )
            globalData.socket_inst.send( jsonData.encode() )
        except Exception as e:
            print("Unable to send message: ", e)

    def SetUsersList(self, users):
        # refresh the current users list
        self.clientList.clear()
        self.clientList.addItems( users )

    def SetScreenName(self, uname):

        global screenName
        screenName = uname

    def AddMessage(self, message, user=""):

        if len(user) > 0:
            message = user +": "+ message

        self.chatOutput.insertPlainText(message+"\n");

    def OnSendMessage(self):

        entry = { "ID": 5, "msg": self.userInput.text() }

        if currentChatter != "All":
            entry["ID"] = 4
            entry["target"] = str(currentChatter)
        else:
            entry["msg"] = screenName +": "+ entry["msg"]

        self.SendMessage( entry )
        self.userInput.setText('')

        print('OnSendMessage: ', entry)

    def OnSetMessageTarget(self):
        global currentChatter

        currentChatter = self.clientList.currentItem().text() #Row()

        print('OnSetMessageTarget: '+str(currentChatter))

    def OnChangeName(self):
        entry = { "ID" : 2, "name" : self.userName.text() }
        self.SendMessage( entry )
        print('OnChangeName: ', entry)

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
        global isRunning, isConnected

        isRunning = False

        if currentBackgroundThread is not None:
            currentBackgroundThread.join()

        if isConnected:
            isConnected = False

            globalData.socket_inst.shutdown(socket.SHUT_RDWR)   # close the connection

            # globalData.socket_inst.detach()                     # close the socket, leaving the underlying file descriptor in tac
                                                                # to prevent any errors from any recv still waiting to receive # does not always work?
            globalData.socket_inst.close()                      # close the socket once and for all, ready for GC
            print("All closed");

        if receive_thread is not None:
            receive_thread.join(2)


if __name__ == '__main__':

    if len(sys.argv) > 1:
        host = sys.argv[1]

        if len(sys.argv) > 2:
            try:
                port = int(sys.argv[2])
            except:
                pass
            
    app = QApplication(sys.argv)
    client = ChatClient()

    currentBackgroundThread = threading.Thread(target=backgroundThread, args=())
    currentBackgroundThread.start()

    sys.exit(app.exec_())