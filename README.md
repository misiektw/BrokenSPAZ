#    Broken SPAZ

##   TorqueScript Engine v. 1.7.5 DSO v.41 Decompiler (works with  Space Pirates and Zobies SPAZ)

I was annoyed by debt mechanic, and devs said they will not change it. Well, I had to change it by myself.
Unfortunately all decompilers I found failed to decompile reserchScreen.cs.dso, which has this mechanic.
So I changed Scarface scripts to work with SPAZ. But after getting it to work I found out that I didn't need to decompile researchScreen just exec.cs.dso, and then add custom script to it just with two functions which apparently override default ones.
Mod included in this repo if you want it.

All the source code was written in `python3` and tested in a `Manjaro 20.2` machine with a `python3.9` interpreter.

##   Links

[Broken Face](https://github.com/sulzbals/BrokenFace) - This is project I forked from.

[Broken Synapse](https://blog.kwiatkowski.fr/?q=en/broken-synapse) ([Github](https://github.com/JusticeRage/BrokenSynapse)) - This project was huge help, as it works with v.41 dso. However it has missing OP's.

[Torque2D source code](https://github.com/GarageGames/Torque2D) - Closest source to 1.7.5 is 2.0. But seems to be few changes.

[Torque2D cs syntax](http://docs.garagegames.com/tgb/official/content/documentation/Scripting/Syntax.html)


##   Usage

Symlink to main script can be found in `bin/dso4spaz`.


```
usage: dso4spaz [-h] [--debug] [--compare] FILE_NAME [FILE_NAME ...]

positional arguments:
  FILE_NAME     name of the file to be decompiled

optional arguments:
  -h, --help    show this help message and exit
  --debug       set logging level to DEBUG
  --compare		simple compare of decoded files. Helps to check if recompiled script is close to original.
```

##	Code
Everything that is written in Broken Face readme pretty much applies here. Of course there are changes because Scarface uses older version of DSO.
I added compare functionality do dso.py to help with quickly checking if decompiled and then recompiled script is close to original.


##   Known Issues

From original, I didn't fix this:

* `Boolean ambiguity`: In composed boolean conditions, it is a good practice to use parenthesis to indicate the order of the operations (e.g. `a && b > c` can be `(a && b) > c` or `a && (b > c)`). There is nothing implemented to disambiguate conditions like this.

In this version::

* Seems like there's a bug in Torque2D 1.7.5 and all numbers in function calls and objects are compiled in as strings. And there seem no way to recognize if originally that was a number or number as string. However, recompiled script are binary perfect with originals, so seems theres no difference.
* Seems that ++/-- operators are compiled in exactly the same as "$var = $var++". I chose to leave just var++/var-- because it sometimes used as array subscripts.
* Concatenation with @ seems to be ambigious. I added 2 edge cases 
* Of course "for" loops are decompiled as "while".