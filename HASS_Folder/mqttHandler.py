import paho.mqtt.client as mqtt
import json
import yaml
import time
import os

#Setting DEBUG string
DEBUG_NAME = "MQTT Handler: "

#This is the topic in which the server will SEND a message for the nodes to send its current status
STATUS_TOPIC = "/update/status"
#This is the topic in which the server will SUBSCRIBE to in order to receive all node status
STATUS_CALLBACK = "/update/callback/"
#This is the topic in which the server will SUBSCRIBE to listen when there is a new node to add
DISCOVER_TOPIC = "/discover/newDevices"
#This is the topic in which the server will SEND the status for a new node
DISCOVER_CALLBACK = "/discover/registerDevice/"
#This is the topic in which the server will SEND a message to a specific node and set its output state
#The topic will contain the desired ID. e.g. if the node ID is ff003 the topic will be "/ff003/status"
#This is the topic in which the server will SEND  a message so the node will reset
RESET_TOPIC = "/update/reset/"

NODES_TYPE = ["light","switch","double switch"]

YAML_FILE_NAME = "configuration.yaml"

LOG_FILE_NAME = "logMqtt.txt"

class MqttHandler():
	def __init__(self,MQTTServer_IP):
		print("Initializing MQTT instance")
		self.innerMQTT = mqtt.Client()
		self.innerMQTT.on_connect = self.on_connect
		self.innerMQTT.on_message = self.on_message
		self.innerMQTT.connect(MQTTServer_IP,1883,60)
		self.newDeviceFlag = False
		self.newDeviceData = None
		self.nodesStatus = []
		

	def on_connect(self,client, userdata, flags, rc):
		self.innerMQTT.subscribe(STATUS_CALLBACK+"#")
		self.innerMQTT.subscribe(DISCOVER_TOPIC)

	#Handles what to do when a message is received
	def on_message(self,client,userdata,msg):
		self.writeLog("\n" + DEBUG_NAME + "Got message!")

		#Possible new or unregistered device detected
		if(msg.topic == DISCOVER_TOPIC):
			#Check if not already on the list 
			#Device may already be on the list and simply turned OFF-ON
			self.writeLog("\n" + DEBUG_NAME + "Discover Topic")
			msg.payload = msg.payload.decode('utf-8')
			try:
				if self.registerNode(json.loads(msg.payload)):
					self.sendConfirmation(json.loads(msg.payload)["id"])
				else:
					self.writeLog("WHAT THE FU%$ HAPPENED????")
			except:
				print("Exception")
				if self.registerNode(json.loads(msg.payload)):
					self.sendConfirmation(json.loads(msg.payload)["id"])
				else:
					self.writeLog("WHAT THE FU%$ HAPPENED????")

		else:
			print("Received unknown topic: {}".format(msg.topic))
			self.writeLog(DEBUG_NAME + "Topic not implemented")

	#Check if candidate is knwon 
	def isKnown(self,nodeID,nodeType):
		with open(YAML_FILE_NAME,'r') as yamlFile:
			try:
				return True
			except Exception as e:
				self.writeLog("Something went wrong with trying to find out if node is known. Error: {}".format(e))
				return False

	#Adds new node to variable
	def registerNode(self,newNode):
		return self.registerYaml(newNode)


	#Sends register confirmation to node
	def sendConfirmation(self,registeredNodeID):
		self.writeLog(DEBUG_NAME + "Sending confirmation to node " + registeredNodeID)
		self.innerMQTT.publish(DISCOVER_CALLBACK + registeredNodeID,"Registered")	

	def resetAllNodes(self):
		self.writeLog("Initializing....Resetting system")
		self.innerMQTT.publish(RESET_TOPIC,"Reset now!")

	#Sends reset message to node
	def sendResetCommand(self,nodeID):
                self.writeLog(DEBUG_NAME + "Sending reset command to node " + nodeID)
                self.innerMQTT.publish(RESET_TOPIC + nodeID,"Reset now!!!!")

	
	def sendStatusUpdateMessage(self):
		self.innerMQTT.publish(STATUS_TOPIC,"Hey!!")

	def registerYaml(self,newNode):
		with open(YAML_FILE_NAME,'a') as inFile:
			try:		
				inFile.write("##########\n## Possible new node!\n#ID: {}\n#Type: {}\n##########".format(newNode["id"],newNode["type"]))
				return True
			except Exception as e:
				self.writeLog("Registration did not work. Problem: {}".format(e))
				return False

	def writeLog(self,message):
		try:
			with open(LOG_FILE_NAME,'a') as logFile:
				logFile.write(message + '\n')
				print(message)
		except Exception as e:
			print("Problem writing on log: {}".format(e))
 

if __name__ == "__main__":
	mqttc = MqttHandler("192.168.1.35")
	mqttc.sendStatusUpdateMessage()
	mqttc.resetAllNodes()
	while True:
		mqttc.innerMQTT.loop()
		time.sleep(0.1)
