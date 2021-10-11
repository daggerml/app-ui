(ns daggerml.app.dml.layout
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.ui :as ui]))

(deftag MAIN
  [_ [] [side content] [] []]
  "
  :host { display: block; }
  #container {
  }
  #side {
    position: fixed;
    height: 100vh;
    width: var(--main-layout--side-width);
    top: 0;
    left: 0;
    z-index: 100;
  }
  #content {
    width: 100vw;
    min-height: 100vh;
    z-index: 10;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "side"  (side))
    (ui/DIV :id "content" (content))))

(deftag CENTERED
  [_ [] [^:default content] [] []]
  "
  :host {
    display: block;
    height: 100%;
    width: 100%;
  }
  #container {
    display: grid;
    grid-template-columns: 1fr min-content 1fr;
    grid-template-rows: 1fr min-content 1fr;
    justify-items: center;
    align-items: center;
    height: 100%;
    width: 100%;
  }
  #content {
    grid-column: 2;
    grid-row: 2;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "content"
      (content))))
