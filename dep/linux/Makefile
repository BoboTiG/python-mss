CC     = gcc
CFLAGS = -O3 -s -shared -rdynamic -fPIC -Wall -pedantic -lX11

all: help

32:
	${CC} ${CFLAGS} -m32 mss.c -o libmss.so.tmp
	mv libmss.so.tmp libmss.so

64:
	${CC} ${CFLAGS} -m64 mss.c -o libmss-64.so.tmp
	mv libmss-64.so.tmp libmss-64.so

clean:
	rm -f libmss*

help:
	@echo make 32: 32 bits compilation
	@echo make 64: 64 bits compilation
