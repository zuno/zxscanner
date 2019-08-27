#!/usr/bin/env python2
#
# ZX Raspberry Keyboard Scanner v4.1
# @mrpjevans mrpjevans.com 2017
# MIT License (https://opensource.org/licenses/MIT) see LICENSE
#


# diff from the original:
#
# added a status led (power on/power off)
# added an rgb led to remember the keyboard status
# added a buzzer
#
# added a full english keyboard (currently no numpad and no F keys) for console use
# please be sure to select en_US keyboard layout on raspi-config
#
# long-press button mean shutdown fuse if running, or shutdown host otherwise
#
# funcKeys: '9' is 'TAB' (needed on some place)
#
# on the normal keyboard the rgb is RED
# on the function keyboard the rgb is GREEN
# on the console keyboard the rgb is BLUE
#
# the console keyboard has 4 layout:
# - normal: normal keys
# - shift: 
# ZX keys in shift mode
# all [A-Z] are mapped as 'SHIFT' [A-Z]
# 1 ( EDIT ) as ESC
# 2 ( CAPS LOCK ) as CAPSLOCK key
# 3 ( TRUE VIDEO ) not mapped
# 4 ( INV VIDEO ) not mapped
# 5 6 7 8 as LEFT DOWN UP RIGHT
# 9 ( GRAPHICS ) not mapped
# 0 ( DELETE) as BACKSPACE
# SPACE (break) as CTRL+C
# - symbols:
# ZX keys with 'symbol' pressed
# all ascii utf7 symbols matched (all but pound over X and copyright under P), under or below the key (example the key 'D' match '\' and not 'TO')
# all other are mapped:
#    Q ( <= ) as PAGEDOWN
#    W ( <> ) as HOME
#    E ( => ) as PAGEUP
#    I ( IN/INPUT) as INSERT
#    LEFTSHIFT switch to extended mode (as 'E' cursor)
#    X ( CLEAR) as DELETE
#    SPACE as TAB
#    ENTER as normal ENTER
# - extended: after pressed SHIFT+SYMBOL
# all keys are mapped as 'LEFTCTRL'
#
# consoleMode supports autorepeat
#
# keyTrack stores False for not pressed or time of keypressed
#
# replaced TABs with SPACEs in the entire code. sorry.


import time, sys, wiringpi, uinput, os

# KB1 (BCOM GPIO pins)
dataLines = [17,4,27,22,9]

# KB1 (BCOM GPIO pins)
addressLines = [11,5,6,26,19,16,20,21]

# Button PIN BCM
buttonGPIO = 12
buttonLED = 13 # support PWM (currently optional; only for future use)

# rgb PIN BCM
ledR = 25
ledG = 23
ledB = 24

# buzzer PIN BCM
buzzerPIN = 18 # support PWM

# The ZX Spectrum Keyboard Matrix (Mapped to modern keyboard )
keys = [
    ['1','2','3','4','5'],
    ['Q','W','E','R','T'],
    ['A','S','D','F','G'],
    ['0','9','8','7','6'],
    ['P','O','I','U','Y'],
    ['LEFTSHIFT','Z','X','C','V'],
    ['ENTER','L','K','J','H'],
    ['SPACE','LEFTCTRL','M','N','B']
]

# Function key mode
funcKeys = [
    ['F1','F2','F3','F4','LEFT'],
    ['Q','W','E','R','T'],
    ['A','S','D','F','G'],
    ['ESC','TAB','RIGHT','UP','DOWN'],
    ['P','O','I','U','Y'],
    ['LEFTSHIFT','Z','X','C','V'],
    ['ENTER','L','K','J','H'],
    ['SPACE','LEFTCTRL','M','N','B']
]

# Track keypresses so we can support multiple keys
keyTrack = [
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False]
]

# Keyboard mode and reset button
buttonPressed = -1
buttonTime = 0

# 0 = Spectrum, 1 = Function Keys
keyboardMode = 0

# Local path
myDir = os.path.dirname(os.path.realpath(__file__));

