This is No Respec Cost mod for SPAZ. Working with v.1.605 Linux version from HumbleBundle (probably with GoG/Steam too).

Installation:

1. Decompile exec.cs.dso (I dont want to include file here, because possible copyright issues).

python dso2cs.py exec.cs.dso

2. Rename file from exec.cs.dso.cs to exec.cs. 
3. Add one line to it (just after last gameScripts entry: "loadingExec("./gameScripts/arenaManager.cs");"):

loadingExec("./gameScripts/xxx_NoRespec.cs");

4. Put exec.cs into any mod directory you're using, or straight into "game" folder in SPAZ installation.

5. Put xxx_NoRespec.cs file into "gameScripts" folder. Again in any mod, or directly into SPAZ.