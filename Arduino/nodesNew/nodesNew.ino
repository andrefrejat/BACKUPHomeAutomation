/********************************************************************************
 *                      André Botelho - Home automation project                 *
 *                                                                              *   
 * This code requires a few third party libraries                               *
 *      https://github.com/knolleary/pubsubclient                               *
 *      https://github.com/tzapu/WiFiManager                                    *  
 *                                                                              *
 *  -Serial is ALWAYS used as TX_ONLY                                                      *
 ********************************************************************************/
#include <HAConstants.h>
#include <PubSubClient.h>
#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>

HAConst HAC = HAConst();

const int NODE_TYPE = HAC.light3;

//Declaration of all 4 possible GPIO and its status
//The direction of use will be set within setup()
const int pins[4] = {0,1,2,3};
boolean pinStatus[4] = {HAC.nodeOFF,HAC.nodeOFF,HAC.nodeOFF,HAC.nodeOFF};
int pinFunction[4] = {HAC.nodeNA,HAC.nodeNA,HAC.nodeNA,HAC.nodeNA};

WiFiClient localWifiClient;
void localCallback(char* topic, byte* payload, unsigned int length);
PubSubClient localClient(localWifiClient);
WiFiManager wifiManager;

//REMEMBER!!!!
//Serial can NOT be used when light4 mode and double switch
const bool useSerial = true;

bool nodeRegistered = false;
String macAddrStr;


unsigned long previousMillis = 0;
const long interval = 1000;  


void printSerial(char* msg){if(useSerial) Serial.println(msg);};



void setup(){
  //Auxiliary variable
  uint8_t macAddr[6];
  
  
  (useSerial ? Serial.begin(115200,SERIAL_8N1,SERIAL_TX_ONLY) : wifiManager.setDebugOutput(false));
  if(useSerial && (NODE_TYPE == HAC.light4 || NODE_TYPE == HAC.doubleSwitch)){
    Serial.println("NODE_TYPE can NOT be this one and have serial output at the same time");
    while(1){delay(100);};
  }
  
  (wifiManager.autoConnect("Home Automation Setup") ? void(0) : wifiManager.resetSettings());

  //Once connected to wifi we can get the mac address....
  WiFi.macAddress(macAddr);
  //...and transform it into a String
  for(int i=0;i<6;i++){
    macAddrStr += String(macAddr[i],16);  
    if(String(macAddr[i],16)=="0")  macAddrStr += '0';
  }

  HAC.setVals((char*)macAddrStr.c_str(),(char*)String(NODE_TYPE).c_str());

  //Now that we connected and set the topics to the appropriate format we can connect to MQTT broker
  //This version of the function will connect both to the local broker and the cloud one
  connectMQTT((char*)macAddrStr.c_str());

  //Now that we (tried?) connected to the MQTT brokers we have to register the new node in the HA server
  registerDevice();

  //IMPORTANT!!!!!! The order of the following two functions MATTER A LOT
  setPinsMode();
  subscribeTopics();

  printSerial("\n\nSTART!!\n");
}

void loop(){
  String auxLoopStr;
  
  localClient.loop();
  delay(10);

  for(int i=0 ; i < 4; i++){
    if(pinFunction[i] == HAC.nodeIN){
      if(!digitalRead(pins[i])){
        while(!digitalRead(pins[i])){delay(10);}
        delay(100);

        pinStatus[i-1] = !pinStatus[i-1];
        digitalWrite(pins[i-1],pinStatus[i-1]);
        auxLoopStr = String(HAC.getStatusCallback());
        auxLoopStr += "/" + String(i-1);
        localClient.publish((char*)auxLoopStr.c_str(),((pinStatus[i-1] == HAC.nodeON) ? "ON" : "OFF"));
      }
    }
  }

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    if(!localClient.connected()){
      if(!connectMQTT((char*)macAddrStr.c_str())){
        ESP.restart();
      }
    }

    if(!localWifiClient.connected()){(wifiManager.autoConnect("Home Automation Setup") ? void(0) : wifiManager.resetSettings());}
  }
}

boolean connectMQTT(char* usrName){
  unsigned int counter=0;
  boolean somethingWentWrong = false;
  localClient.setServer(HAC.getMQTTIP(),HAC.getMQTTPort());

  while(!localClient.connect(usrName) && counter < 20){
    delay(100);
    counter++;
    printSerial("Trying again to connect to local MQTT");
  }
  if(counter<20) printSerial("Connected to local MQTT");
  else somethingWentWrong = true;
  
  //If it got here it connected to local broker.
  localClient.setCallback(localCallback);
}

boolean registerDevice(){
  localClient.subscribe(HAC.getDiscoverCallback());
  
  unsigned int counter = 0;
  while(!nodeRegistered && (counter<100)){
    printSerial("...Device still not registered....");

    localClient.publish(HAC.getDiscoverTopic(),HAC.getRegisterPayload());
    localClient.loop();
    
    counter++;
    delay(1000);
  }

  if(nodeRegistered){
    localClient.unsubscribe(HAC.getDiscoverCallback());
    printSerial("Registered on server");
  }

  return nodeRegistered;
}

