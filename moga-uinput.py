#!/usr/bin/env python3

import sys, os, time
import bluetooth
import libevdev

class MogaInput(object):
    UINPUT_DATA = None

    def __init__(self, moga_nr, uinput_code):
        self.moga_nr = moga_nr
        self.uinput_code = uinput_code
        self.state = None
    
    def event(self):
        return libevdev.InputEvent(self.uinput_code, value=self.state)

    def update(self, state):
        if self.state != state:
            self.state = state
            return True
        return False
    
    def parse(self, data):
        raise NotImplementedError

    def process(self, data):
        state = self.parse(data)
        if self.update(state): return self.event()
        else: return None

class MogaButton(MogaInput):
    def parse(self, data):
        return bool(data[0] & (1 << self.moga_nr))

class MogaAxis(MogaInput):
    UINPUT_DATA = libevdev.InputAbsInfo(
        minimum=-127,
        maximum=127,
        resolution=8
    )
    def __init__(self, moga_nr, uinput_code, invert=False):
        super().__init__(moga_nr, uinput_code)
        self.invert = invert
    def parse(self, data):
        state = data[2 + self.moga_nr]
        if state >= 128:
            state -= 255
        return -state if self.invert else state

class MogaTrigger(MogaInput):
    UINPUT_DATA = libevdev.InputAbsInfo(
        minimum=0,
        maximum=255,
        resolution=8
    )
    def parse(self, data):
        return data[6 + self.moga_nr]

class MogaPad(MogaButton):
    def parse(self, data):
        return data[1] & (1 << self.moga_nr)

class MogaBridge(object):
    PLAYER_COMMAND = 67
    POLL_COMMAND = 65
    POLL_RESPONSE = 97
    LISTEN_COMMAND = 68
    LISTEN_RESPONSE = 100

    REPORT_EVENT = libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, value=0)

    @staticmethod
    def checksum(data):
        n = 0
        for i in data:
            n = (i ^ n) & 255
        return n

    @staticmethod
    def is_gen1_name(name):
        return name.upper().startswith("BD&A") \
            or name.upper().startswith("BDA")
    @staticmethod
    def is_gen2_name(name):
        return name.upper().startswith("MOGA") \
            and "HID" not in name.upper()
    @staticmethod
    def is_moga_name(name):
        return MogaBridge.is_gen1_name(name) \
            or MogaBridge.is_gen2_name(name)

    @classmethod
    def find(cls, timeout=5, player=1):
        devices = bluetooth.discover_devices(
            duration=timeout,
            lookup_names=True
        )
        for address, name in devices:
            if cls.is_moga_name(name):
                services = bluetooth.find_service(address=address)
                for service in services:
                    if service["protocol"] == "RFCOMM":
                        if cls.is_gen2_name(name):
                            return Moga2Bridge(name, address=address, port=service["port"], player=player)
                        else:
                            return MogaBridge(name, address=address, port=service["port"], player=player)

    def __init__(self, name, address, port, player=1):
        self.name = name
        self.address = address
        self.port = port
        self.player = player
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

        self.device = libevdev.Device()
        self.device.name = self.name
        self.uinput_device = None
        self.inputs = {}

        self.add_inputs(
            Y=MogaButton(0, libevdev.EV_KEY.BTN_NORTH),
            B=MogaButton(1, libevdev.EV_KEY.BTN_EAST),
            A=MogaButton(2, libevdev.EV_KEY.BTN_SOUTH),
            X=MogaButton(3, libevdev.EV_KEY.BTN_WEST),
            START=MogaButton(4, libevdev.EV_KEY.BTN_START),
            SELECT=MogaButton(5, libevdev.EV_KEY.BTN_SELECT),
            L1=MogaButton(6, libevdev.EV_KEY.BTN_TL),
            R1=MogaButton(7, libevdev.EV_KEY.BTN_TR),

            X1=MogaAxis(0, libevdev.EV_ABS.ABS_X),
            Y1=MogaAxis(1, libevdev.EV_ABS.ABS_Y, invert=True),
            X2=MogaAxis(2, libevdev.EV_ABS.ABS_RX),
            Y2=MogaAxis(3, libevdev.EV_ABS.ABS_RY, invert=True),

            UP=MogaPad(0, libevdev.EV_KEY.BTN_DPAD_UP),
            DOWN=MogaPad(1, libevdev.EV_KEY.BTN_DPAD_DOWN),
            LEFT=MogaPad(2, libevdev.EV_KEY.BTN_DPAD_LEFT),
            RIGHT=MogaPad(3, libevdev.EV_KEY.BTN_DPAD_RIGHT),
            L2P=MogaPad(4, libevdev.EV_KEY.BTN_TL2),
            R2P=MogaPad(5, libevdev.EV_KEY.BTN_TR2),
            THUMBL=MogaPad(6, libevdev.EV_KEY.BTN_THUMBL),
            THUMBR=MogaPad(7, libevdev.EV_KEY.BTN_THUMBR)
        )
    
    def add_inputs(self, **kwargs):
        self.inputs.update(kwargs)
        for name, input in kwargs.items():
            self.device.enable(input.uinput_code, data=input.UINPUT_DATA)

    def connect(self):
        self.uinput_device = self.device.create_uinput_device()
        self.socket.connect((self.address, self.port))
        self.send(self.PLAYER_COMMAND)
    
    def close(self):
        self.socket.close()
        self.uinput_device.fd.close()
        self.uinput_device = None

    def send(self, command):
        data = bytearray(5)
        data[0] = 0x5A
        data[1] = len(data)
        data[2] = command
        data[3] = self.player
        data[4] = self.checksum(data[:-1])
        self.socket.send(bytes(data))
    
    def recv(self):
        data = self.socket.recv(12)
        assert(data[0] == 0x7A)
        size = data[1]
        if size > 12:
            data = data + self.socket.recv(size - 12)
        assert(len(data) == size)
        assert(self.checksum(data[:-1]) == data[-1])
        response = data[2]
        payload = data[4:4 + size]
        player = data[3]
        assert(player == self.player)
        return (response, payload, player)
    
    def process(self, data):
        events = []
        for name, input in self.inputs.items():
            event = input.process(data)
            if event: events.append(event)
        return events
    
    def poll(self):
        self.send(self.POLL_COMMAND)
        response, payload, player = self.recv()
        if response == self.POLL_RESPONSE:
            return self.process(payload)

    def listen(self):
        self.send(self.LISTEN_COMMAND)
        while True:
            response, payload, player = self.recv()
            if response == self.LISTEN_RESPONSE:
                events = self.process(payload)
                if events:
                    yield events

    def bridge(self):
        for events in self.listen():
            events.append(self.REPORT_EVENT)
            self.uinput_device.send_events(events)
            yield events

