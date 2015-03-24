#! /usr/bin/make -f

SOURCES = \
	description.xml \
	META-INF/manifest.xml \
	Addons.xcu \
	Jobs.xcu \
	ProtocolHandler.xcu \
	Accelerators.xcu \
	cybercompliance.py

ADDITIONAL_PATHS = pythonpath icons

EXTENSION = cybercompliance.oxt

all: $(EXTENSION)

$(EXTENSION):
	zip -r $(EXTENSION) \
		$(SOURCES) \
		$(ADDITIONAL_PATHS)

clean:
	rm $(EXTENSION)

install:
	unopkg add $(EXTENSION)

uninstall:
	unopkg remove $(EXTENSION)
