;(This file is for a My Prusa w/ Bowden mount)
;(**** begin initilization commands ****)
G21 ;(set units to mm)
G90 ;(set positioning to absolute)
G28 ;(home all axis)
G1 Z0.0 F300 ; ( adjust for platform going up due to heat)
G92 Z0 ;(set the z level of homing)
G1 X0 Y0 Z10 F1500 ;(move up a bit)
M106 ; (Fan on)
G4 P1500 ; (Spin up)
M106 S200 ; (Slow down a bit)
;M140 S75 ;(set bed temperature)
;M104 S175 ;(set PLA extruder temperature)
M109 ;(wait for extruder)
M190 ;(wait for bed)
G1 X25 Y2 Z10 F1500 ;(move up a bit)
G92 E0 ;(reset extruder to 0)
G1 F100 ;(set feed rate to 60mm/min)
G1 E12  ;(feed some plastic)
G1 E6 F3200 ;(retract)
G92 E0 ;(reset extruder to 0)
; Give me 10sec some to clean up the plastic
G4 P10000 
