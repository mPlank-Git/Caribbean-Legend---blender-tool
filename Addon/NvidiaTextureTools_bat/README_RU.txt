DDS Texture Converter BAT Tools
===============================

Набор BAT-файлов для быстрой конвертации текстур в DDS через NVIDIA Texture Tools Exporter (https://developer.nvidia.com/texture-tools-exporter).

Используются три варианта конвертации:

1. BC1 / DXT1
   Для обычных color / albedo / diffuse текстур без альфы.

2. BC3 / DXT5
   Для текстур с альфой, normal map и RMA.

3. Auto Combine
   Автоматическая конвертация по постфиксам:
   *_nom.* -> BC3 / DXT5
   *_rma.* -> BC3 / DXT5
   все остальные текстуры -> BC1 / DXT1


Установка
---------

1. Установить NVIDIA Texture Tools Exporter.

2. Найти папку, где лежит файл:

   nvtt_export.exe

   Обычно это:

   C:\Program Files\NVIDIA Corporation\NVIDIA Texture Tools\

   или папка, куда была распакована standalone-версия NVIDIA Texture Tools.

3. Поместить BAT-файлы рядом с nvtt_export.exe.

Пример структуры:

NVIDIA Texture Tools
| nvtt_export.exe
| BC1_DXT1.bat
| BC3_DXT5.bat
| BC1_BC3_combine.bat
|
|-- output_bc1
|-- output_bc3
|-- output_combine


Использование
-------------

BAT-файлы работают через drag & drop.

Нужно выделить одну или несколько текстур и перетащить их прямо на нужный BAT-файл.

Если просто запустить BAT двойным кликом, он не будет знать, какие файлы нужно конвертировать.


BC1 / DXT1
----------

Используется для обычных текстур без альфы:

diffuse.png
albedo.tga
wood_wall.jpg

Перетащить нужные файлы на:

BC1_DXT1.bat

Результат будет сохранён в папку:

output_bc1


BC3 / DXT5
----------

Используется для текстур с альфой, normal map или специальных карт:

glass_alpha.png
stone_nom.tga
metal_rma.png

Перетащить нужные файлы на:

BC3_DXT5.bat

Результат будет сохранён в папку:

output_bc3


Auto Combine
------------

Автоматический BAT-файл сам выбирает формат по имени файла:

wall.png     -> BC1 / DXT1
wall_nom.png -> BC3 / DXT5
wall_rma.png -> BC3 / DXT5

Перетащить пачку файлов на:

BC1_BC3_combine.bat

Результат будет сохранён в папку:

output_combine


Правила именования для Auto Combine
-----------------------------------

Для автоматической сортировки используются постфиксы в конце имени файла:

_nom
_rma

Примеры правильных имён:

wood_planks.png
wood_planks_nom.png
wood_planks_rma.png

Результат:

wood_planks.dds     -> BC1 / DXT1
wood_planks_nom.dds -> BC3 / DXT5
wood_planks_rma.dds -> BC3 / DXT5


Где менять папку экспорта
-------------------------

В каждом BAT-файле есть строка OUTPUT.

Для BC1:

set "OUTPUT=%~dp0output_bc1"

Для BC3:

set "OUTPUT=%~dp0output_bc3"

Для Auto Combine:

set "OUTPUT=%~dp0output_combine"

Чтобы изменить папку экспорта, нужно поменять значение после OUTPUT=.

Например, было:

set "OUTPUT=%~dp0output_combine"

Можно заменить на:

set "OUTPUT=D:\Converted_DDS"

После этого DDS-файлы будут сохраняться в:

D:\Converted_DDS


Где менять путь к NVIDIA Texture Tools
--------------------------------------

По умолчанию BAT-файлы ищут nvtt_export.exe рядом с собой:

set "NVTT=%~dp0nvtt_export.exe"

Если BAT-файлы лежат не в папке NVIDIA Texture Tools, можно указать путь вручную:

set "NVTT=C:\Program Files\NVIDIA Corporation\NVIDIA Texture Tools\nvtt_export.exe"


Поддерживаемые входные форматы
------------------------------

Можно использовать:

png
tga
tif
tiff
jpg
jpeg
bmp
psd

На выходе создаются файлы:

.dds


Рекомендации по форматам
------------------------

BC1 / DXT1 использовать для:

albedo
diffuse
base color
обычных color-текстур без альфы

BC3 / DXT5 использовать для:

текстур с альфой
normal map с постфиксом _nom
RMA-текстур с постфиксом _rma

Auto Combine использовать, если нужно закинуть сразу много текстур и автоматически выбрать формат по постфиксам.


Важно
-----

Для работы BAT-файлы должны иметь доступ к nvtt_export.exe.

Самый простой вариант:
положить BAT-файлы прямо рядом с nvtt_export.exe.

Если путь другой, нужно изменить строку NVTT внутри BAT-файла.