void setPinsMode(){
  if(NODE_TYPE == HAC.light1){
    pinFunction[0] = HAC.nodeNA;
    pinFunction[1] = HAC.nodeNA;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeNA;
  }
  else if(NODE_TYPE == HAC.light2){
    pinFunction[0] = HAC.nodeOUT;
    pinFunction[1] = HAC.nodeNA;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeNA;
  }
  else if(NODE_TYPE == HAC.light3){
    pinFunction[0] = HAC.nodeOUT;
    pinFunction[1] = HAC.nodeNA;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeOUT;
  }
  else if(NODE_TYPE == HAC.light4){
    pinFunction[0] = HAC.nodeOUT;
    pinFunction[1] = HAC.nodeOUT;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeOUT;
  }
  else if(NODE_TYPE == HAC.singleSwitch){
    pinFunction[0] = HAC.nodeNA;
    pinFunction[1] = HAC.nodeNA;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeIN;
  }
  else if(NODE_TYPE == HAC.doubleSwitch){  
    pinFunction[0] = HAC.nodeOUT;
    pinFunction[1] = HAC.nodeIN;
    pinFunction[2] = HAC.nodeOUT;
    pinFunction[3] = HAC.nodeIN;    
  }

  for(int i = 0; i < 4; i++){
    ((pinFunction[i]==HAC.nodeOUT) ? pinMode(pins[i],OUTPUT) : void(0));
  }
}

void subscribeTopics(){
  String auxStr;
  
  localClient.subscribe(HAC.getStatusTopic());
  localClient.subscribe(HAC.getResetTopic());
  
  for(int i=0 ; i < 4 ; i++){
    if(pinFunction[i] == HAC.nodeOUT){
      auxStr = String(HAC.getUpdateTopic());
      auxStr += "/" + String(i);
      localClient.subscribe((char*)auxStr.c_str());
      printSerial((char*)auxStr.c_str());
    }
  }
}

void localCallback(char* topic, byte* payload, unsigned int length){
  String payloadStr = "";
  String auxStr;
  for(int i=0;i<length;i++){
    payloadStr += (char)payload[i];
  }
  printSerial((char*)payloadStr.c_str());

  if(payloadStr.startsWith("inner")){
    printSerial("Payload before inner");
    printSerial((char*)payloadStr.c_str());
    payloadStr = payloadStr.substring(sizeof("inner"));
    printSerial("Payload after inner");
    printSerial((char*)payloadStr.c_str());
  }

  printSerial("\n\n!!!Received MQTT message!!!");

  if(String(topic)==(HAC.getDiscoverCallback()) && !nodeRegistered){
    printSerial("Discover topic received");
    
    if(payloadStr == "Registered"){
      nodeRegistered = true;
      printSerial("Node registration successfull! =D");
    }
    else{
      printSerial("Node registration NOT successfull");
    }
  }

  

  else if(String(topic).startsWith(HAC.getStatusTopic())){
    printSerial("Got a status topic...Sending my outputs status");

    for(int i=0 ; i< 4 ; i++){
      if(pinFunction[i] == HAC.nodeOUT){
          auxStr = String(HAC.getStatusCallback());
          auxStr += "/" + String(i);
          localClient.publish((char*)auxStr.c_str(),((pinStatus[i] == HAC.nodeON) ? "ON" : "OFF"));
      }
    }
  }

  else if(String(topic).startsWith(HAC.getUpdateTopic())){
    printSerial("Got a update topic...Checking which pin is it and updating");
    auxStr = String(topic).substring(String(HAC.getUpdateTopic()).length()+1);
    int pin = atoi(String(topic).substring(String(HAC.getUpdateTopic()).length()+1).c_str());

    if(payloadStr == "ON"){
      if(pinFunction[pin] == HAC.nodeOUT){
        pinStatus[pin] = HAC.nodeON;
        digitalWrite(pins[pin],pinStatus[pin]);
        localClient.publish(HAC.getStatusCallback((char*)auxStr.c_str()),"ON");
        Serial.println(HAC.formatTopic(HAC.getStatusCallback((char*)auxStr.c_str())));
      }
    }
    else if(payloadStr == "OFF"){
      if(pinFunction[pin] == HAC.nodeOUT){
        pinStatus[pin] = HAC.nodeOFF;
        digitalWrite(pins[pin],pinStatus[pin]);
        localClient.publish(HAC.getStatusCallback((char*)auxStr.c_str()),"OFF");
        Serial.println(HAC.formatTopic(HAC.getStatusCallback((char*)auxStr.c_str())));
      }
    }
  }

  else if(String(topic).startsWith(HAC.getResetTopic())){
    printSerial("Resetting!!......see you in a bit x)");
    delay(10);
    ESP.restart();
  }
}



