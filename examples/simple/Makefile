BMFONT2C = python3 ../../bmfont2c.py
CFLAGS = -g3 -O0

test: test.o fontlibrary.o
test.o: test.c fontlibrary.h
fontlibrary.o: fontlibrary.c

fontlibrary.c fontlibrary.h: liberation.fnt liberation_0.tga bmfont2c.cfg
	$(BMFONT2C)

.PHONY: clean
clean:
	rm -f fontlibrary.c fontlibrary.h test *.o
