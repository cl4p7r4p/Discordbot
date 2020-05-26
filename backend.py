import aiohttp
import asyncio
import json
import time
import discord
import config as cf

## RaidEvent Liste initialisieren
raidEvents = []

protocol = "https"
server = "cddt-wow.de"


base_url = protocol + "://" + server

functions = {
    "list" : "calevents_list&number=6&raids_only=1", ## **number** = anzahl der nächsten Raids
    "nextevents" : "calevents_list&number=6&raids_only=1", ## **number** = anzahl der nächsten Raids
    "details": "calevents_details&eventid=",
    "signup" : "raid_signup&atype=user",
    "comment" : "add_comment&atype=api",
    "chars": "user_chars"
}

## Rollen IDs
roleDict = {
    1: "Heal",
    2: "Tank",
    3: "Range DD",
    4: "Melee DD"
}

## Klassen IDs
classDict = {
    2 : "<:druide:673074897869864990>",
    3 : "<:jger:673074895185248256>",
    4 : "<:magier:673074898087837717>",
    6 : "<:priester:673074898519982081>",
    7 : "<:schurke:673074897450172447>",
    8 : "<:schamane:673074897806950411>",
    9 : "<:hexer:673074897790173204>",
    10 : "<:krieger:673074895386837002>"
    }

class EmbedEvent():
    def detailFormat(self):
        # Function returns the format of signups. 2: roles, 0: classes (used for indexing the tuples)
        if len(self.data['raidstatus']['status0']['categories']) == 4:
            self.format = int(2)
            return
        elif len(self.data['raidstatus']['status0']['categories']) == 8:
            self.format = int(0)
            return
        else:
            return -1

    def getClassByID(self,x):
        # Returniert das Klassen-Emoji
        if x in classDict:
            return classDict[x]
        else:
            return "?"

    def footerText(self):
        if int(time.time())>self.deadline_ts:
            return "Die Raidanmeldung ist bereits geschlossen."
        else:
            return "Die Raidanmeldung ist noch bis {} möglich.".format(timeToStr(self.deadline))


    def getRaidMember(self):
        ## Charakternamen, Klassen, Rollen und Anmeldestatus aus dem JSON extrahieren
        for status in self.data['raidstatus']:
            for category in self.data['raidstatus'][status]['categories']:
                for char in self.data['raidstatus'][status]['categories'][category]['chars']:
                    if self.data['raidstatus'][status]['id'] == 0: ## Bestätigte
                        self.anmeldungen.append((int(self.data['raidstatus'][status]['categories'][category]['chars'][char]['classid']), self.data['raidstatus'][status]['categories'][category]['chars'][char]['name'] + " (B)", int(self.data['raidstatus'][status]['categories'][category]['id'])))
                    elif self.data['raidstatus'][status]['id'] == 1: ## Anmeldungen
                        self.anmeldungen.append((int(self.data['raidstatus'][status]['categories'][category]['chars'][char]['classid']), self.data['raidstatus'][status]['categories'][category]['chars'][char]['name'], int(self.data['raidstatus'][status]['categories'][category]['id'])))
                    elif self.data['raidstatus'][status]['id'] == 2: ## Abmeldungen
                        self.abmeldungen.append(self.getClassByID(int(self.data['raidstatus'][status]['categories'][category]['chars'][char]['classid'])) + " " + self.data['raidstatus'][status]['categories'][category]['chars'][char]['name'])
                    elif self.data['raidstatus'][status]['id'] == 3: ## ersatzbank
                        self.ersatzbank.append(self.getClassByID(int(self.data['raidstatus'][status]['categories'][category]['chars'][char]['classid'])) + " " + self.data['raidstatus'][status]['categories'][category]['chars'][char]['name'])
                    else:
                        return -1
        self.anmeldungen.sort()
        self.abmeldungen.sort()
        self.ersatzbank.sort()

    def getListById(self,x):
        # gibt entweder eine Liste der Rollen oder Klassen aus
        strList = ""
        for tup in self.anmeldungen:
            if tup[self.format] == x:
                strList += self.getClassByID(tup[0]) + " " + tup[1] + "\n"
            else:
                pass
        # print("Liste:\n" + strList)
        if len(strList) > 0:
            return strList
        else:
            return ":ghost:"

    def printListToLine(self,liste):
        if len(liste) > 0:
            str = (', '.join(liste))
        else:
            str = "Niemand"
        # print("To Line: " + str)
        return str

    def createEmbed(self):
        self.getRaidMember()
        embed = discord.Embed(title=self.raid_title, url=base_url, description="Datum und Zeit: {}".format(self.raid_date), color=0xa73ee6)
        embed.set_author(name="Die drei R präsentieren:")
        embed.set_thumbnail(url=self.iconURL)
        embed.add_field(name="Anmeldungen", value="{} von {} Spielern".format(self.raid_signups,self.raid_maxcount), inline=False)
        if self.format == 2:
            embed.add_field(name="Tanks", value=self.getListById(2), inline=True)
            embed.add_field(name="Heiler", value=self.getListById(1), inline=True)
            embed.add_field(name="Range DD", value=self.getListById(3), inline=True)
            embed.add_field(name="Melee DD", value=self.getListById(4), inline=True)
        elif self.format == 0:
            embed.add_field(name="Krieger", value=self.getListById(10), inline=True)
            embed.add_field(name="Jäger", value=self.getListById(3), inline=True)
            embed.add_field(name="Magier", value=self.getListById(4), inline=True)
            embed.add_field(name="Priester", value=self.getListById(6), inline=True)
            embed.add_field(name="Schurke", value=self.getListById(7), inline=True)
            embed.add_field(name="Schamane", value=self.getListById(8), inline=True)
            embed.add_field(name="Hexenmeister", value=self.getListById(9), inline=True)
            embed.add_field(name="Druide", value=self.getListById(2), inline=True)

        embed.add_field(name="Auf der Ersatzbank oder verspätet", value=self.printListToLine(self.ersatzbank), inline=False)
        embed.add_field(name="Abgemeldet", value=self.printListToLine(self.abmeldungen), inline=False)
        embed.set_footer(text=self.footerText())

        self.embedContent = embed

    def __init__(self,id,data):
        self.id = id
        self.data = data
        self.format = 1
        self.iconURL = base_url + data['icon']
        self.raid_title = data['title']
        self.raid_date = data['start']
        self.deadline = data['deadline']
        self.deadline_ts = data['deadline_timestamp']
        self.raid_signups = data['raidstatus']['status0']['count'] + data['raidstatus']['status1']['count']
        self.raid_maxcount = data['raidstatus']['status0']['maxcount']
        self.anmeldungen = []
        self.abmeldungen = []
        self.ersatzbank = []
        self.embedContent = None
        self.detailFormat()
        self.createEmbed()


