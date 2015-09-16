# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
from getpass import getpass
from json import loads
from random import choice, randint
from re import match
from urllib import urlopen
from xmpp import Client, JID, Message, NS_MUC, Presence

config = ConfigParser()
config.read('jupisnbg.cfg')
user = config.get('user', 'jid')
user_password = config.get('user', 'password')
room = config.get('room', 'jid')
room_password = config.get('room', 'password')
nick = config.get('room', 'nick')

with open('witze.txt') as f:
    jokes = f.read().splitlines()

with open('witze_anarchy.txt') as g:
    jokes_anarchy = g.read().splitlines()

def message_callback(client, stanza): # get msgs
    sender = stanza.getFrom()
    message = stanza.getBody()
    message = unicode(message)

    if sender.bareMatch(room):
        sender_nick = sender.getResource()
        print(('[r] %s: %s' % (sender_nick, message)).encode('utf-8'))

        # message forwarding
	if "@jupisnbg" in message:
            # replied from group
            jupi_repliedby = sender.getResource()
            jupi_message = message.replace("@jupisnbg", "") 
            jupi_message = jupi_message.split(" ", 1)[1]
            receiver = jupi_message.split(" ", 1)[0]
            if "@" in receiver and "." in receiver: 
                jupi_message = jupi_message.replace(receiver, "")
                jupi_reply = "[" + jupi_repliedby +  "]: " + jupi_message
                client.send(Message(to = receiver, body = jupi_reply, typ = "chat"))
            elif "--help" in receiver: 
                client.send(Message(to = room, body = "Usage: [at]jupisnbg full_jabber_id_of_recipient message.", typ = "groupchat"))

        # insult people
        m = match(r'\.insult (.*)', message)
        if m:
            msg_room('%s is an idiot.' % (m.group(1)))
            return

        # say things
        m = match(r'''\.say (["']?)(.*)\1''', message)
        if m:
            text = m.group(2)
            if not text:
                msg_room(' ')
            else:
                msg_room(text)
            return

        # throw a dice
        m = match(r'\.dice (\d+)', message)
        if m:
            faces = int(m.group(1))
            msg_room('/me rolls a dice with %d faces.' % (faces))
            if faces:
                msg_room('The dice shows %d (trust me).' % (randint(1, faces)))
            else:
                msg_room('fuck you. -.-')
            return
        
        # show a kitten
        m = match(r'\.kitten', message)
        if m:
            link = urlopen('http://random.cat/meow')
            pic = link.read()
            msg_room("uhm... ok. Here is a picture of a cute cat: %s." % (pic))
            return

        # make a joke
        m = match(r'''\.joke (["']?)(.*)\1''', message)
        if m:
            text = m.group(2)
            if text == "anarchy":
                msg_room(choice(jokes_anarchy))
            else:
                msg_room(choice(jokes))
            return

        # query icndb
        m = match(r'\.icndb', message)
        if m:
            query = urlopen('http://api.icndb.com/jokes/random?escape=javascript&limitTo=explicit,nerdy')
            reply = loads(query.read())
            try:
                msg_room(reply['value']['joke'].decode('string_escape'))
            except KeyError:
                msg_room('Chuck Norris can query ICNDB without getting an error.')
            return

        # execute command
        m = match(r'\.([^ ]*) ?(.*)', message)
        if m:
            verb = m.group(1)
            rest = m.group(2)

            # third person singular form of verb (non-irregular)
            if verb.endswith('s') or verb.endswith('x'):
                verb += 'es'
            else:
                verb += 's'

            # genitive form of sender_nick
            if not sender_nick.endswith('s') and not sender_nick.endswith('x'):
                sender_nicks = sender_nick + 's'
            else:
                sender_nicks = sender_nick

            # fix pronoums
            rest = rest.split(' ')
            for i, word in enumerate(rest):
                if word == 'me' or word == 'myself':
                    rest[i] = sender_nick
                elif word == 'my':
                    rest[i] = sender_nicks
                elif word == 'you':
                    rest[i] = 'they'
                elif word == 'your':
                    rest[i] = 'their'
                elif word == 'yourself':
                    rest[i] = 'themself'
            rest = ' '.join(rest)

            msg_room('/me %s %s' % (verb, rest))
            return
    else:
        sender_nick = sender.getNode()
        print(('[p] %s: %s' % (sender_nick, message)).encode('utf-8'))
        sendertext = "[" + unicode(sender)  + "]: " + message
        test = client.send(Message(to = room, body = sendertext, typ = "groupchat"))

def presence_callback(client, stanza):
    # not used yet
    pass

def join_room(extension=None):
    if extension:
        presence = Presence(to='%s/%s+%s' % (room, nick, extension))
    else:
        presence = Presence(to='%s/%s' % (room, nick))
    presence.setTag('x', namespace=NS_MUC).setTagData('password', room_password)
    presence.getTag('x').addChild('history',{'maxchars':'0','maxstanzas':'0'})
    client.send(presence)

def msg_room(message):
    send_msg(room, message, typ='groupchat')

def send_msg(to, message, typ='chat'):
    client.send(Message(to=to, body=message, typ=typ))

# connect to server
client = Client(JID(user).getDomain(), debug=[])
client.connect()
while not client.auth(JID(user).getNode(), user_password, resource=JID(user).getResource()):
    print('Unable to authorize.')
    password = getpass('Password for %s:' % (user))

# register handlers
client.RegisterHandler('message', message_callback)
client.RegisterHandler('presence', presence_callback)

# send presence
client.sendInitPresence()
join_room()

# process incoming messages
while True:
    client.Process(1)
