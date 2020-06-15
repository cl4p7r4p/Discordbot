import time
import discord
import pickle
import backend
import config as cf

# ********* CONFIG PART ************

reactions = ["✅", "🚫", "💤"]
reactDict = {
    "✅": "anmelden",  # status 1
    "🚫": "abmelden",  # status 2
    "💤": "auf die Bank setzen"  # status 3,
}
reactStatus = {
    "✅": 1,  # status 1
    "🚫": 2,  # status 2
    "💤": 3  # status 3
}
status_options = [" :sparkle: Bestätigt", " :white_check_mark: Angemeldet",
                  " :no_entry_sign: Abgemeldet", " :zzz: Ersatzbank",
                  " :ghost: **ICH BIN EIN GESPENST**"]

NUM_RAIDS = 3

#####################


class Unauthorized(Exception):
    pass


class Guffelbot(discord.Client):

    raids_posted = 0

    def authorized(self, author):
        if author.id not in self.registered_users:
            raise Unauthorized()

    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        # List of current Raid IDs
        self.curEvents = []
        # to retrieve raid id by message id {messageID:raidID}
        self.eventDic = {}
        # to retrieve the id of the embed by raid id {raidId:messageId}
        self.postedRaids = {}
        self.refreshCooldown = 15  # min. time between embed refreshes
        self.cdTime = int(time.time())
        try:
            with open('users.pkl', 'rb') as f:
                self.registered_users = pickle.load(f)
        except Exception as e:
            print('Error >> ', str(e))
            self.registered_users = {}

    async def on_ready(self):
        print('Logged on as', self.user)
        try:
            await backend.preperation()
            print("All set. Let's go!")
        except Exception as e:
            print('Error >> ', str(e))
            print("das hat nicht geklappt")

    async def deletemsg(self, message):
        await message.channel.purge(limit=1)

    def is_me(self, m):
        return m.author == client.user

    def clearRaidShow(self):
        self.postedRaids = {}
        self.curEvents = []
        return

    async def on_message(self, message):
        if message.author == self.user:  # don't respond to ourselves
            return

        if message.content.startswith('!cddt'):
            if not isinstance(message.channel, discord.DMChannel):
                await self.deletemsg(message)
                await message.author.send("lass uns das hier klären :shushing_face:")
                return
            commands = message.content.lower().split(' ')
            try:
                await getattr(self, commands[1])(message.author, message.channel, commands[2:])
            except Unauthorized:
                auth_embed = discord.Embed(
                    title="Bitte richte zuerst dein Token ein.",
                    url="https://cddt-wow.de/index.php/Settings.html?s=",
                    description="Weitere Hilfe mit `!cddt help setup`"
                )
                await message.channel.send(embed=auth_embed)
            except Exception as e:
                print(e)
                await message.channel.send("Fehler beim Bearbeiten Deiner Anfrage")

        if message.content == 'quitt':
            if message.author.name == "hairypotta":
                # await self.deletemsg(message)
                await client.close()
            else:
                await message.channel.send("Du bist nicht mein Meister :poop:")

        if message.content == 'clean up for real 1337':
            if message.author.name == "hairypotta":
                await message.channel.purge(limit=50)
                self.clearRaidShow()
            else:
                await message.channel.send("Du bist nicht mein Meister :poop:")

        if message.content == 'show raids':
            # await self.deletemsg(message)
            if message.author.name == "hairypotta":
                await self.postRaids(message)

    async def postRaids(self, message):
        async with message.channel.typing():
            # displays the "typing" emote at avatar to show that bot is working
            nextEvents = (await backend.getNextEvents())
            await backend.makeRaidEvents(nextEvents)
            # check if the list of upcoming events has changed
            updateEmbed = (self.curEvents[:NUM_RAIDS]
                           == nextEvents[:NUM_RAIDS])

            if not updateEmbed and len(self.postedRaids) > 0:
                # if the eventlist has changed and events are already posted
                # we want to post new embeds and delete the old ones
                for raidid in self.postedRaids:
                    delMsgID = self.postedRaids[raidid]
                    print('trying to find and \
                    delete message ID {}'.format(delMsgID))

                    # try to fetch old messages by ID and delete them
                    try:
                        msg = await message.channel.fetch_message(delMsgID)
                        await msg.delete()
                        print('msgId [{}] wurde gelöscht'.format(delMsgID))
                    except Exception as e:
                        print('Das Löschen des Embeds ist nicht gelungen...')
                        print(str(e))
                try:
                    self.postedRaids.clear()
                    print('postedRaids clear')
                except Exception as e:
                    print(str(e))

            for raidid in nextEvents[:NUM_RAIDS]:  # only post NUM_RAIDS embeds
                raidEmbed = backend.raidEventDic[raidid]["embed"].embedContent
                dead_ts = backend.raidEventDic[raidid]["embed"].deadline_ts
                if updateEmbed:
                    try:
                        print('updating embed')
                        msg = await message.channel.fetch_message(
                            self.postedRaids[raidid])
                        await msg.edit(embed=raidEmbed)
                        if dead_ts < int(time.time()):
                            await self.clearReactions(msg)
                    except Exception as e:
                        await message.channel.send('Ich habe versucht, \
                        die Embeds zu updaten. Das ist aber nicht gelungen. \
                        Versuch es bitte noch einmal.')
                        self.clearRaidShow()
                        print('Error: {}'.format(str(e)))
                        print('posted raids und curevents resettet')
                        return
                else:
                    print('posting new embed')
                    msg = await message.channel.send(embed=raidEmbed)
                    self.postedRaids[raidid] = msg.id
                    self.eventDic[msg.id] = raidid
                    if dead_ts > int(time.time()):
                        await self.addStatusReactions(msg)
                        await msg.add_reaction("🔁")
                self.cdTime = int(time.time())
            self.curEvents = nextEvents
            return

    async def addStatusReactions(self, msg):
        for emoji in reactions:
            await msg.add_reaction(emoji)
        return

    async def clearReactions(self, msg):
        for reaction in msg.reactions:
            await reaction.remove(msg.author)
        return

    async def on_reaction_add(self, reaction, user):
        if (user.name == self.user.name) \
                or (reaction.message.id not in self.eventDic):
            return
        print("reaction von {} registriert".format(user.name))
        if not isinstance(reaction.message.channel, discord.DMChannel):
            await reaction.remove(user)
        if reaction.emoji == "🔁"\
                and (int(time.time()) - self.cdTime) > self.refreshCooldown:
            self.cdTime = int(time.time())
            await self.postRaids(reaction.message)
        elif reaction.emoji in reactions:
            try:
                print('trying to signup {} ({})'.format(user.name, user.id))
                await self.signupByReaction(reaction, user)
            except Exception as inst:
                print(type(inst))    # the exception instance
                print(inst.args)     # arguments stored in .args
                print(inst)
                await user.send("Das hat leider nicht geklappt.\n\
                Du hast mir vermutlich deinen Token noch nicht verraten. \
                Um das zu ändern tippe `!cddt help setup`")
        else:
            return

    async def next(self, author, channel, args):
        """__**next**__
Diese Funktion zeigt dir die nächsten Raidevents in einer kompakten \
Darstellung an und ermöglicht dir eine direkte Rückmeldung.
"""
        self.authorized(author)
        try:
            async with channel.typing():
                event_embed = discord.Embed(
                    title="Kommende Raids",
                    description="Bitte an- oder abmelden. :partying_face:"
                )
                await channel.send(embed=event_embed)
                r = await backend.getData(
                    self.registered_users[author.id]['token'],
                    "nextevents")
                if int(r['status']) == 1:
                    nextEvents = r
                    for event in nextEvents['events']:
                        eventid = int(nextEvents['events'][event]['eventid'])
                        eventtitle = nextEvents['events'][event]['title']
                        raid_embed = discord.Embed(
                            title=eventtitle,
                            description="Datum/Zeit: {}\nDein aktueller Status \
                            ist: {}".format(backend.timeToStr(
                                nextEvents['events'][event]['start']),
                                status_options[int(
                                    nextEvents['events'][event]['user_status']
                                )])
                        )
                        event_msg = await channel.send(embed=raid_embed)
                        self.eventDic[event_msg.id] = eventid
                        await self.addStatusReactions(event_msg)
                        if eventid not in backend.raidEventDic:
                            await backend.makeRaidEvents([eventid])
                elif int(r['status']) == 0:
                    await channel.send(embed=discord.Embed(
                        title='Das ging schief :/',
                        description="Fehler: {}".format(str(r['error']))
                    ))
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)
            await channel.send("Aus irgendeinem Grund, kann ich dir gerade "
                               "keine kommenden Raids zeigen. Sorry.")

    async def help(self, author, channel, args):
        if args == [] or args is None:
            await channel.send("""
```asciidoc
Verfügbare Befehle:
----------------------
[Tokeneinrichtung]
- !cddt setup <TOKEN>

[Kommende Raids]
- !cddt next

[1-Klick-Anmeldung]
- !cddt oneclick

Mehr Hilfe zu den Befehlen mit: !cddt help <BEFEHL>
```
            """)
        else:
            try:
                doc = getattr(self, args[0]).__doc__
                await channel.send(doc)
            except Exception as e:
                print(e)
                await channel.send("Dafür fehlt mir leider der Hilfetext")

    async def setup(self, author, channel, args):
        """__**Einrichtung des EQDKP Tokens**__
Um die Funktionen des Discord Bots zu nutzen musst du auf der Webseite
https://cddt-wow.de registriert und freigeschaltet sein.

Navigiere zu den `Registrierungs-Details`, indem du auf der Webseite oben links auf deinen
Benutzernamen klickst und dann dem Link zu `Einstellungen` folgst. Alternativ nutze diesen Link
    https://cddt-wow.de/index.php/Settings.html?s=.

Dein Token findest du innerhalb der `Registrierungs-Details` unter `Private Schlüssel`
als `Privater API-Schlüssel`. Du kannst rechts auf `**********` klicken um es dir
anzeigen zu lassen. Kopiere es um dann den `setup`-Befehl mit deinem Token auszuführen.

`!cddt setup 12345ab34dc...34255612313`

Benutze den `setup`-Befehl nur in Direktnachrichten mit dem Bot.
und kann sich unter deinem Namen für Raids anmelden. Sollte dein Token einmal in fremde Hände
gelangen, kannst du auf der Webseite, dort wo du auch dein Token gefunden hast, neue Schlüssel generieren
und den `setup`-Befehl erneut ausführen.
        """

        if not isinstance(channel, discord.DMChannel):
            await channel.send("Bitte mach das in einem privaten Chat mit mir!")
            return
        if len(args) < 1:
            await channel.send("Da war leider kein Token dabei.")
            return
        if author.id in self.registered_users:
            await channel.send("Dein Token wird aktualisiert.")
            self.registered_users[author.id]['token'] = args[0]
        else:
            await channel.send("Dein Token wird hinzugefügt.")
            self.registered_users[author.id] = {'token': args[0]}
            self.registered_users[author.id]['username'] = author.name
        await self.dumpPickle()
        return

    async def dumpPickle(self):
        try:
            with open('users.pkl', 'wb') as f:
                pickle.dump(self.registered_users, f)
        except Exception as e:
            print(e)
        return

    async def register_OneClick(self, msg, user, char_id, char_name):
        answer = await self.selection_helper("Möchtest du in Zukunft \
        die 1-Klick-Anmeldung nutzen?", ["Ja", "Nein"], user, msg.channel)
        if answer == 1:
            try:
                self.registered_users[user.id]['oneclick'] = 1
                self.registered_users[user.id]['char_name'] = char_name
                self.registered_users[user.id]['char_id'] = char_id
                await self.dumpPickle()
            except Exception as e:
                print(e)
                await msg.channel.send("Da ging was schief.")
                return
            success_embed = discord.Embed(
                title="1-Klick-Anmeldung startklar",
                description="Das war ein voller Erfolg. In Zukunft wirst du \
                direkt beim Klick auf die Reaktion mit **{}** entsprechend \
                angemeldet.\n Mit `!cddt oneclick` kannst Du das \
                ändern".format(char_name)
            )
            await msg.channel.send(embed=success_embed)
        return

    async def oneclick(self, author, channel, args):
        """__**Die 1-Klick-Anmeldung**__
Zur Einrichtung der 1-Klick-Anmeldung ist es notwendig, dass Du die reguläre
Anmeldeprozedur einmal durchlaufen hast.
Am Ende der Anmeldung wirst du gefragt,
ob du die 1-Klick-Anmeldung freischalten möchtest. \n
Zum ein- und ausschalten oder resetten der Anmeldung tippe:
`!cddt oneclick`
        """
        if 'oneclick' not in self.registered_users[author.id]:
            await channel.send("Die 1-Klick-Anmeldung ist für dich leider noch \
             nicht konfiguriert.\nBitte durchlaufe einmal den regulären \
             Anmeldeprozess mit mir, indem du auf eine Reaktion unter \
             dem Raidevent klickst."
                               )
            return
        else:
            oneclick_status = self.registered_users[author.id]['oneclick']
            text = {0: "ausgeschaltet", 1: "eingeschaltet", 2: "gelöscht"}
            answer = await self.selection_helper("Die 1-Klick-Anmeldung ist \
            aktuell **{}**. Möchtest du das ändern?".format(
                text[oneclick_status]),
                ["Ja", "Nein", "Reset"],
                author,
                channel)
            if answer == 1 and oneclick_status == 0:
                new_status = 1
                self.registered_users[author.id]['oneclick'] = new_status
            elif answer == 1 and oneclick_status == 1:
                new_status = 0
                self.registered_users[author.id]['oneclick'] = new_status
            elif answer == 3:
                del self.registered_users[author.id]['oneclick']
                new_status = 2
            else:
                await channel.send("Die 1-Klick-Anmeldung bleibt \
                **{}**".format(text[oneclick_status]))
                return
            try:
                await self.dumpPickle()
                await channel.send("Die 1-Klick-Anmeldung wurde \
                **{}**".format(text[new_status]))
                return
            except Exception as e:
                print(e)
                await channel.send("Da ging was schief.")
                return

    async def selection_helper(self, prompt, list, author, channel):
        def check(message):
            return message.author == author and message.channel == channel

        select_embed = discord.Embed(title=prompt)
        select_embed.set_footer(
            text="Bitte mit der Nummer deiner Auswahl antworten.")
        for i in range(len(list)):
            select_embed.add_field(name=str(i + 1), value=list[i])
        await channel.send(embed=select_embed)
        msg = await self.wait_for('message', check=check)
        if int(msg.content) - 1 in range(len(list)):
            return int(msg.content)
        else:
            raise ValueError('Out of range')

    async def note_helper(self, author, channel):
        def check(message):
            return message.author == author and message.channel == channel

        await channel.send("Wie lautet deine Notiz?")
        msg = await self.wait_for('message', check=check)
        if len(msg.content) > 0:
            return str(msg.content)
        else:
            print('Fehler in der Notizabfrage: Notiz zu kurz')

    async def signupByReaction(self, reaction, user):
        self.authorized(user)
        raidID = self.eventDic[reaction.message.id]
        raidevent = backend.raidEventDic[raidID]
        note = ""
        skip_signup = False

        print('Anmeldevorgang für {} von {} begonnen'.format(
            raidevent['title'], user.name))

        # wenn für oneclick angemeldet den ganzen Kram überspringen.
        if 'oneclick' in self.registered_users[user.id]:
            if self.registered_users[user.id]['oneclick'] == 1:
                msg = await user.send("1-Klick-Anmeldung läuft")
                char_id = self.registered_users[user.id]['char_id']
                skip_signup = True
                print('skipping signup questions...')
        if not skip_signup:
            msg = await user.send("Hey {} :wave:".format(user.name))
            try:
                print('start regular signup process')
                answer = await self.selection_helper("Du willst Dich für \
                den Raid __**{}**__ **{}**?".format(
                    raidevent['title'],
                    reactDict[reaction.emoji]),
                    ["Ja", "Nein"], user,
                    msg.channel)
                if answer == 1:
                    try:
                        char_options = []
                        char_ids = []
                        chars = await backend.getData(
                            self.registered_users[user.id]['token'],
                            "chars")
                        if chars['chars'] is None:
                            await msg.channel.send("Bitte lege zuerst einen \
                            Charakter auf der Homepage an.")
                            return
                        for char in chars['chars']:
                            print(char)
                            char_options.append(chars['chars'][char]['name'])
                            char_ids.append(chars['chars'][char]['id'])
                        if len(char_options) > 1:
                            charidx = await self.selection_helper(
                                "Welcher Charakter?",
                                char_options,
                                user,
                                msg.channel) - 1
                        else:
                            charidx = 0
                        notiz = await self.selection_helper("Möchtest du deiner \
                        Anmeldung eine Notiz hinzufügen?", ["Ja", "Nein"],
                                                            user, msg.channel)
                        print("antwort auf notizfrage: {}".format(notiz))
                        if notiz == 1:
                            note = await self.note_helper(user, msg.channel)
                            print("eingegebene notiz: {}".format(note))
                        char_id = char_ids[charidx]
                    except Exception as e:
                        print(e)
                        await msg.channel.send("Bei der Charakterauswahl ist \
                        ein Fehler aufgetreten.\nVermutlich ist dein Token \
                        falsch. `!cddt help setup` für weitere Instruktionen.")
                        return
                else:
                    await msg.channel.send("Abgebrochen")
                    return
            except Exception as e:
                print(e)
                await msg.channel.send("Eine seltsame Auswahl, \
                ich breche den Vorgang ab.")
                return
            await msg.channel.send("Dein Anmeldestatus wird aktualisiert.")
        r = await backend.raidSignup(self.registered_users[user.id]['token'],
                                     raidID, char_id,
                                     reactStatus[reaction.emoji], note)
        print("response: {}".format(r))
        try:
            if r['status'] == 1:
                success_embed = discord.Embed(
                    title="Alles klar!",
                    description="Dein Status für **{}**\n{} wurde \
                    aktualisiert.\n **Status:** {}\n**Notiz:** {}".format(
                        raidevent['title'], raidevent['start'],
                        reaction.emoji, note)
                )
                success_embed.set_thumbnail(url=raidevent['iconURL'])
                await msg.channel.send(embed=success_embed)
                # Ein Klick registrierung anbieten
                if 'oneclick' not in self.registered_users[user.id]:
                    await self.register_OneClick(msg,
                                                 user,
                                                 char_ids[charidx],
                                                 char_options[charidx])
            else:
                if r['error'] == 'required data missing' and r['info'] == 'roleid':
                    await msg.channel.send(embed=discord.Embed(
                        title="Standardrolle setzen!",
                        url="https://cddt-wow.de/index.php/MyCharacters/?s=",
                        description="Du hast keine Standardrolle für deinen \
                        gewählten Charakter gesetzt. Bitte klicke oben auf den \
                        Link um dies nachzuholen."
                    ))
                    return
                elif r['error'] == 'access denied':
                    await msg.channel.send(embed=discord.Embed(
                        title="Token ungültig!",
                        description="Mit __!cddt help setup__ erfährst du, \
                        wie du den Token richtig installierst."
                    ))
                    return
                elif r['error'] == 'statuschange not allowed':
                    await msg.channel.send(embed=discord.Embed(
                        title="Zu spät!",
                        description="Die Raidanmeldung ist bereits geschlossen. \
                        Bitte wende dich an die Raidleitung oder \
                        deinen Klassenleiter.\nAlternativ kannst du auch auf \
                        der Webseite ein Kommentar hinterlassen."
                    ))
                    return
                print(r)
                await msg.channel.send("Das hat leider nicht geklappt.")
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)


client = Guffelbot()

client.run(cf.guffeltoken1)  # 1: test #2: live
