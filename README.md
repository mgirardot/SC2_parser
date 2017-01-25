#StarCraft2 Replay Parser

The aim of this project is to create a dataset from StarCraft2 replay files.

##Download replays

Replays are avaliable at the [ggtracker](http://ggtracker.com/matches/) website. To Download them from Windows, I used this command in a power-shell console:
`Invoke-WebRequest http://ggtracker.com/matches/[#REPLAY_NUM]/replay -OutFile #REPLAY_NUM.replay`

Where `#REPLAY_NUM` is the replay number found on [ggtracker](http://ggtracker.com/matches/). Downloads from Unix should work with the `wget` utility.

##Extract Action-list

The [Sc2gears parser](https://github.com/icza/sc2gears) can extract all the actions of the players from the replay files:

`Sc2gears-win.cmd --print-action-list --use-frames #REPLAY_NUM.replay > #REPLAY_NUM.csv`

##Replace spaces

Unfortunately, [Sc2gears parser](https://github.com/icza/sc2gears) do not export action infos in a usable csv format. I removed the spaces at the begining of each lines and replaced the multiple spaces separating each column with a tabulation. I used the `replace_spaces.ps` powershell script to perform the cleaning of the csv files inplace.

##Parsing the data

`python /src/Parser_5min.py [Source files] [Destination File]`


* Source Files: the output of the [Sc2gears parser](https://github.com/icza/sc2gears)
* Destination File: the csv to write

