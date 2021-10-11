SHELL  := /bin/bash

yarn.lock: package.json
	yarn install

dev: yarn.lock
	yarn shadow-cljs watch app

release: yarn.lock
	yarn shadow-cljs release app --verbose --debug

browser-test: yarn.lock
	yarn shadow-cljs watch browser-test

node-test: yarn.lock
	yarn shadow-cljs compile node-test --verbose

start:
	yarn shadow-cljs start

stop:
	yarn shadow-cljs stop
