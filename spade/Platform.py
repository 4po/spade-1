from AMS import AmsAgentDescription
from DF import DfAgentDescription, ServiceDescription
import xmpp
import threading
import Agent
import Envelope
import FIPAMessage
import AID
import Behaviour
import os.path
import sys
import traceback
import SocketServer
import SimpleHTTPServer
import BaseHTTPServer
import time
import thread
import copy
import ACLMessage
import types
import ACLParser
import BasicFipaDateTime

#from swi import SWIHandler
from wui import *
from os.path import *

class PlatformRestart(Exception):
    def __init__(self): pass
    def __str__(self): return



class SpadePlatform(Agent.PlatformAgent):
    

    class RouteBehaviour(Behaviour.Behaviour):
        
        def __init__(self):
            Behaviour.Behaviour.__init__(self)
            
        def _process(self):
            msg = self._receive(True)
            if (msg != None):
                print ">>> SPADE Platform Received a message: " + str(msg)
                if msg.getSender() == self.myAgent.getAID():
                    # Prevent self-loopholes
                    print "###ACC LOOP HOLE"
                    return

                to_list = msg.getReceivers()
                d = {}
                for to in to_list:
                    if not to.getAddresses()[0] in d:
                        d[to.getAddresses()[0]]=list()
                    d[to.getAddresses()[0]].append(to)
                for k,v in d.items():
                    newmsg = msg
                    newmsg.to = v
                    try:
                        protocol, receiver_URI = k.split("://")
                    except:
                        print ">>> Malformed Agent Address URI: " + str(k)
                        break

                    # Check if one of our MTPs handles this protocol
                    #switch(protocol)
                    if protocol in self.myAgent.mtps.keys():
                        print ">>> Message through protocol", str(protocol)
                        #ap = ACLParser.ACLxmlParser()
                        #payload = ap.encodeXML(newmsg)
                        payload = str(newmsg)

                        envelope = Envelope.Envelope()
                        envelope.setFrom(newmsg.getSender())
                        for i in newmsg.getReceivers():
                            envelope.addTo(i)
                        envelope.setAclRepresentation("fipa.acl.rep.string.std")  # Always the same?
                        envelope.setPayloadLength(len(payload))
                        envelope.setPayloadEncoding("US-ASCII")
                        envelope.setDate(BasicFipaDateTime.BasicFipaDateTime())
                        self.myAgent.mtps[protocol].send(envelope, payload)
                    else:
                        # Default case: it's an XMPP message
                        print ">>> Message through protocol XMPP"
                        platform = self.myAgent.getSpadePlatformJID().split(".",1)[1]
                        if not platform in receiver_URI:
                            # Outside platform
                            print ">>> Message for another platform"
                            self.myAgent.send(newmsg, "jabber")
                        else:
                            # THIS platform
                            print ">>> Message for current platform"
                            for recv in v:
                                #self.myAgent._sendTo(newmsg, recv.getName(), "jabber")
                                self.myAgent.send(newmsg, "jabber")

                    """
                    if k[7:] != self.myAgent.getSpadePlatformJID():
                        self.myAgent._sendTo(newmsg, k[7:])
                    else:
                        for recv in v:
                            self.myAgent._sendTo(newmsg, recv.getName())
                    # Reenviamos el msg a todos los destinatarios
                    # Tambien deberiamos comprobar el protocolo y usar una pasarela en el caso de que sea necesario.
                    #print "Message to", to.getName(), "... Posting!"
                    """
            else:
                print "ACC::dying... it shouldn't happen"

    def __init__(self, node, password, server, port, config=None):
        Agent.PlatformAgent.__init__(self, node, password, server, port, config=config, debug=[])

    def _setup(self):
        self.setDefaultBehaviour(self.RouteBehaviour())

        #self.addBehaviour(self.SWIBehaviour())
        #swi.SWIHandler.platform = self
        #self.wui = WUI(self)
        self.wui.registerController("index",self.index)
        self.wui.registerController("webadmin_indigo",self.webadmin_indigo)
        self.wui.registerController("agents", self.agents)
        self.wui.registerController("services", self.services)
        self.wui.registerController("sendmessage", self.sendmessage)
        self.wui.setPort(8008)
        self.wui.start()
        
        # Load MTPs
        self.mtps = {}
        for name,mtp in self.config.acc.mtp.items():
        #self.mtps[mtp.protocol] = mtp.instance(name)
            try:
                 mtp_path = "."+os.sep+"spade"+os.sep+"mtp"
                 if os.path.exists(mtp_path):
                      sys.path.append(mtp_path)
                 else:
                    # This path should come from the config file . . .
                      mtp_path = os.sep+"usr"+os.sep+"share"+os.sep+"spade"+os.sep+"mtp"
                      sys.path.append(mtp_path)

                 mod = __import__(name)
                 self.mtps[mtp['protocol']] = mod.INSTANCE(name,self.config,self)

            except Exception, e:
                print "EXCEPTION IMPORTING MTPS: ",str(e)
                _exception = sys.exc_info()
                if _exception[0]:
                     msg='\n'+''.join(traceback.format_exception(_exception[0], _exception[1], _exception[2])).rstrip()
                     print msg

    def takeDown(self):
        for k,mtp in self.mtps.items():
	    try:
                mtp.stop()
		del self.mtps[k]
            except:
                pass



    #Controllers
    def index(self):
        import sys
        import time
        servername = self.getDomain()
        platform = self.getName()        
        version = str(sys.version)
        the_time = str(time.ctime())
        return "webadmin_indigo.pyra", dict(servername=servername, platform=platform, version=version, time=the_time)

    def webadmin_indigo(self):
        import sys
        import time
        servername = self.getDomain()
        platform = self.getName()        
        version = str(sys.version)
        the_time = str(time.ctime())
        return "webadmin_indigo.pyra", dict(servername=servername, platform=platform, version=version, time=the_time)

    def agents(self):
        import sys
        import time
        servername = self.getDomain()
        platform = self.getName()        
        version = str(sys.version)
        the_time = str(time.ctime())
        search = self.searchAgent(AmsAgentDescription())
        """for agent in search:
            if not agent.has_key("fipa:state"):
                agent["fipa:state"] = ""
        """
        return "agents.pyra", dict(servername=servername, platform=platform, version=version, time=the_time, agents=search)

    def services(self):
        import sys
        import time
        servername = self.getDomain()
        platform = self.getName()        
        version = str(sys.version)
        the_time = str(time.ctime())
        search = self.searchService(DF.DfAgentDescription())
        servs = {}
        idn = 0
        for dad in search:
            for service in dad.getServices():
                if service.getType() not in servs.keys():
                    servs[service.getType()] = {}
                servs[service.getType()][idn] = {}
                servs[service.getType()][idn]["name"] = str(service.getName())
                servs[service.getType()][idn]["provider"] = str(dad.getAID().getName())
                servs[service.getType()][idn]["addresses"] = ""
                for address in dad.getAID().getAddresses():
                    servs[service.getType()][idn]["addresses"] += str(address)+" "
                idn += 1
        print servs
        return "services.pyra", dict(servername=servername, platform=platform, version=version, time=the_time, services=servs)

    def sendmessage(self, to):
        import sys
        import time
        servername = self.getDomain()
        platform = self.getName()        
        version = str(sys.version)
        the_time = str(time.ctime())

        search = self.searchAgent(AmsAgentDescription())
        agents = []
        for agent in search:
            agents.append(agent.getAID().getName())

        return "message.pyra", dict(servername=servername, platform=platform, version=version, time=the_time, keys=agents, to=to)





















    def getMembers(self,aname):
        msg = ACLMessage.ACLMessage()
        msg.setOntology("spade:x:organization")
        template = Behaviour.ACLTemplate()
        template.setConversationId(msg.getConversationId())
        t = Behaviour.MessageTemplate(template)
        b = self.GetMembersBehav()
        b.msg = msg
        b.aname = aname
        self.addBehaviour(b,t)
        b.join()
        return b.result

    class GetMembersBehav(Behaviour.OneShotBehaviour):
        def _process(self):
            self.result = []
	    self.msg.addReceiver(AID.aid(self.aname, addresses=["xmpp://"+self.aname]))
	    self.msg.setContent("MEMBERS")
	    self.myAgent.send(self.msg)
	    rep = None
	    rep = self._receive(True, 20)
	    if rep:
	        print "The members list arrived"
	        self.result = rep.getContent().split(",")





