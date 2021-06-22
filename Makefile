SHELL  := /bin/bash
CSSIN   = src/css/main.css
CSSOUT  = public/css/main.css

yarn.lock: package.json
	yarn install

$(CSSOUT): $(CSSIN)
	yarn tailwindcss -i $< -o $@

css:
	yarn tailwindcss -i $(CSSIN) -o $(CSSOUT) --watch

dev: yarn.lock
	yarn shadow-cljs watch app

release: yarn.lock
	yarn shadow-cljs release app

browser-test: yarn.lock
	yarn shadow-cljs watch browser-test

node-test: yarn.lock
	yarn shadow-cljs compile node-test

start:
	yarn shadow-cljs start

stop:
	yarn shadow-cljs stop
