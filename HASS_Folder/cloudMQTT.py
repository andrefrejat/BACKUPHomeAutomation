import paho.mqtt.client as mqtt

import time



CLOUD_USER = "andrefrejat@gmail.com"

CLOUD_PASS = "45f66b00"



def local_on_connect(client,userdata,rc):

	if(not rc):

		print("Locally connected")

	else:

		print("Locally NOT connected")





def local_on_message(client,userdata,msg):

	print("Received local msg!")
	msg.payload = msg.payload.decode('utf-8')
	print("Topic: {} .... Msg: {}".format(msg.topic,msg.payload))
	if(not str(msg.payload).startswith("inner")):

		formattedStr = "/andrefrejat@gmail.com/broker2" + msg.topic
		print("Publishing cloud... Topic: {} .... Msg: {}\n\n\n".format(formattedStr,msg.payload))

		mqttclient.publish(formattedStr,msg.payload)
	else:
		print("It was inner")



# Define event callbacks

def on_connect(client, userdata, rc):

	if rc == 0:

		print("Cloud connected successfully.")

	else:

		print("Cloud connection failed. rc= "+str(rc))



def on_publish(client, userdata, mid):

	print("Cloud message "+str(mid)+" published.")



def on_subscribe(client, userdata, mid, granted_qos):

	print("Cloud subscribe with mid "+str(mid)+" received.")



def on_message(client, userdata, msg):

	print("Received cloud msg")
	msg.payload = msg.payload.decode('utf-8')
	msg.topic = msg.topic[len("/andrefrejat@gmail.com/broker1"):]
	print("Topic: {} .... Msg: {}".format(msg.topic,msg.payload))

	print("Sending in.... Topic: {} .... Msg: {}".format(msg.topic,("inner"+msg.payload)))
	if(msg.topic.startswith("/update/callback")):
		localClient.publish(msg.topic,msg.payload)
	else:
		localClient.publish(msg.topic,("inner"+msg.payload))







localClient = mqtt.Client()

localClient.on_message = local_on_message

localClient.on_connect = local_on_connect

localClient.connect("192.168.1.35",1883,60)



mqttclient = mqtt.Client()

mqttclient.on_connect = on_connect

mqttclient.on_publish = on_publish

mqttclient.on_subscribe = on_subscribe

mqttclient.on_message = on_message



# Connect

mqttclient.username_pw_set(CLOUD_USER, CLOUD_PASS)

mqttclient.connect("mqtt.dioty.co", 1883)



# Start subscription

mqttclient.subscribe("/andrefrejat@gmail.com/broker1/#")

localClient.subscribe("#")
localClient.unsubscribe("/update/callback/#")


# Loop; exit on error

print("starting program...")

rc = 0

while rc == 0:

	mqttclient.loop()

	localClient.loop()

	time.sleep(0.1)
