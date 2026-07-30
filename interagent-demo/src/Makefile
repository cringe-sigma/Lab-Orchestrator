# InterAgent Demo — Build
CC     = gcc
CFLAGS = -O2 -Wall -pthread
BINDIR = ../bin

TARGETS = $(BINDIR)/victim $(BINDIR)/cache_attacker $(BINDIR)/memory_attacker

all: $(TARGETS)

$(BINDIR)/victim: victim.c common.h
	$(CC) $(CFLAGS) -o $@ victim.c

$(BINDIR)/cache_attacker: cache_attacker.c common.h
	$(CC) $(CFLAGS) -o $@ cache_attacker.c

$(BINDIR)/memory_attacker: memory_attacker.c common.h
	$(CC) $(CFLAGS) -o $@ memory_attacker.c

clean:
	rm -f $(TARGETS)

.PHONY: all clean
