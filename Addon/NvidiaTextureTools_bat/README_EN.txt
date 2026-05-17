DDS Texture Converter BAT Tools
===============================

A set of BAT files for quick texture conversion to DDS using NVIDIA Texture Tools Exporter (https://developer.nvidia.com/texture-tools-exporter).

There are three conversion options:

1. BC1 / DXT1
   For regular color / albedo / diffuse textures without alpha.

2. BC3 / DXT5
   For textures with alpha, normal maps, and RMA textures.

3. Auto Combine
   Automatic conversion based on file suffixes:
   *_nom.* -> BC3 / DXT5
   *_rma.* -> BC3 / DXT5
   all other textures -> BC1 / DXT1


Installation
------------

1. Install NVIDIA Texture Tools Exporter.

2. Find the folder that contains the file:

   nvtt_export.exe

   Usually it is located here:

   C:\Program Files\NVIDIA Corporation\NVIDIA Texture Tools\

   or in the folder where the standalone version of NVIDIA Texture Tools was unpacked.

3. Place the BAT files next to nvtt_export.exe.

Example folder structure:

NVIDIA Texture Tools
| nvtt_export.exe
| BC1_DXT1.bat
| BC3_DXT5.bat
| BC1_BC3_combine.bat
|
|-- output_bc1
|-- output_bc3
|-- output_combine


Usage
-----

The BAT files work via drag & drop.

Select one or more texture files and drag them directly onto the required BAT file.

If you simply double-click a BAT file, it will not know which files should be converted.


BC1 / DXT1
----------

Use this for regular textures without alpha:

diffuse.png
albedo.tga
wood_wall.jpg

Drag the required files onto:

BC1_DXT1.bat

The result will be saved to:

output_bc1


BC3 / DXT5
----------

Use this for textures with alpha, normal maps, or special maps:

glass_alpha.png
stone_nom.tga
metal_rma.png

Drag the required files onto:

BC3_DXT5.bat

The result will be saved to:

output_bc3


Auto Combine
------------

The automatic BAT file chooses the format based on the file name:

wall.png     -> BC1 / DXT1
wall_nom.png -> BC3 / DXT5
wall_rma.png -> BC3 / DXT5

Drag a batch of files onto:

BC1_BC3_combine.bat

The result will be saved to:

output_combine


Naming Rules for Auto Combine
-----------------------------

Automatic sorting uses suffixes at the end of the file name:

_nom
_rma

Examples of correct file names:

wood_planks.png
wood_planks_nom.png
wood_planks_rma.png

Result:

wood_planks.dds     -> BC1 / DXT1
wood_planks_nom.dds -> BC3 / DXT5
wood_planks_rma.dds -> BC3 / DXT5


Where to Change the Export Folder
---------------------------------

Each BAT file contains an OUTPUT line.

For BC1:

set "OUTPUT=%~dp0output_bc1"

For BC3:

set "OUTPUT=%~dp0output_bc3"

For Auto Combine:

set "OUTPUT=%~dp0output_combine"

To change the export folder, edit the value after OUTPUT=.

For example, this:

set "OUTPUT=%~dp0output_combine"

Can be changed to:

set "OUTPUT=D:\Converted_DDS"

After that, DDS files will be saved to:

D:\Converted_DDS


Where to Change the Path to NVIDIA Texture Tools
------------------------------------------------

By default, the BAT files look for nvtt_export.exe next to themselves:

set "NVTT=%~dp0nvtt_export.exe"

If the BAT files are not located inside the NVIDIA Texture Tools folder, you can set the path manually:

set "NVTT=C:\Program Files\NVIDIA Corporation\NVIDIA Texture Tools\nvtt_export.exe"


Supported Input Formats
-----------------------

You can use:

png
tga
tif
tiff
jpg
jpeg
bmp
psd

The output files will be:

.dds


Format Recommendations
----------------------

Use BC1 / DXT1 for:

albedo
diffuse
base color
regular color textures without alpha

Use BC3 / DXT5 for:

textures with alpha
normal maps with the _nom suffix
RMA textures with the _rma suffix

Use Auto Combine if you need to drop many textures at once and automatically choose the format based on suffixes.


Important
---------

The BAT files must have access to nvtt_export.exe.

The easiest option:
place the BAT files directly next to nvtt_export.exe.

If the path is different, edit the NVTT line inside the BAT file.
