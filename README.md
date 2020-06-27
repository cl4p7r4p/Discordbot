# Discordbot for EQDKP
This bot can be used in combination with an EQDKP Installation.
See https://eqdkp-plus.eu/ for more Information.


## Functions:
- post and update upcoming raidevents with details (e.g. raid-setup, raid-note, setup, ...)
- users can see their raidstatus for the upcoming # raids and change directly (via DM)
- raidlead can remind dc-users to respond to raid (bot crosschecks discord users against website users and sends DM to users)
- users can respond via "one-click" or run "regular" sign-up procedure where they can choose main/twink char and add a note
- users can comment on raidevents

## not implemented yet
- setup routine
- any DKP related stuff
- ...

# Setup
- You need a "config.py" File with your EQDKP API Mastertoken (read-only) and your Bottoken like this:
config.py:
```
BOTTOKEN = NASDJJsdas8128
mastertoken = ashd1231291aeeeff
```

- change server adress in backend.py