class Moga2Bridge(MogaBridge):
    POLL_COMMAND = 69
    POLL_RESPONSE = 101
    LISTEN_COMMAND = 70
    LISTEN_RESPONSE = 102

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_inputs(
            L2=MogaTrigger(0, libevdev.EV_ABS.ABS_HAT2Y),
            R2=MogaTrigger(1, libevdev.EV_ABS.ABS_HAT2X)
        )

BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
def main():
    try:
        player = int(sys.argv[1])
        if player < 1 or player > 4:
            raise ValueError("player must be between 1 and 4")
    except (IndexError, ValueError) as e:
        print("error: {}".format(e))
        print("usage: moga-uinput.py PLAYER=1/2/3/4")
        return
    print("Searching for Moga device...")
    while True:
        moga = MogaBridge.find(timeout=10, player=player)
        if moga: break
        print("Retrying...")
    moga.connect()
    last_code = None
    for events in moga.bridge():
        for event in events:
            if event == MogaBridge.REPORT_EVENT:
                continue
            if event.code != last_code:
                last_code = event.code
                sys.stdout.write("\n{}".format(event.code))
            if event.type == libevdev.EV_ABS:
                if event.code == libevdev.EV_ABS.ABS_HAT2X or event.code == libevdev.EV_ABS.ABS_HAT2Y:
                    block = BLOCKS[int((event.value / 256) * len(BLOCKS))]
                else:
                    block = BLOCKS[int(((event.value + 127) / 256) * len(BLOCKS))]
                sys.stdout.write(block)
            else:
                sys.stdout.write("\u2588" if event.value else " ")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