# 102+ keyboard
#
# ESC  F1 F2 F3 F4  F5 F6 F7 F8  F9 F10 F11 F2          PRINT SCRLCK PAUSE
# `~ 1! 2@ 3# 4$ 5% 6^ 7& 8* 9( 0) -_ =+ BACKSPACE      INS   HOME PGUP       NUM / * -
# TAB qQ wW eE rR tT yY uU iI oO pP [{ ]}  ENTER        CANC  END  PGDOW        7 8 9 +
# CAPS aA sS dD fF gG hH jJ kK lL ;: '" \|                                      4 5 6 
# SHIFT <> zZ xX cC vV bB nN mM ,< .> /? SHIFT                UP                1 2 3 
# CTRL WIN ALT          SPACE       ALTGR MENU CTRL     LEFT DOWN RIGHT         0 . ENTER

# zx spectrum keyboard
#
# 1!edit 2@caps 3#truev 4$invv 5%left 6&down 7'up 8(right 9)gr 0_del
# Q<=    W<>    E>=     R<     T>     Y[     U]   I       O;   P"
# A~     S|     D`      F{     G}     H^     J-   K+      L=   enter
# sh/cap Z:     X       C?     V/     B*     N,   M.      sym  sp/brk

# keys are tuple; ('SHIFT','A') sends press SHIFT press A release A release SHIFT
# ZX keys in normal mode
normalKeys = [
    [('1',),('2',),('3',),('4',),('5',)],
    [('Q',),('W',),('E',),('R',),('T',)],
    [('A',),('S',),('D',),('F',),('G',)],
    [('0',),('9',),('8',),('7',),('6',)],
    [('P',),('O',),('I',),('U',),('Y',)],
    ['shift',('Z',),('X',),('C',),('V',)],
    [('ENTER',),('L',),('K',),('J',),('H',)],
    [('SPACE',),'symbol',('M',),('N',),('B',)]
]

# ZX keys in shift mode
# all [A-Z] are mapped as 'SHIFT' [A-Z]
# 1 ( EDIT ) as ESC
# 2 ( CAPS LOCK ) as CAPSLOCK key
# 3 ( TRUE VIDEO ) as ???
# 4 ( INV VIDEO ) as ???
# 5 6 7 8 as LEFT DOWN UP RIGHT
# 9 ( GRAPHICS ) as ???
# 0 ( DELETE) as BACKSPACE
# SPACE (break) as CTRL+C
shiftKeys = [
    [('ESC',),('CAPSLOCK',),False,False,('LEFT',)], # edit as esc, capslock as capslock, truevideo, invvideo, left 
    [('LEFTSHIFT','Q'),('LEFTSHIFT','W'),('LEFTSHIFT','E'),('LEFTSHIFT','R'),('LEFTSHIFT','T')],
    [('LEFTSHIFT','A'),('LEFTSHIFT','S'),('LEFTSHIFT','D'),('LEFTSHIFT','F'),('LEFTSHIFT','G')],
    [('BACKSPACE',),False,('RIGHT',),('UP',),('DOWN',)], # delete graphics right up down
    [('LEFTSHIFT','P'),('LEFTSHIFT','O'),('LEFTSHIFT','I'),('LEFTSHIFT','U'),('LEFTSHIFT','Y')],
    ['shift',('LEFTSHIFT','Z'),('LEFTSHIFT','X'),('LEFTSHIFT','C'),('LEFTSHIFT','V')],
    [('ENTER',),('LEFTSHIFT','L'),('LEFTSHIFT','K'),('LEFTSHIFT','J'),('LEFTSHIFT','H')],
    [('LEFTCTRL','C'),'symbol',('LEFTSHIFT','M'),('LEFTSHIFT','N'),('LEFTSHIFT','B')] # sh+space == ctrl+c
]

