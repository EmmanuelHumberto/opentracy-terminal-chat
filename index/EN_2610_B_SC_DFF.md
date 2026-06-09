<!-- Convertido de: /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/knowledge/01-motores/brushless/EN_2610_B_SC_DFF.pdf -->

# EN_2610_B_SC_DFF


## Pagina 1

Edition 2020 Feb. 18
Brushless DC-Flat Motors
with integrated Speed Controller
1,6 W
3,12 mNm
2610 ... B SC
Values at 22°C and nominal voltage
2610 T
006 B SC
012 B SC
Power supply electronic
UP
4 ... 18
4 ... 18
V DC
Power supply motor
Umot
1,7 ... 18
1,7 ... 18
V DC
Nominal voltage for motor
UN
6
12
V
No-load speed  (at UN)
n0
6 700
6 650
min-¹
Peak torque  (S2 operation for max. 2s/1s)
Mmax.
6
6
mNm
Torque constant
kM
8,8
17,6
mNm/A
PWM switching frequency
fPWM
96
96
kHz
Efficiency electronic
η
95
95
%
Standby current for electronic (at UN)
lel
0,02
0,02
A
Speed range (up to 12V / 18V)
400 ... 13 300
400 ... 10 000
min-¹
 
 
 
Shaft bearings
ball bearings, preloaded
Shaft load max.:
– with shaft diameter
1,5
mm
– radial at 3 000 min-¹ (3 mm from mounting flange)
4
N
– axial at 3 000 min-¹ (push only)
3,5
N
– axial at standstill (push only)
17,5
N
Shaft play:
– radial
≤ 0,015
µm
– axial
= 0
µm
Operating temperature range
-25 ...
+80
°C
Housing material
plastic
Mass
20,1
g
Rated values for continuous operation
Rated torque
MN
3,25
3,12
mNm
Rated current (thermal limit)
IN
0,53
0,29
A
Rated speed
nN
1 600
1 300
min-¹
Interface / range of functions
... SC
Configuration from Motion Manager 5.0
via USB Programming Adapter
Operating modes
Integrated speed control via PI controller and external set value specification; commu-
tation via digital Hall sensors. Can optionally be operated in voltage controller mode or 
fixed speed mode.
Speed range
Digital Hall = from 400 min-1
Additional functions
Integrated current limitating to protect against thermal overload. Intermittent opera-
tion (S2) with up to double the continuous current. Separate voltage supply for motor 
and electronics. Direction of rotation changeover through separate switching input; 
reading of speed signal via frequency output.
M [mNm]
0,5
1
1,5
2
2,5
3
3,5
4
4,5
5
0
Watt
2 000
0
  4 000
  6 000
  8 000
 10 000
 12 000
UN
1,2
1,6
0,8
0,4
n [min-1]
Intermittent operation
Operating point 
at nominal value
Recommended operation areas (example: nominal voltage 12V) 
Note:
The display shows the range of possible 
operation points of the drives at a given 
ambient temperature of 22°C.
The diagram indicates the recommended 
speed in relation to the available torque 
at the output shaft.
It includes the assembly on a plastic- as well 
as on a metal flange (assembly method: 
IM B 5).
The nominal voltage linear slope describes 
the maximal achievable operating points 
at nominal voltage.
Any points of operation above this linear 
slope will require a supply voltage Umot > UN.
Plastic flange
Metal flange
For notes on technical data and lifetime performance  
refer to “Technical Information”.
© DR. FRITZ FAULHABER GMBH & CO. KG
Specifications subject to change without notice.
www.faulhaber.com


## Pagina 2

Edition 2020 Feb. 18
Dimensional drawing
2610 T ... B SC
1
1,25
1
6
1,5
  26
R 1,5
ø30
90°
4x
ø2,1
ø26
ø1,5
 0
-0,01
A
ø0,07
0,04
ø6 -0,05
A
 0
150±10
2±1
10,4±0,2
7±0,25
5x1
6±0,2
1±0,2
Option, cable and connection information
4257
 
 
 
 
 
 
 
 
1
6
Option
 Type                       Description
  
 
  
 
 
  
 
 
  
 
 
  
 
  
 
  
 
 
Example product designation: 2610T012BSC-4257
 
  
 
  
 
  
 
 
Name Function
Inputs-outputs 
Description 
 
Connection
 
 
 
1 
UP 
power supply electronic 
4 ... 18 V DC 
2  
Umot 
power supply motor 
1,7 ... 18 V DC 
3 
GND 
ground 
4  
Unsoll 
input voltage 
Uin = 0 ... 10 V | > 10 V ... UP 
 
 
 
» set speed value not defined 
 
 
input resistance 
Rin ≥ 8,9 kΩ
 
 
set speed value 
per 1 V , 1 000 min-1
 
 
 
Uin < 0,15 V » motor stops
 
 
 
Uin > 0,3 V » motor starts
5  
DIR 
direction of rotation 
to ground or U < 0,5 V » counterclockwise 
 
 
 
open or level > 3 V » clockwise 
 
 
input resistance 
Rin ≥ 10 kΩ
6  
FG 
frequency output 
max. UP; Imax = 15 mA; open collector 
 
 
 
with 22 kΩ pull-up resistor
 
 
 
6 lines per revolution
Standard cable
PVC ribbon cable 6 x AWG 28, 1 mm
Note: For details on the connection assignment, see device manual for the SCS.
AWG 28 / PVC ribbon cable 
with connector Picoblade
Connector
Precision Gearheads / Lead Screws
Encoders
Drive Electronics
Integrated
Cables / Accessories
To view our large range of 
accessory parts, please refer to the 
“Accessories” chapter.
For notes on technical data and lifetime performance  
refer to “Technical Information”.
© DR. FRITZ FAULHABER GMBH & CO. KG
Specifications subject to change without notice.
Product combination
www.faulhaber.com
