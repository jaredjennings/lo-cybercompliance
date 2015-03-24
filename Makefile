#! /usr/bin/make -f

SOURCES = \
	description.xml \
	META-INF/manifest.xml \
	Addons.xcu \
	Accelerators.xcu \
	cybercompliance.py

ADDITIONAL_PATHS = pythonpath icons

EXTENSION = cybercompliance.oxt

all: $(EXTENSION)

$(EXTENSION): $(SOURCES)
	zip -r $(EXTENSION) \
		$(SOURCES) \
		$(ADDITIONAL_PATHS)

clean:
	rm $(EXTENSION)

install:
	unopkg add $(EXTENSION)

uninstall:
	unopkg remove $(EXTENSION)
