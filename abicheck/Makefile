prefix ?= /usr
modules =  abicheck
cmd = abi-info-check

modules_dir = $(DESTDIR)$(prefix)/share/$(modules)
bin_dir = $(DESTDIR)$(prefix)/bin

.PHONY: install uninstall build

build:
	$(HOME)/.local/bin/pyinstaller -F -n $(cmd) main.py

install:
	mkdir -p $(modules_dir)
	cp -r conf  $(modules_dir)/
	mkdir -p $(bin_dir)
	install -m 755 dist/$(cmd) $(bin_dir)/$(cmd)

uninstall:
	rm -f $(bin_dir)/$(cmd)
	rm -rf $(modules_dir)

clean:
	rm -rf build/ dist/ __pycache__/
