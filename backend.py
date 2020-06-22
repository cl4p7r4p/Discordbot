import aiohttp
import json
import time
from datetime import datetime
import pytz
import discord
import config as cf

# Set Timezone
timezone = pytz.timezone("Europe/Berlin")

# RaidEvent Liste initialisieren
raidEvents = []

# Set Server Details
protocol = "https"
server = "cddt-wow.de"


base_url = protocol + "://" + server

functions = {
    # **number** = anzahl der nächsten Raids (für show raids)
    "list": "calevents_list&number=6&raids_only=1",
    # **number** = anzahl der nächsten Raids (für next)
    "nextevents": "calevents_list&number=7&raids_only=1",
    "details": "calevents_details&eventid=",
    "signup": "raid_signup&atype=user",
    "comment": "add_comment&atype=api",
    "chars": "user_chars"
}

# Rollen IDs
roleDict = {
    1: "Heal",
    2: "Tank",
    3: "Range DD",
    4: "Melee DD"
}

# Klassen IDs with custom Emoji
classDict = {
    2: "<:druide:673074897869864990>",
    3: "<:jger:673074895185248256>",
    4: "<:magier:673074898087837717>",
    6: "<:priester:673074898519982081>",
    7: "<:schurke:673074897450172447>",
    8: "<:schamane:673074897806950411>",
    9: "<:hexer:673074897790173204>",
    10: "<:krieger:673074895386837002>"
}

colors = {
    'green': 0x38f044,
    'red': 0xdb1d0f
}

# structure raidEventDic:
# {raidId : {title=raidtitle,embed=raidembed,iconURL=...}}
raidEventDic = {}


class EmbedEvent():
    def detailFormat(self):
        # Function returns the format of signups. 2: roles, 0: classes
        # (used for indexing the tuples)
        if len(self.data['raidstatus']['status0']['categories']) == 4:
            self.format = int(2)
            return
        elif len(self.data['raidstatus']['status0']['categories']) == 8:
            self.format = int(0)
            return
        else:
            return -1

    def getClassByID(self, x):
        # Returniert das Klassen-Emoji
        if x in classDict:
            return classDict[x]
        else:
            return "?"

    def signupPossible(self):
        return int(time.time()) < self.deadline_ts

    def footerText(self) -> str:
        timeNow = datetime.now().astimezone(timezone)

        text = ""
        strUpdate = "Letztes Update: {}".format(
            timeNow.strftime("%d.%m. um %H:%M")
        )
        if not self.signupPossible():
            text = "Die Raidanmeldung ist bereits geschlossen."
        else:
            text = "Die Raidanmeldung ist noch bis {} möglich.".format(
                timeToStr(self.deadline))

        returnstr = "{} \n{}".format(strUpdate, text)
        return returnstr

    def getRaidMember(self):
        # Charakternamen, Klassen, Rollen und Anmeldestatus extrahieren
        for status in self.data['raidstatus']:
            categories = self.data['raidstatus'][status]['categories']
            for category in categories:
                chars = categories[category]['chars']
                for char in chars:
                    if self.data['raidstatus'][status]['id'] == 0:
                        # Bestätigte
                        self.anmeldungen.append((
                            int(chars[char]['classid']),
                            chars[char]['name'] + " (B)",
                            int(categories[category]['id'])
                        ))
                    elif self.data['raidstatus'][status]['id'] == 1:
                        # Anmeldungen
                        self.anmeldungen.append((
                            int(chars[char]['classid']),
                            chars[char]['name'],
                            int(categories[category]['id'])
                        ))
                    elif self.data['raidstatus'][status]['id'] == 2:
                        # Abmeldungen
                        self.abmeldungen.append(
                            self.getClassByID(int(chars[char]['classid']))
                            + " "
                            + chars[char]['name']
                        )
                    elif self.data['raidstatus'][status]['id'] == 3:
                        # Ersatzbank
                        self.ersatzbank.append(
                            self.getClassByID(int(chars[char]['classid']))
                            + " "
                            + chars[char]['name'])
                    else:
                        return -1
        self.anmeldungen.sort()
        self.abmeldungen.sort()
        self.ersatzbank.sort()

    def getListById(self, x):
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

    def createEmbed(self):
        self.getRaidMember()
        embed = discord.Embed(title=self.raid_title,
                              url=base_url,
                              description=timeToStr(self.raid_date),
                              color=(
                                  colors['green'] if self.signupPossible()
                                  else colors['red'])
                              )
        embed.set_thumbnail(url=self.iconURL)
        embed.add_field(name="Anmeldungen", value="{} von {} Spielern".format(
            self.raid_signups, self.raid_maxcount), inline=False)
        if self.format == 2:
            embed.add_field(
                name="Tanks", value=self.getListById(2), inline=True)
            embed.add_field(
                name="Heiler", value=self.getListById(1), inline=True)
            embed.add_field(name="Range DD",
                            value=self.getListById(3), inline=True)
            embed.add_field(name="Melee DD",
                            value=self.getListById(4), inline=True)
        elif self.format == 0:
            embed.add_field(
                name="Krieger", value=self.getListById(10), inline=True)
            embed.add_field(
                name="Jäger", value=self.getListById(3), inline=True)
            embed.add_field(
                name="Magier", value=self.getListById(4), inline=True)
            embed.add_field(name="Priester",
                            value=self.getListById(6), inline=True)
            embed.add_field(
                name="Schurke", value=self.getListById(7), inline=True)
            embed.add_field(name="Schamane",
                            value=self.getListById(8), inline=True)
            embed.add_field(name="Hexenmeister",
                            value=self.getListById(9), inline=True)
            embed.add_field(
                name="Druide", value=self.getListById(2), inline=True)

        embed.add_field(name="Auf der Ersatzbank oder verspätet",
                        value=printListToLine(self.ersatzbank),
                        inline=False)
        embed.add_field(name="Abgemeldet",
                        value=printListToLine(self.abmeldungen),
                        inline=False)
        embed.set_footer(text=self.footerText())

        self.embedContent = embed

    def __init__(self, RaidObj):
        self.id = RaidObj.raidid
        self.data = RaidObj.data
        self.format = 1
        self.iconURL = RaidObj.iconURL
        self.raid_title = self.data['title']
        self.raid_date = self.data['start']
        self.deadline = self.data['deadline']
        self.deadline_ts = self.data['deadline_timestamp']
        self.raid_signups = self.data['raidstatus']['status0']['count'] + \
            self.data['raidstatus']['status1']['count']
        self.raid_maxcount = self.data['raidstatus']['status0']['maxcount']
        self.anmeldungen = []
        self.abmeldungen = []
        self.ersatzbank = []
        self.embedContent = None
        self.detailFormat()
        self.createEmbed()

    def getSignedUpMembers(self) -> list:
        signedUpMembers = (self.anmeldungen
                           + self.abmeldungen
                           + self.ersatzbank)

        return signedUpMembers


