# netauto
Management Automation on A Juniper Network

This repository contains Python 3 scripts based on Juniper PyEZ	to manage a network built on Juniper equipment. Scripts are briefed as below:

------------------
1. pm.generator.py

This script generates .csv files to populate these on Patch Manager: 1) faceplate icons on floor map; 2) fixed cables between faceplates and patch panels in comm rooms; 3) patching from patch panel to switch interfaces.

usage: pm.generator.py [-h] [-x {icon,fixed,patch}] [-s FILE] [-o FILE] [-c {Burnaby,Surrey,Vancouver}] [-b BUILDING] [-f FLOOR] [-cf CLOSET_FLOOR] [-cst CLOSET] [-rk RACK]

Generate PM update file

optional arguments:
  -h, --help            show this help message and exit
  -x {icon,fixed,patch}, --switch {icon,fixed,patch}
                        function switch: "icon" for floor objects, "fixed" for fixed cables, "patch" for patching in comm rooms
  -s FILE, --source_file FILE
                        directory of source file
  -o FILE, --output_file FILE
                        directory of output file
  -c {Burnaby,Surrey,Vancouver}, --campus {Burnaby,Surrey,Vancouver}
                        campus name
  -b BUILDING, --building BUILDING
                        building name
  -f FLOOR, --floor FLOOR
                        floor name
  -cf CLOSET_FLOOR, --closet_floor CLOSET_FLOOR
                        floor of closet
  -cst CLOSET, --closet CLOSET
                        comm room number
  -rk RACK, --rack RACK
                        switch rack number
Limits and Practice:
	In generating faceplate icons: 1) number of ports on a faceplate <= 10; 2) not for AP faceplate if its format is in 'ROOM£-AP[n]'.
	In generating fixed cables (aka circuits): faceplates and comm room could be on same or different floors, but faceplates in a source file have to be on same floor, same idea to comm room.
	In generating patching: If patching is done in a good pattern, then it's more efficient to manually make connections on Patch Manager, insead of running Python.

Templates:

