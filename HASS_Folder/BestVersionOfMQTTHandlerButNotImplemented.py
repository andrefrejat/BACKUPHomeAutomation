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
			if not self.isKnown(json.loads(msg.payload)["id"],json.loads(msg.payload)["type"]):
				self.writeLog(DEBUG_NAME + "device unregistered")
				if self.registerNode(json.loads(msg.payload)):
					self.sendConfirmation(json.loads(msg.payload)["id"])
				else:
					self.writeLog("WHAT THE FU%$ HAPPENED????")
			else:
				self.writeLog(DEBUG_NAME + "Device already registered")
				self.writeLog(DEBUG_NAME + "Sending confirmation message")
				self.sendConfirmation(json.loads(msg.payload)["id"])
		else:
			print("Received unknown topic: {}".format(msg.topic))
			self.writeLog(DEBUG_NAME + "Topic not implemented")

	#Check if candidate is knwon 
	def isKnown(self,nodeID,nodeType):
		with open(YAML_FILE_NAME,'r') as yamlFile:
			try:
				data = yaml.load(yamlFile)
				items = data.get(NODES_TYPE[nodeType])
				#########################################################
				#
				print("Checking if is known....Data: {} ...... items: {}".format(str(data),str(items)))
				#
				#########################################################
				for index,item in enumerate(items):
					self.writeLog("Index: {} we have item {}".format(index,item))
					if item["name"] == nodeID:
						self.writeLog("Node is Known")
						return True
				self.writeLog("Node Unknown")
				return False
			except Exception as e:
				self.writeLog("Something went wrong with trying to find out if node is known. Error: {}".format(e))
				return False

	#Adds new node to variable
	def registerNode(self,newNode):
		#Final check to see if it is really a new one
		if not self.isKnown(newNode["id"],newNode["type"]):
			self.writeLog("Registering new node: {}".format(newNode["id"]))
			return self.registerYaml(newNode)
		else:
			return False


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
		with open(YAML_FILE_NAME,'r') as inFile:
			allData = yaml.load(inFile)	
		try:
			#print('newNode["type"]: {}'.format(newNode["type"]))
			if newNode["type"] == 0:
				return True
			elif newNode["type"] == 1:
				self.writeLog("Found switch type")
				allData["switch"].append({'name': '{}'.format(newNode["id"]), 'command_topic': '/{}/status'.format(newNode["id"]), 'platform': 'mqtt', 'state_topic': '/update/callback/{}'.format(newNode["id"]),'retain':'true'})
				allData["homeassistant"]["customize"]["switch.{}".format(newNode["id"])] = {'friendly_name':'New Node {}'.format(newNode["id"])}
				file = open(YAML_FILE_NAME,'w')
				yaml.dump(allData,file, default_flow_style=False)
				file.close()
				os.system("sudo systemctl restart home-assistant.service")
				return True
			elif newNode["type"] == 2:
				self.writeLog("Found double Switch")

				if not allData["switch"]:
					print("switch was not found")
					allData["switch"] = []
				else:
					print("Switch array found")
				allData["switch"].append({'name': '{}_switch1'.format(newNode["id"]), 'command_topic': '/{}/status/switch1'.format(newNode["id"]), 'platform': 'mqtt', 'state_topic': '/update/callback/{}/switch1'.format(newNode["id"]),'retain':'true'})
				allData["switch"].append({'name': '{}_switch2'.format(newNode["id"]), 'command_topic': '/{}/status/switch2'.format(newNode["id"]), 'platform': 'mqtt', 'state_topic': '/update/callback/{}/switch2'.format(newNode["id"]),'retain':'true'})
				self.writeLog("Adding to configuration file")
				file = open(YAML_FILE_NAME,'w')
				yaml.dump(allData,file, default_flow_style=False)
				file.close()
	
				if not hasattr(allData["homeassistant"],"customize"):
					allData["homeassistant"]["customize"] = {}
				allData["homeassistant"]["customize"]['switch.{}_switch1'.format(newNode["id"])] = {'friendly_name':'New Node {} switch 1'.format(newNode["id"])}
				allData["homeassistant"]["customize"]['switch.{}_switch2'.format(newNode["id"])] = {'friendly_name':'New Node {} switch 2'.format(newNode["id"])}
				file = open(YAML_FILE_NAME,'w')
				yaml.dump(allData,file,default_flow_style=False)
				file.close()
				return True
			else:
				self.writeLog("What type is it? I think it is not implemented....")
				return False	
		except Exception as e:
			self.writeLog("Registration did not work. Problem: {}".format(e))

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
