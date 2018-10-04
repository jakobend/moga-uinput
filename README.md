# moga-uinput
Userland linux driver for Moga bluetooth gamepads in "A" mode

## Prototype
A working prototype can be found in `moga-uinput.py`. It only supports one controller per instance at the moment.

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
- Figure out best way to hook into BlueZ connection events (udev rule? daemon?)
- Implement userland driver in C
