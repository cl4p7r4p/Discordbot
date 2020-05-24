import aiohttp
import asyncio
# import json
import time
import discord
import pickle
from backend import *
import config as cf

reactions = ["✅", "🚫", "💤","🔁" ]
reactDict = {
    "✅": "anmelden", #status 1
    "🚫": "abmelden", #status 2
    "💤": "auf die Bank setzen" #status 3,
}
reactStatus = {
    "✅": 1, #status 1
    "🚫": 2, #status 2
    "💤": 3 #status 3
}
class Unauthorized(Exception):
    pass

class Guffelbot(discord.Client):
    def authorized(self, author):
        if not author.id in self.registered_users:
            raise Unauthorized()


    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        try:
            with open('users.pkl', 'rb') as f:
                self.registered_users = pickle.load(f)
        except:
            self.registered_users = {}

    async def on_ready(self):
        print('Logged on as', self.user)
        try:
            await preperation()
            print("Vorbereitung abgeschlossen")
        except:
            print("das hat nicht geklappt")

    async def deletemsg(self, message):
        await message.channel.purge(limit=1)

    def is_me(self,m):
        return m.author == client.user

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.content.startswith('!cddt'):
            commands = message.content.split(' ')
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
                await self.deletemsg(message)
                await client.close()
            else:
                await message.channel.send("Du bist nicht mein Meister :poop:")
        if message.content == 'clean up':
            if message.author.name == "hairypotta":
                await message.channel.purge(limit=50, check=self.is_me)
            else:
                await message.channel.send("Du bist nicht mein Meister :poop:")

        if message.content == 'show raids':
            await self.deletemsg(message)
            await self.postRaids(message)

    async def postRaids(self,message):
        for ev in raidEvents:
            if ev.isPosted and (int(time.time())-ev.creationTime)<120:
                # await message.channel.send("noch zu jung")
                pass
            elif ev.isPosted and (int(time.time())-ev.creationTime)>120:
                # await message.channel.send("Anzeige wird aktualisiert")
                msg = await message.channel.fetch_message(ev.messageID)
                await ev.update()
                await msg.edit(embed=ev.embed.embedContent)

            else:
                msg = await message.channel.send(embed=ev.embed.embedContent)
                ev.isPosted = True
                ev.messageID = msg.id
                ev.channelID = msg.channel.id
                if ev.deadline_ts>int(time.time()):
                    for emoji in reactions:
                        await msg.add_reaction(emoji)

    async def on_reaction_add(self, reaction, user):
        print("reaction von {} registriert".format(user.name))
        if  reaction.count < 2:
            return
        elif reaction.emoji not in reactions:
            await reaction.remove(user)
        elif reaction.emoji=="🔁":
            await reaction.remove(user)
            await self.postRaids(reaction.message)
        else:
            raid = findEventByMsgId(reaction.message.id)
            try:
                await reaction.remove(user)
                await self.signupByReaction(reaction, user, raid)
            except:
                await user.send("Du hast leider keine gültige Verbindung zur Raidanmeldung. \nUm das zu ändern, folge den Instruktionen die du von mir mit den Zauberworten:\n **!cddt help setup** \n erhältst.")


    async def next(self, author, channel, args):
        event_embed = discord.Embed(title="Kommende Raids")
        for raid in raidEvents:
            event_embed.add_field(
                name=raid.title,
                value="{0} von {1} Uhr bis {2} Uhr".format(
                    '.'.join(reversed(raid.starttime.split(' ')[0].split('-'))),
                    raid.starttime.split(' ')[1],
                    raid.starttime.split(' ')[1],
                ),
                inline=False)
        await channel.send(embed=event_embed)

    async def help(self, author, channel, args):
        if args == [] or args == None:
            await channel.send("""
```asciidoc
Verfügbare Befehle:
----------------------
[Tokeneinrichtung]
- !cddt setup <TOKEN>

[Kommende Raids]
- !cddt next

[Raidstatus]
- !cddt status

Mehr Hilfe zu den Befehlen mit: !cddt help <BEFEHL>
```
            """)
        else:
            try:
                doc = getattr(self, args[0]).__doc__
                await channel.send(doc)
            except Exception as e:
                print(e)
                await channel.send("Dafür fehlt mir leider der Hilfetext, informiere Theo")

    async def setup(self, author, channel, args):
        """__**Einrichtung des EQDKP Tokens**__
    Um die Funktionen des Discord Bots zu nutzen musst du auf der Webseite \
https://cddt-wow.de registriert und freigeschaltet sein.

    Navigiere zu den `Registrierungs-Details`, indem du auf der Webseite oben links auf deinen \
Benutzernamen klickst und dann dem Link zu `Einstellungen` folgst. Alternativ nutze diesen Link \
    https://cddt-wow.de/index.php/Settings.html?s=.

    Dein Token findest du innerhalb der `Registrierungs-Details` unter `Private Schlüssel` \
als `Privater API-Schlüssel`. Du kannst rechts auf `**********` klicken um es dir \
anzeigen zu lassen. Kopiere es um dann den `setup`-Befehl mit deinem Token auszuführen.

`!cddt setup 12345ab34dc...34255612313`

    Benutze den `setup`-Befehl nur in Direktnachrichten mit dem Bot. Sonst hat jeder dein Token \
und kann sich unter deinem Namen für Raids anmelden. Sollte dein Token einmal in fremde Hände \
gelangen, kannst du auf der Webseite, dort wo du auch dein Token gefunden hast, neue Schlüssel generieren \
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
            self.registered_users[author.id] = {'token':args[0]}
        await self.dumpPickle()
        return

    async def dumpPickle(self):
        try:
            with open('users.pkl', 'wb') as f:
                pickle.dump(self.registered_users, f)
        except Exception as e:
            print(e)
            await channel.send("Beim der permanenten Speicherung von Daten ist ein Fehler aufgetreten")
        return

    async def register_OneClick(self, msg, user, char_id, char_name):
        answer = await self.selection_helper("Möchtest du in Zukunft die 1-Klick-Anmeldung nutzen?", ["Ja", "Nein"], user, msg.channel)
        if answer==1:
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
                description="Das war ein voller Erfolg. In Zukunft wirst du direkt beim Klick auf die Reaktion mit **{}** entsprechend angemeldet.".format(char_name)
            )
            await msg.channel.send(embed=success_embed)
        return

    async def selection_helper(self, prompt, list, author, channel):
        def check(message):
            return message.author == author and message.channel == channel

        select_embed = discord.Embed(title=prompt)
        select_embed.set_footer(text="Bitte mit der Nummer deiner Auswahl antworten.")
        for i in range(len(list)):
            select_embed.add_field(name=str(i+1), value=list[i])
        await channel.send(embed=select_embed)
        msg = await self.wait_for('message', check=check)
        if int(msg.content)-1 in range(len(list)):
            return int(msg.content)
        else:
            raise ValueError('Out of range')

    async def note_helper(self, author, channel):
        def check(message):
            return message.author == author and message.channel == channel

        await channel.send("Wie lautet deine Notiz?")
        msg = await self.wait_for('message', check=check)
        if len(msg.content)>0:
            return str(msg.content)
        else:
            print('Fehler in der Notizabfrage: Notiz zu kurz')

    async def signupByReaction(self, reaction, user, raidevent):
        self.authorized(user)
        status_options = [":sparkle: Bestätigt", ":white_check_mark: Angemeldet", ":no_entry_sign: Abgemeldet", ":zzz: Ersatzbank"]
        note = "powered by guffelbot"

        ## wenn für oneclick angemeldet den ganzen kram überspringen.
        if 'oneclick' in self.registered_users[user.id]:
            if self.registered_users[user.id]['oneclick']==1:
                msg = await user.send("1-Klick-Anmeldung läuft")
                char_id = self.registered_users[user.id]['char_id']
                pass
        else:
            msg = await user.send("Hey {}.".format(user.name))
            try:
                answer = await self.selection_helper("Du willst Dich für den Raid __**{}**__ **{}**?".format(raidevent.title,reactDict[reaction.emoji]), ["Ja", "Nein"], user, msg.channel)
                if answer == 1:
                    try:
                        char_options = []
                        char_ids = []
                        chars = await getData(self.registered_users[user.id]['token'],"chars")
                        for char in chars['chars']:
                            print(char)
                            char_options.append(chars['chars'][char]['name'])
                            char_ids.append(chars['chars'][char]['id'])
                        if len(char_options) > 1:
                            charidx = await self.selection_helper("Welcher Charakter?", char_options, user, msg.channel)-1
                        else:
                            charidx = 0
                        notiz = await self.selection_helper("Möchtest du deiner Anmeldung eine Notiz hinzufügen?", ["Ja", "Nein"], user, msg.channel)
                        print("antwort auf notizfrage: {}".format(notiz))
                        if notiz == 1:
                            note = await self.note_helper(user, msg.channel)
                            print("eingegebene notiz: {}".format(note))
                        char_id = char_ids[charidx]
                    except Exception as e:
                        print(e)
                        await msg.channel.send("Eine seltsame Auswahl, ich breche den Vorgang ab.")
                        return
                else:
                    await msg.channel.send("Abgebrochen")
                    return
            except Exception as e:
                print(e)
                await msg.channel.send("Eine seltsame Auswahl, ich breche den Vorgang ab.")
                return
            await msg.channel.send("Dein Anmeldestatus wird aktualisiert.")
        r =  await raidevent.signup(self.registered_users[user.id]['token'], char_id, reactStatus[reaction.emoji],note)
        print("response: {}".format(r))
        print("type: {}".format(type(r)))
        try:
            if r['status'] == 1:
                success_embed = discord.Embed(
                    title="Alles klar!",
                    description="Dein Status für **{}** am {} wurde aktualisiert.\n **Status:** {}\n**Notiz:** {}".format(raidevent.title,raidevent.starttime,reaction.emoji,note)
                )
                success_embed.set_thumbnail(url=raidevent.iconURL)
                await msg.channel.send(embed=success_embed)
                ## Ein Klick registrierung anbieten
                if not 'oneclick' in self.registered_users[user.id]:
                    await self.register_OneClick(msg,user,char_ids[charidx],char_options[charidx])
            else:
                if r['error'] == 'required data missing' and r['info'] == 'roleid':
                    await msg.channel.send(embed=discord.Embed(
                        title="Standardrolle setzen!",
                        url="https://cddt-wow.de/index.php/MyCharacters/?s=",
                        description="Du hast keine Standardrolle für deinen gewählten Charakter gesetzt. Bitte klicke oben auf den Link um dies nachzuholen."
                    ))
                    return
                print(r)
                await msg.channel.send("Das hat nicht geklappt.")
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)


client = Guffelbot()

client.run(cf.guffeltoken1) #1: test #2: live