class RaidEvent():
    def __init__(self, title, id, starttime, data):
        self.title = title
        self.ID = id
        self.starttime = starttime
        self.isPosted = False
        self.messageID =  0
        self.channelID = 0
        self.deadline_ts = data['deadline_timestamp']
        self.creationTime = int(time.time())
        self.embed = EmbedEvent(id, data)
        self.iconURL = base_url + data['icon']

    async def update(self):
        raiddata = await getData(cf.mastertoken, "details", self.ID)
        if raiddata == self.embed.data:
            return
        else:
            self.embed = EmbedEvent(self.ID, raiddata)
            self.creationTime = int(time.time())


async def updateEmbed(raidid, embed):
        raiddata = await getData(cf.mastertoken, "details", raidId)
        if raiddata == embed.data:
            return embed
        else:
            return EmbedEvent(raidid, raiddata)

async def raidSignup(token, raidid, memberid, status, note):
        payload = {
            "eventid": raidid,
            "memberid": memberid,
            "status": status,
        }
        if len(note) > 1:
            payload['note'] = note
        payload = json.dumps(payload)
        print("trying to post signup")
        post = await postData(token,"signup", payload)
        return post

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def getData(token,fun,eventid=0):
    async with aiohttp.ClientSession() as session:
        content = await fetch(session, base_url+'/api.php?format=json&atoken='+token+'&function='+functions[fun]+'{}'.format("" if eventid==0 else eventid))
        # convert response to json
        content = json.loads(content)
        if int(content['status'])==1:
            return content
        else:
            return -1


async def postData(token,fun,payload):
    # print("trying to post data at: {}".format(base_url+'/api.php?format=json&atoken='+token+'&function='+functions[fun]))
    # print("with payload: {}".format(payload))
    try:
        async with  aiohttp.ClientSession() as session:
            async with session.post(base_url+'/api.php?format=json&atoken='+token+'&function='+functions[fun], data=payload) as resp:
                status = await resp.text()
        await session.close()
        return json.loads(status)
    except:
        return -1

async def getNextEvents():
    nextEvents = []
    data = await getData(cf.mastertoken,"list")
    for event in data['events']:
        if data['events'][event]['closed'] == 0:
            nextEvents.append(data['events'][event]['eventid'])
        else:
            pass
    return nextEvents

async def getRaidDetails(id):
    eventData = await getData(cf.mastertoken,"details",id)
    title = eventData['title']
    start = eventData['start']
    raidid = int(id)
    return title,raidid,start,eventData


async def makeRaidEvents(nextEvents):
    for eventid in nextEvents:
        details = await getRaidDetails(eventid)
        raidEvents.append(RaidEvent(details[0],details[1],details[2],details[3]))


async def preperation():
    eventliste = await getNextEvents()
    await makeRaidEvents(eventliste)

def getEventById(id):
    print("suche Raid mit ID: {}".format(id))
    for event in raidEvents:
        if event.ID == int(id):
            return event
    return -1

def timeToStr(zeit):
    try:
        str = "{0} um {1} Uhr".format('.'.join(reversed(zeit.split(' ')[0].split('-'))),zeit.split(' ')[1])
    except:
        str="Dienstag: 12:32"
    return str
