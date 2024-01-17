PRODUCT = declad
VERSION = 2.0.1
BUILD_HOME = $(HOME)/build
BUILD_DIR = $(BUILD_HOME)/$(PRODUCT)
TEMPLATES_DIR = $(BUILD_DIR)/templates
TAR_DIR = /tmp/$(USER)
TAR_FILE = $(TAR_DIR)/$(PRODUCT)_$(VERSION).tar


FILES = config.py declad.py file_descriptor.py fts3client.py \
        graphite_interface.py historydb.py lfn2pfn.py local_scanner.py \
        metacat_client.py mover.py rucio_client.py samweb_client.py \
        scanner.py tools.py version.py web_server.py xrootd_scanner.py \
        config_sample.yaml meta_sample.json

# - not needed as we are moving EOS to EOS using xrootd fts3client.py context.py request.py


all: tarball

tarball: build $(TAR_DIR)
	cd $(BUILD_DIR); tar cf $(TAR_FILE) *
	@echo
	@echo Tarfile $(TAR_FILE) created
	@echo

build: $(BUILD_DIR) $(TEMPLATES_DIR)
	@echo
	@echo building version $(VERSION) ...
	@echo
	find . -type f -name \*.pyc -exec rm -f {} \;
	echo 'Version="$(VERSION)"' > $(BUILD_DIR)/version.py
	cp $(FILES) $(BUILD_DIR)
	cp -R logs $(BUILD_DIR)
	cp -R custom $(BUILD_DIR)
	cp templates/*.html $(TEMPLATES_DIR)
	chmod +x $(BUILD_DIR)/declad.py

clean:
	rm -rf $(TAR_FILE) $(BUILD_DIR)

$(BUILD_DIR):
	mkdir -p $@

$(TAR_DIR):
	mkdir -p $@
	
$(TEMPLATES_DIR):	$(BUILD_DIR)
	mkdir -p $@
	
