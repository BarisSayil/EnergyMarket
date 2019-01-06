from multiprocessing import Process, Value, Lock, Array
from sysv_ipc import MessageQueue, IPC_CREAT
import random
from time import sleep
import datetime
from concurrent.futures import ThreadPoolExecutor
import sys
from threading import Thread


mutex = Lock()

class Home(Process):

    numberOfHomes=0

    def __init__(self,productionRate, consumptionRate):
        super().__init__()
        Home.numberOfHomes+=1
        self.budget=1000
        self.productionRate=productionRate
        self.consumptionRate=consumptionRate
        self.energy=0
        self.homeNumber=Home.numberOfHomes
        self.mqInit=MessageQueue(1000) #Default Queue
        self.mqInit.send((str(self.homeNumber)).encode()) #Tells market Home x neeeds MQ
        

    def run(self):
        theMQhasBeenCreated = 0
        while theMQhasBeenCreated == 0:
            try:
                self.mq = MessageQueue(128+self.homeNumber)
            except:
                print("Mq not exists yet")
                sleep(2)
            else:
                theMQhasBeenCreated = 1
                print("Home: MQ created !")
        sleep(5)
        print("Home {}: Starting to send requests to Market !".format(self.homeNumber))
        while 1:
            print("Home {}: My budget is {} dollars.".format(self.homeNumber,self.budget))
            self.energy=self.productionRate-self.consumptionRate

            if self.energy<0:
                self.buy()
            elif self.energy>0:
                self.sell()


            if self.budget<0:
                print("Home {}: Shit I'm broke!".format(self.homeNumber))
                self.sendMessage('Broke')
                break

            sleep(5)

    def sendMessage(self,n):
        self.mq.send(str(n).encode())
        print("Home{} sent: {}".format(self.homeNumber,n))


    def receiveMessage(self):
        message, t = self.mq.receive()
        value = message.decode()
        print("Home{} recieved: {}".format(self.homeNumber,value))
        if value != "Buy" or value != "Nothing":
            value = int(value)
        return value


    def buy(self):
        print("Home {}: What's the price? I wanna buy some energy.".format(self.homeNumber))
        self.sendMessage('Buy')
        temporary=self.receiveMessage()
        if temporary != "Buy" or temporary != "Nothing":
            price=temporary
            print("Home {}: It seems the price is {} dollars.".format(self.homeNumber,price))
            self.budget+=self.energy*price
        else :
            print("There is an error, anyway...")

    def sell(self):
        print("Home {}: What's the price? I wanna sell some energy.".format(self.homeNumber))
        self.sendMessage('Sell')
        price=self.receiveMessage()
        print("Home {}: It seems the price is {} dollars.".format(self.homeNumber,price))
        self.budget+=self.energy*price


class Market(Process):

    def __init__(self):
        super().__init__()
        self.price=20
        self.messageQueueList=[]
        self.messageQueueList.append(MessageQueue(1000,IPC_CREAT))
        print("The market's messageQueueList: {}".format(self.messageQueueList))
        self.mqExists=False

    def lookAtRequests(self):
        print("Look at request launched")
        while self.mqExists == False:
            sleep(1)
            print("Market: No MQ yet")
        print("Market: Found MQ")
        while 1:
            for x in range(1,len(self.messageQueueList)):
                print(x)
                print(self.messageQueueList[x])
                value=self.receiveMessage(x)
                if value != '':
                    with ThreadPoolExecutor(max_workers = 3) as executor:
                        print("demand received")
                        executor.submit(self.handleMessage,value,x)

    def handleMessage(self,m,channel):
        if m=='Broke':
            print('Market: No more homes alive :(')

        elif m=='Buy':
            with mutex:
                print('Market: The price of energy is %s dollars.' %self.price)
                self.sendMessage(self.price,channel)
            print('Market: Energy is bought.')
            print("Market: Increasing the price")
            with mutex:
                self.price+=5

        elif m=='Sell':
            print('Market: The price of energy is %s dollars.' %self.price)
            with mutex:
            	self.sendMessage(self.price,channel)
            print('Market: Energy is sold.')
            print("Market: Decreasing the price")
            with mutex:
            	self.price-=2

    def newMQ(self):
        while 1:
            print("new MQ while loop")
            x = self.receiveMessage(0)
            if x != "":
                print("Market received demand of new MQ")
                homeNb = int(x)
                print("Home",homeNb,"demands a MQ")
                self.messageQueueList.append(MessageQueue(128+homeNb,IPC_CREAT))
                print("Modified the messageQueueList")
                print(self.messageQueueList)
                self.mqExists = True
                print(self.mqExists)
            sleep(1)

    def run(self):
        print("Creation du thread newMQ")
        createMQ = Thread(target=self.newMQ ,args= ())
        createMQ.start()
        print("Creation du thread requestLook")
        requestLook = Thread(target=self.lookAtRequests , args=())
        requestLook.start()
        print("Lancements termines ! ")
        print('Market: The price of energy is now %s dollars.' %self.price)
        sleep(10)

    def sendMessage(self, n, index):
        self.messageQueueList[index].send(str(n).encode())
        print("Market sent: {}".format(n))

    def receiveMessage(self,index):
        message, t = self.messageQueueList[index].receive()
        value = message.decode()
        print("Market recieved: {}".format(value))
        return value




if __name__=="__main__":

    market=Market()
    market.start()

    home1=Home(0,10)
    home1.start()
