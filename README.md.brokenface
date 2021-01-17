#    Broken Face

##   TorqueScript Decompiler for `Scarface` based on `Broken Synapse`

This is a decompiler for the `TorqueScript` scripts used in the game `Scarface - The World is Yours`. Even though the `Torque Game Engine` has been [open-sourced](https://github.com/GarageGames/Torque3D), this game in particular seems to run a modified version of it, therefore the scripts were compiled into a slightly different format, which is not recognized by the available open `TorqueScript` decompilers.

By reverse-engineering this variant of the `C Script` file format I was able to to write this decompiler that had a 100% success rate for the scripts that I tested. That is, all the files with `.cso` and `.dso` extensions located inside the `scriptc` folder, which can be obtained by decompressing the `cement.rcf` file found in the installation directory of the game.

All the source code was written in `python3` and tested in a `Debian bullseye` machine with a `python3.8.2` interpreter.

##   Important Links

[Scarface Remastered Project](https://discord.gg/ZRGeNsu) - This Discord server is from a group of people remastering the `Scarface` game. This decompiler is my contribution to the project, and hopefully it will help modding the game.

[Broken Synapse](https://blog.kwiatkowski.fr/?q=en/broken-synapse) ([Github](https://github.com/JusticeRage/BrokenSynapse)) - The project `Broken Face` was forked from. The code itself was written from scratch, since I went for a more modular, object-oriented approach, and some file format and decoding specificities are also different, but both the linked article and the code were very helpful resources during the development of `Broken Face`.

[Torque3D source code](https://github.com/GarageGames/Torque3D) The concepts of some instructions are not very easy to understand just by their names and the few lines of `python` code dedicated to them in `Broken Synapse`. Therefore, it was good to take a look on `Torque`'s source code sometimes to have some insight of how the virtual machine works.

[Meth0d's article on Scarface scripts](https://forum.mixmods.com.br/f120-ajuda/t3376-scarface-the-world-is-yours-cso-scripts) (in portuguese) - This article was really useful for implementing the first steps of the decompiler. Basically the whole `parsing` stage described in the `Flow` section below was reverse-engineered by `Meth0d` and documented there.

##   Usage

The main script can be found in `bin/decompile`.


```
usage: decompile [-h] [--parse-only] [--debug] FILE_NAME [FILE_NAME ...]

positional arguments:
  FILE_NAME     name of the file to be decompiled

optional arguments:
  -h, --help    show this help message and exit
  --parse-only  only parse the file and dump the structures
  --debug       set logging level to DEBUG
```

##   Flow

While `Broken Synapse` is divided in a `parsing` and a `decompilation` stages, I opted for a three-stage flow scheme. The first stage is the same: `Parsing` the script file fields. Then, instead of a single stage for translating the `Bytecode` directly into text, I implemented a `decoding` stage that translates the `Bytecode` into an intermediary structure and a `formatting` stage that reads this structure and pretty-prints the source code.

This intermediary structure is basically a tree of objects representing `TorqueScript` syntax components (e.g. function declarations, calls, `while` loops, `if` and `else` statements, etc.). The aim is to reduce complexity, as a complex process is now split into a simpler stage for retrieving all elements of the script and another really simple stage for formatting them as text.

###  Parsing

The parsing stage consists of reading the script file and dumping its substructures into objects like `lists` and `dictionaries`. Those substructures are parsed from the fields listed below, in order:

* `Script Version` (4-bytes long, little-endian) - Should be the version of `Torque` being used, but it seems to be always set to `1`.
* `Global String Table Size` (4-bytes long, little-endian) - Size, in bytes, of the `Global String Table` to be parsed next.
* `Global String Table` (consecutive null-terminated strings) - List of strings used by the script in the global scope.
* `Global Float Table Size` (4-bytes long, little-endian) - Size, in entries, of the `Global Float Table` to be parsed next.
* `Global Float Table` (4-bytes long, little-endian (each - single precision)) - List of floats used by the script in the global scope.
* `Function String Table Size` (4-bytes long, little-endian) - Size, in bytes, of the `Function String Table` to be parsed next.
* `Function String Table` (consecutive null-terminated strings) - List of strings used by the script in the local scopes of the functions.
* `Function Float Table Size` (4-bytes long, little-endian) - Size, in entries, of the `Function Float Table` to be parsed next.
* `Function Float Table` (4-bytes long, little-endian (each - single precision)) - List of floats used by the script in the local scopes of the functions.
* `Bytecode Size` (4-bytes long, little-endian) - Size, in "codes", of the `Bytecode` to be parsed next.
* `Bytecode` - Stream of "codes" that describe the instructions the script consists of. This structure is indexed both by byte and by "code". Each "code" can be either:
  - 1-byte long
  - 3-bytes long (effectively 2-bytes long, little-endian) - The byte `0xff` is reserved to indicate that a code is 2-bytes long. The next two bytes after an occurrence of this control code compose a single code (e.g. if the `Bytecode` is `0x00ff112233`, the first code is `0x00`, the second is `0x1122` and the third is `0x33` (code indexing)).
* `Ident Table Size` (4-bytes long, little-endian) - Size, in entries, of the `Ident Table` to be parsed next.
* `Ident Table` - Table of string references to be patched into the `Bytecode`. Each entry consists of the following:
  - `Offset` (4-bytes long, little-endian) - Offset of a string in one of the string tables.
  - `Count` (4-bytes long, little-endian) - Number of locations in the `Bytecode` where the current reference (`Offset`) must be written, to be parsed next.
    - `Location` (4-bytes long, little-endian (each)) - Code index of `Bytecode` to write current reference.

#### Patching

For some reason, the `Bytecode` included in the file is not complete "as is". After parsing all the substructures of the file, a further step is needed for patching the string references of the `Ident Table` into the `Bytecode`. This is done by writing the `Offset` field of each entry to the addresses of the `Bytecode` described on their respectives `Location` fields.

###  Decoding

Similarly to `Java`, `TorqueScript` is compiled into a low-level assembly-like `Bytecode`, which has to be interpreted by a virtual machine in order to be run. The decoding stage consists of going through this `Bytecode` instruction by instruction, constructing objects representing the script components and appending them to the tree.

Although `TorqueScript` is a [type-insensitive](http://docs.garagegames.com/torque-3d/reference/syntaxVariables.html) language, internally the engine deals with three data types: Unsigned integer (`uint`), `float` and `string`. Boolean values are often represented either as `uint` or as a single code.

#### Decoding instructions

All instructions consist of an `opcode` identifying the instruction, possibly followed by parameters. Each parameter can be represented either as a single code, or as one of the supported data types. The instruction set consists of 83 `opcodes` ranging from `0` to `85` with a few gaps.

To decode an instruction, the `opcode` is read, then the decoding routine for this `opcode` is called. This routine reads the parameters of the instruction and can update the simulated virtual machine state (stacks, current variable, object and field registers, etc.) and/or append objects to the tree depending on the instruction.

#### Decoding uints

After some reverse engineering, I came to the conclusion that `uints` are always two codes long and packed as big-endian. It is actually really tricky, because this means that an `uint` can be:

* 2-bytes long (big-endian)
* 4-bytes long (effectively 2-bytes long, big-endian) - Sometimes `uints` are encoded e.g. in the format `0x00ff1122`, where `0x1122` is the actual value.
* 6-bytes long (effectively 4-bytes long, big-endian) - Sometimes `uints` are encoded e.g. in the format `0xff1122ff3344`, where `0x11223344` is the actual value (at least I believe it is like this. This pattern can only be found in a couple scripts and the decompilation just worked for them after I tried to decode the patterns like this).

#### Decoding floats

This data type is easier. `floats` are always described in the `float` tables, and are only referenced in the `Bytecode` by offsets of the tables encoded as 2-bytes long big-endian offsets.

#### Decoding strings

Perhaps the trickiest of the three. `strings` are also only referenced in the `Bytecode`, but they can be:

* 2-bytes long (big-endian) - If the string offset was not patched to the location being accessed, it is encoded as big-endian.
* 2-bytes long (little-endian) - If the string offset was patched, it is encoded as little-endian.
* 4-bytes long (effectively 2-bytes long little-endian) - Sometimes the offsets are encoded e.g. in the format `0x00ff1122`, where `0x1122` is the actual offset. I do not know whether or not it is encoded always as little-endian because coincidently the offsets were always patched as well, but this works.

###  Formatting

The third and last stage consists of going through the tree of `Torque` objects and pretty-printing them as text. This resulting text is the decompiled source code.

The tree structure works as follows: Each node represents a line of code. To get the sourcde code, the tree is traversed in [level order](https://www.geeksforgeeks.org/level-order-tree-traversal/). If a node has children pointers, it means that it declares a code block, and its children represent the lines of code inside it. So, for example, the following tree:

```
      function a()
      /     |     \
     /      |      \
  b = c   if (d)   else
         /      \    |
        /        \   |
       e()      f()  g()
```

Is translated into the following source code during formatting:

```
function a()
{
    b = c;
    if (d)
    {
        e();
        f();
    }
    else
    {
        g();
    }
}
```

Refer to the `Architecture` section below for implementation details.

##   Architecture

The project is divided into the submodules listed here. These topics only provide a brief description, as there are comments describing the classes and methods in more detail inside the source code files.

###  util

Here goes utilitary classes and methods that have a more general purpose than only decompiling `TorqueScript`.

#### binary

The `BinaryReading` class is defined here. The functionality is similar to built-in classes of `Java` and `C#`: It encapsulates a `bytes` object, which can be read and processed through methods. Those methods can be used to read specific amounts of bytes and/or decode bytes into specific formats (e.g. `uint16`, `float32`, `string`). All the stream reading control is done internally in the instance, making the interface very simple.

###  core

Here goes specific classes and methods that implement the functionality of this application.

#### dso

Basically everything related to the `parsing` stage is defined here. The classes of the substructures of the file (`StringTable`, `FloatTable`, `Bytecode`, etc.) and also the routines for parsing and patching.

#### codec

Basically everything related to the `decoding` stage. The decoding routines per `opcode`, the dictionary relating these opcodes to its respective routine, the context variables and stacks for simulating the virtual machine state, etc.

#### torque

Finally, everything related to the `formatting` stage. The classes representing the nodes of the tree and also classes representing supported `TorqueScript` operations (`+`, `-`, `*`, etc.). Each one of those classes has `__str__` method override, making it really simple to format them as text. This allows us to easily deal with composed operations, for example, since once you call this method for an operation, it is called as well for the operands recursively.

##   Known Issues

Although I got excellent results with this decompiler, there is a lot of decompiled code to analyse, and a lot of bugs and demands appear as you go deeper. Some issues I am already aware that happen or that could happen are listed below:

* `Boolean ambiguity`: In composed boolean conditions, it is a good practice to use parenthesis to indicate the order of the operations (e.g. `a && b > c` can be `(a && b) > c` or `a && (b > c)`). There is nothing implemented to disambiguate conditions like this.
