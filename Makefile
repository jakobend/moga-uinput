PACKAGES:=glib-2.0 gio-2.0
CFLAGS+=`pkg-config --cflags $(PACKAGES)`
LDFLAGS+=`pkg-config --libs $(PACKAGES)`
OBJECTS=src/main.o

moga-uinput: $(OBJECTS)
	$(CC) $(LDFLAGS) $< -o $@

.PHONY: all
all: moga-uinputt

.PHONY: clean
clean:
	$(RM) $(OBJECTS) moga-uinput
