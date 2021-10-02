(ns daggerml.app.dml.layout
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.ui :as ui]))

(deftag MAIN :block
  [[] [side content] _]
  "
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
