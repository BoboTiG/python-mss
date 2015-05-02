CC     = gcc
CFLAGS = -O3 -s -shared -rdynamic -fPIC -Wall -pedantic -lX11

all:
	${CC} ${CFLAGS} -m64 mss.c -o libmss-64.so
	${CC} ${CFLAGS} -m32 mss.c -o libmss.so

clean:
	rm -f libmss*
