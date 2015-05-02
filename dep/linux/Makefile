CC     = gcc
CFLAGS = -shared -rdynamic -fPIC -Wall -pedantic -lX11

all: help

32:
	${CC} ${CFLAGS} -m32 mss.c -o libmss.tmp
	mkdir -p 32
	mv libmss.tmp 32/libmss.so

64:
	${CC} ${CFLAGS} -m64 mss.c -o libmss.tmp
	mkdir -p 64
	mv libmss.tmp 64/libmss.so

clean:
	rm -f */libmss.so.${VERSION}

help:
	@echo make 32: 32 bits compilation
	@echo make 64: 64 bits compilation
