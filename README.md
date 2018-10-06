# moga-uinput
Userland linux driver for Moga bluetooth gamepads in "A" mode

## Architecture
`moga-uinput` runs as a daemon that monitors D-Bus connection messages from
`org.bluez`. When a Moga gamepad is found, a thread is spawned that creates
a new virtual UInput device for it, opens a bluetooth serial port and listens to
incoming messages from the gamepad. These are then translated to UInput events,
which are sent to the UInput device via libevdev.

## Prototype
A working prototype can be found in `moga-uinput.py`. It only implements the
per-gamepad logic, but also device discovery.

Requirements:
- Python 3
- [pybluez](https://github.com/pybluez/pybluez)
- [python-libevdev](https://github.com/whot/python-libevdev)

```
usage: moga-uinput.py PLAYER=1/2/3/4
```

## To do
- Add inline documentation to prototype
- Document Moga serial protocol
- Implement userland driver in C
