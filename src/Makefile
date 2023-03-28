prefix ?= /usr
modules =  abicheck
cmd = abi-info-check-online

modules_dir = $(DESTDIR)$(prefix)/share/$(modules)
bin_dir = $(DESTDIR)$(prefix)/bin
man1_dir = $(DESTDIR)$(prefix)/share/man/man1

.PHONY: install uninstall

install:
	mkdir -p $(modules_dir)
	cp -r conf  $(modules_dir)/

	python3  ./$(cmd).py -v
	mkdir -p $(man1_dir)
	mkdir -p $(man1_dir)
	install -m 644 ${cmd}.1 $(man1_dir)/

	$(HOME)/.local/bin/pyinstaller -F $(cmd).py
	install -m 755 dist/$(cmd) $(bin_dir)/

uninstall:
	rm -f $(bin_dir)/$(cmd)
	rm -f $(man1_dir)/$(cmd).1*
	rm -rf $(modules_dir)

clean:
	rm -rf build/ dist/ __pycache__/
build:
	$(HOME)/.local/bin/pyinstaller -F $(cmd).py