# ZX keys with 'symbol' pressed
# all ascii utf7 symbols matched (all but pound over X and copyright under P), under or below the key (example the key 'D' match '\' and not 'TO')
# all other are mapped:
#    Q ( <= ) as PAGEDOWN
#    W ( <> ) as HOME
#    E ( => ) as PAGEUP
#    I ( IN/INPUT) as INSERT
#    LEFTSHIFT switch to extended mode (as 'E' cursor)
#    X ( CLEAR) as DELETE
#    SPACE as TAB
#    ENTER as normal ENTER
symbolKeys = [
    [('LEFTSHIFT','1'),('LEFTSHIFT','2'),('LEFTSHIFT','3'),('LEFTSHIFT','4'),('LEFTSHIFT','5')], # ! @ # $ %
    [('PAGEDOWN',),('HOME',),('PAGEUP',),('LEFTSHIFT','COMMA',),('LEFTSHIFT','DOT')], # (<= as pgdown) (<> as home) (>= as pgup) < >
    [('LEFTSHIFT','GRAVE'),('LEFTSHIFT','BACKSLASH'),('GRAVE',),('LEFTSHIFT','LEFTBRACE'),('LEFTSHIFT','RIGHTBRACE')], # ~ | ` { }
    [('LEFTSHIFT','MINUS'),('LEFTSHIFT','0'),('LEFTSHIFT','9'),('APOSTROPHE',),('LEFTSHIFT','7')], # _ ) ( ' &
    [('LEFTSHIFT','APOSTROPHE'),('SEMICOLON',),('LEFTSHIFT','INSERT'),('RIGHTBRACE',),('LEFTBRACE',)], # " ; (in as insert) ] [
    ['extended',('LEFTSHIFT','SEMICOLON'),('LEFTSHIFT','DELETE'),('LEFTSHIFT','SLASH'),('SLASH',)], # extended : (clear) ? /
    [('ENTER',),('EQUAL',),('LEFTSHIFT','EQUAL'),('MINUS',),('LEFTSHIFT','6')], # enter = + - ^
    [('TAB',),'symbol',('DOT',),('COMMA',),('LEFTSHIFT','8')] # (space as tab) symbol . , *
]

# ZX keys in extended mode
# all keys are mapped as 'LEFTCTRL'
extendedKeys = [
    [('LEFTCTRL','1'),('LEFTCTRL','2'),('LEFTCTRL','3'),('LEFTCTRL','4'),('LEFTCTRL','5')], 
    [('LEFTCTRL','Q'),('LEFTCTRL','W'),('LEFTCTRL','E'),('LEFTCTRL','R'),('LEFTCTRL','T')],
    [('LEFTCTRL','A'),('LEFTCTRL','S'),('LEFTCTRL','D'),('LEFTCTRL','F'),('LEFTCTRL','G')],
    [('LEFTCTRL','0'),('LEFTCTRL','9'),('LEFTCTRL','8'),('LEFTCTRL','7'),('LEFTCTRL','6')],
    [('LEFTCTRL','P'),('LEFTCTRL','O'),('LEFTCTRL','I'),('LEFTCTRL','U'),('LEFTCTRL','Y')],
    ['shift',('LEFTCTRL','Z'),('LEFTCTRL','X'),('LEFTCTRL','C'),('LEFTCTRL','V')],
    [('LEFTCTRL','ENTER'),('LEFTCTRL','L'),('LEFTCTRL','K'),('LEFTCTRL','J'),('LEFTCTRL','H')],
    [('LEFTCTRL','SPACE'),'symbol',('LEFTCTRL','M'),('LEFTCTRL','N'),('LEFTCTRL','B')]
]


def getKey(k):
    # k is a tuple
    if   (consoleMode == 0): modeKeys = normalKeys
    elif (consoleMode == 1): modeKeys = shiftKeys
    elif (consoleMode == 2): modeKeys = symbolKeys
    elif (consoleMode == 3): modeKeys = extendedKeys
    return modeKeys[k[0]][k[1]]