class EventObj():
    def __init__(self, id, data):
        self.raidid = id
        self.data = data
        self.raid_title = data['title']
        self.raid_date = data['start']
        self.deadline = data['deadline']
        self.deadline_ts = data['deadline_timestamp']
        self.iconURL = base_url + data['icon']
        self.startTime = "Am {}".format(timeToStr(data['start']))


async def updateEmbed(raidid, embed):
    raiddata = await getData(cf.mastertoken, "details", raidid)
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
    post = await postData(token, "signup", payload)
    return post


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def getData(token: str, fun: str, eventid=0, manual=False) -> dict:
    function = fun if manual else functions[fun]
    async with aiohttp.ClientSession() as session:
        content = await fetch(session,
                              base_url
                              + '/api.php?format=json&atoken='
                              + token
                              + '&function='
                              + function
                              + '{}'.format("" if eventid == 0 else eventid))
        # convert response to json
        content = json.loads(content)
        return content


async def postData(token: str, fun: str, payload):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(base_url + '/api.php?format=json&atoken='
                                    + token
                                    + '&function=' + functions[fun],
                                    data=payload) as resp:
                status = await resp.text()
        await session.close()
        return json.loads(status)
    except Exception as e:
        print('Error >> ', str(e))
        return -1


async def getNextEvents() -> list:
    # Function returns list of upcoming event IDs
    nextEvents = []
    data = await getData(cf.mastertoken, "list")
    for event in data['events']:
        if data['events'][event]['closed'] == 0:
            # make sure its an INT, sometime its STR
            nextEvents.append(int(data['events'][event]['eventid']))
        else:
            pass
    return nextEvents


async def getRaidDetails(id: int) -> EventObj:
    eventData = await getData(cf.mastertoken, "details", id)
    raidid = int(id)
    return EventObj(raidid, eventData)


async def makeRaidEvents(nextEvents: list):
    # Für jedes Event wird ein Eintrag im EventDictionary angelegt,
    # damit man einfacher auf die Daten zugreifen kann
    for eventid in nextEvents:
        eventObj = await getRaidDetails(eventid)
        raidEventDic[eventObj.raidid] = {"title": eventObj.raid_title}
        raidEventDic[eventObj.raidid]["iconURL"] = eventObj.iconURL
        raidEventDic[eventObj.raidid]["start"] = eventObj.startTime
        raidEventDic[eventObj.raidid]["embed"] = EmbedEvent(eventObj)


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
        str = "{0} um {1} Uhr".format(
            '.'.join(reversed(zeit.split(' ')[0].split('-'))),
            zeit.split(' ')[1])
    except Exception as e:
        print('Error >> ', str(e))
        str = "Dienstag: 12:32"
    return str


def printListToLine(liste):
    if len(liste) > 0:
        str = (', '.join(liste))
    else:
        str = "Niemand"
    return str
