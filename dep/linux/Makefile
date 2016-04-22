CC     = gcc
CFLAGS = -shared -rdynamic -fPIC -Wall -pedantic -lX11
ARCH  := $(shell getconf LONG_BIT)

clean:
	rm -f */libmss.so

all: clean
	mkdir -p ${ARCH}
	${CC} ${CFLAGS} -m${ARCH} mss.c -o ${ARCH}/libmss.so