# Well this is annoying
device = uinput.Device([

    uinput.KEY_ESC,
    uinput.KEY_F1,
    uinput.KEY_F2,
    uinput.KEY_F3,
    uinput.KEY_F4,
    uinput.KEY_F5,
    uinput.KEY_F6,
    uinput.KEY_F7,
    uinput.KEY_F8,
    uinput.KEY_F9,
    uinput.KEY_F10,
    # uinput.KEY_F11,
    # uinput.KEY_F12,

    uinput.KEY_GRAVE,   # ` ~
    uinput.KEY_1,       # 1 !
    uinput.KEY_2,       # 2 @
    uinput.KEY_3,       # 3 #
    uinput.KEY_4,       # 4 $
    uinput.KEY_5,       # 5 %
    uinput.KEY_6,       # 6 ^
    uinput.KEY_7,       # 7 &
    uinput.KEY_8,       # 8 *
    uinput.KEY_9,       # 9 (
    uinput.KEY_0,       # 0 )
    uinput.KEY_MINUS,   # - _
    uinput.KEY_EQUAL,   # = +
    uinput.KEY_BACKSPACE,

    uinput.KEY_TAB,
    uinput.KEY_Q,       
    uinput.KEY_W,
    uinput.KEY_E,
    uinput.KEY_R,
    uinput.KEY_T,
    uinput.KEY_Y,
    uinput.KEY_U,
    uinput.KEY_I,
    uinput.KEY_O,
    uinput.KEY_P,
    uinput.KEY_LEFTBRACE,  # [ {
    uinput.KEY_RIGHTBRACE, # ] }
    uinput.KEY_ENTER,

    uinput.KEY_CAPSLOCK,
    uinput.KEY_A,
    uinput.KEY_S,
    uinput.KEY_D,
    uinput.KEY_F,
    uinput.KEY_G,
    uinput.KEY_H,
    uinput.KEY_J,
    uinput.KEY_K,
    uinput.KEY_L,
    uinput.KEY_SEMICOLON,  # ; :
    uinput.KEY_APOSTROPHE, # ' "
    uinput.KEY_BACKSLASH,  # \ |

    uinput.KEY_LEFTSHIFT,
    #uinput.KEY_102ND,      # < > on most querty 102+key layouts
    uinput.KEY_Z,
    uinput.KEY_X,
    uinput.KEY_C,
    uinput.KEY_V,
    uinput.KEY_B,
    uinput.KEY_N,
    uinput.KEY_M,
    uinput.KEY_COMMA, # , <
    uinput.KEY_DOT, # . <
    uinput.KEY_SLASH, # / ?
    uinput.KEY_RIGHTSHIFT,

    uinput.KEY_LEFTCTRL,
    uinput.KEY_LEFTALT,
    uinput.KEY_SPACE,
    uinput.KEY_RIGHTALT,
    uinput.KEY_RIGHTCTRL,

    # uinput.KEY_SYSRQ,
    # uinput.KEY_SCROLLLOCK,
    # uinput.KEY_PAUSE,
    uinput.KEY_INSERT,
    uinput.KEY_HOME,
    uinput.KEY_PAGEUP,
    uinput.KEY_DELETE,
    uinput.KEY_END,
    uinput.KEY_PAGEDOWN,

    uinput.KEY_UP,
    uinput.KEY_LEFT,
    uinput.KEY_RIGHT,
    uinput.KEY_DOWN,

    # uinput.KEY_NUMLOCK,
    # uinput.KEY_KPSLASH,
    # uinput.KEY_KPASTERISK,     # KEYPAD *
    # uinput.KEY_KPMINUS,
    # uinput.KEY_KP7,
    # uinput.KEY_KP8,
    # uinput.KEY_KP9,
    # uinput.KEY_KPPLUS,
    # uinput.KEY_KP4,
    # uinput.KEY_KP5,
    # uinput.KEY_KP6,
    # uinput.KEY_KP1,
    # uinput.KEY_KP2,
    # uinput.KEY_KP3,
    # uinput.KEY_KP0,
    # uinput.KEY_KPDOT,
    # uinput.KEY_KPENTER,
])

# Setup GPIO

def bip(f,l):
    wiringpi.softToneWrite(buzzerPIN,f)
    time.sleep(l/1000.0)
    wiringpi.softToneWrite(buzzerPIN,0)

def setled(r,g,b):
    wiringpi.digitalWrite(ledR,r)
    wiringpi.digitalWrite(ledG,g)
    wiringpi.digitalWrite(ledB,b)

def getled():
    return ( wiringpi.digitalRead(ledR), wiringpi.digitalRead(ledG), wiringpi.digitalRead(ledB) )

wiringpi.wiringPiSetupGpio()

wiringpi.softToneCreate(buzzerPIN)

wiringpi.pinMode(buttonLED, 1)
wiringpi.digitalWrite(buttonLED, 1)
for led in [ledR,ledG,ledB]:
    wiringpi.pinMode(led, 1)

setled(1,0,0)


# Set all address lines high
for addressLine in addressLines:
    wiringpi.pinMode(addressLine, 1)
    wiringpi.digitalWrite(addressLine, 1)

# Set all data lines for input
for dataLine in dataLines:
    wiringpi.pullUpDnControl(dataLine, 2)

