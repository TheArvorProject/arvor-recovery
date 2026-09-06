.PHONY: all test run run-sim install clean help

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
LIBDIR ?= $(PREFIX)/lib/arvor-recovery

all: test

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v

run-sim:
	./bin/arvor-recovery --simulate

run:
	sudo ./bin/arvor-recovery

install:
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(LIBDIR)
	cp -a core ui assets $(DESTDIR)$(LIBDIR)/
	install -m 755 bin/arvor-recovery $(DESTDIR)$(BINDIR)/arvor-recovery

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf /tmp/arvor_recovery_build /tmp/arvor_recovery.squashfs

help:
	@echo "Arvor Linux Recovery Mode (100% Graphical UEFI Interface)"
	@echo "Targets:"
	@echo "  make test      - Run automated unit tests"
	@echo "  make run-sim   - Launch Graphical Recovery in simulation mode"
	@echo "  make run       - Launch Graphical Recovery with live root privileges"
	@echo "  make install   - Install to $(PREFIX)"
	@echo "  make clean     - Clean cache and build artifacts"