# Setup Button
wiringpi.pinMode(buttonGPIO, 0)
wiringpi.pullUpDnControl(buttonGPIO, 2)

# Announce
print("Running")
bip(1000,100)

try:

    # Loop forever
    while True:
        # Button check
        if(wiringpi.digitalRead(buttonGPIO) == False):
            # Record time the button was pressed
            if(buttonPressed == -1):
                buttonPressed = time.time()
                print('Button pressed')
                bip(3000,20)
                buttonBip=time.time()
            else:
                # bip 3 times before act
                if(time.time() > buttonBip+1):
                    buttonBip=time.time()
                    bip(3000,10)

        elif(buttonPressed != -1):
            # Button released - but how long was it pressed for?
            buttonTime = time.time() - buttonPressed

            # If over 3 secs, switch keyboard mode
            if(buttonTime < 3):

                # Switch modes
                if(keyboardMode == 0):
                    print("Switching to Function Keys")
                    keyboardMode = 1;
                    bip(1000,200)
                    setled(0,1,0)
                elif(keyboardMode == 1):
                    print("Switching to Console Keys")
                    keyboardMode = 2;
                    bip(2000,200)
                    setled(0,0,1)
                    consoleMode = 0
                    consoleModeTime = time.time()
                    autorepeatKey = None
                elif(keyboardMode == 2):
                    print("Switching to Spectrum Keys")
                    keyboardMode = 0;
                    bip(3000,200)
                    setled(1,0,0)
            else:
                print('Killing FUSE or shutdown')
                os.system('if pgrep fuse; then killall fuse; else halt;fi')

            # Reset
            buttonPressed = -1
                        
        if(keyboardMode < 2):
            # Keyboard(s) for fuse

            # Individually set each address line low
            for addressLine in range(8):
                
                # Set low
                wiringpi.digitalWrite(addressLines[addressLine], 0)
                
                # Scan data lines
                for dataLine in range(5):

                    # Get state and details for this button
                    isFree = wiringpi.digitalRead(dataLines[dataLine])
                    if(keyboardMode == 0):
                        keyPressed = keys[addressLine][dataLine]
                    else:
                        keyPressed = funcKeys[addressLine][dataLine]
                    keyCode = getattr(uinput, 'KEY_' + keyPressed)

                    # If pressed for the first time
                    if(isFree == False and keyTrack[addressLine][dataLine] == False):

                        # Press the key and make a note
                        print('Pressing ' + keyPressed)
                        device.emit(keyCode, 1)
                        keyTrack[addressLine][dataLine] = time.time()
                        bip(3000,1)

                    # If not pressed now but was pressed on last check
                    elif(isFree == True and keyTrack[addressLine][dataLine]):
                            
                        # Release the key and make a note
                        print('Releasing ' + keyPressed)
                        device.emit(keyCode, 0)
                        keyTrack[addressLine][dataLine] = False

                # Set high
                wiringpi.digitalWrite(addressLines[addressLine], 1)

                # Have a quick snooze (suggested by Keef)
                time.sleep(.01)
        
        if(keyboardMode == 2):
            # Keyboard for console


            # consoleMode:
            #     0 = normal
            #     1 = shift pressed
            #     2 = symbol pressed
            #     3 = extended (shift+symbol pressed then released)
            if   (consoleMode == 0): setled(0,0,1)
            elif (consoleMode == 1): setled(0,1,1)
            elif (consoleMode == 2): setled(1,0,1)
            elif (consoleMode == 3): setled(1,1,1)
            listPressed=[]


            # Individually set each address line low
            for addressLine in range(8):
                    
                # Set low
                wiringpi.digitalWrite(addressLines[addressLine], 0)
                
                # Scan data lines
                for dataLine in range(5):

                    # Get state and details for this button
                    isFree = wiringpi.digitalRead(dataLines[dataLine])
                    keyPressed = keys[addressLine][dataLine]
                    # keyCode = getattr(uinput, 'KEY_' + keyPressed)

                    if(isFree == False and type(normalKeys[addressLine][dataLine])==type(())):
                        listPressed.append((addressLine,dataLine))

                    # If pressed for the first time
                    if(isFree == False and keyTrack[addressLine][dataLine] == False):

                        # Press the key and make a note
                        print('Pressing ' + keyPressed)
                        keyTrack[addressLine][dataLine] = time.time()
                        autorepeatKey = {'k':(addressLine,dataLine),'n':0,'t':False}
                        # if two keys are pressed the last wins

                    # If not pressed now but was pressed on last check
                    elif(isFree == True and keyTrack[addressLine][dataLine]):
                        
                        # Release the key and make a note
                        print('Releasing ' + keyPressed)
                        keyTrack[addressLine][dataLine] = False
                        autorepeatKey = None

                # Set high
                wiringpi.digitalWrite(addressLines[addressLine], 1)

                # Have a quick snooze (suggested by Keef)
                time.sleep(.01)

            shiftkey = keyTrack[5][0]
            symbolkey = keyTrack[7][1]
            if shiftkey > consoleModeTime or symbolkey > consoleModeTime:
                print "enter change mode"
                # need to change console mode; all keys already pressed will be ignored
                autorepeatKey = None
                if shiftkey and symbolkey:
                    if consoleMode == 3:
                        consoleMode=0
                    else:
                        consoleMode=3
                    extendedPressed = False
                    print "shift+symbol pressed"
                elif shiftkey:
                    consoleMode = 1
                    print "shift pressed"
                elif symbolkey:
                    consoleMode = 2
                    print "symbol pressed"
                print "mode switched to"
                print consoleMode
                consoleModeTime = time.time()
                continue
            if consoleMode == 3 and (shiftkey or symbolkey):
                autorepeatKey = None
                # to manage keys you have to release both shift and symbol
                continue
            if consoleMode == 0 and (shiftkey or symbolkey):
                autorepeatKey = None
                # this condition is bad, but possible
                continue
            if consoleMode == 1 and symbolkey:
                autorepeatKey = None
                # this condition is not possible
                continue
            if consoleMode == 2 and shiftkey:
                # this condition is not possible
                autorepeatKey = None
                continue
            if consoleMode == 1 and not shiftkey:
                # shift was released; need change mode
                print "shift released rollback to normal"
                autorepeatKey = None
                consoleMode = 0
                consoleModeTime = time.time()
                continue
            if consoleMode == 2 and not symbolkey:
                # symbol was released; need change mode
                print "symbol released rollback to normal"
                autorepeatKey = None
                consoleMode = 0
                consoleModeTime = time.time()
                continue
            if consoleMode == 3 and extendedPressed and not listPressed:
                # you can turnoff extended mode
                print "return to normal after extended"
                autorepeatKey = None
                consoleMode = 0
                consoleModeTime = time.time()
                continue
            # now you can manage pressed keys
            # autorepeatKey = {'k':(addressLine,dataLine),'n':0,'t':False}
            if autorepeatKey:
                keyPressed = getKey(autorepeatKey['k'])
                print keyPressed
                if not keyPressed:
                    # key not implemented
                    autorepeatKey = None
                    continue
                if (autorepeatKey['n'] == 0) or (autorepeatKey['n'] == 1 and time.time() > autorepeatKey['t']+0.7) or (autorepeatKey['n'] > 1 and time.time() > autorepeatKey['t']+0.2):
                    extendedPressed = True
                    bip(3000,1)
                    autorepeatKey['t']=time.time()
                    autorepeatKey['n']+=1
                    print autorepeatKey['n']
                    if len(keyPressed) == 1:
                        keyCode = getattr(uinput, 'KEY_' + keyPressed[0])
                        device.emit(keyCode, 1)
                        print "press "+keyPressed[0]+" down"
                        device.emit(keyCode, 0)
                        print "press "+keyPressed[0]+" up"
                    else:
                        keyCode0 = getattr(uinput, 'KEY_' + keyPressed[0])
                        keyCode1 = getattr(uinput, 'KEY_' + keyPressed[1])
                        device.emit(keyCode0, 1)
                        print "press "+keyPressed[0]+" down"
                        device.emit(keyCode1, 1)
                        print "press "+keyPressed[1]+" down"
                        device.emit(keyCode1, 0)
                        print "press "+keyPressed[1]+" up"
                        device.emit(keyCode0, 0)
                        print "press "+keyPressed[0]+" up"

except KeyboardInterrupt:
    for led in [ledR,ledG,ledB,buttonLED]:
        wiringpi.digitalWrite(led, 0)
    bip(500,100)
    sys.exit(0)
