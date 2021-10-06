(ns daggerml.app.dml.nav
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.ui :as ui]))

(deftag BAR :block
  [[] [header center footer] _]
  "
  #container {
    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    row-gap: 0.5em;
    height: 100%;
    width: 100%;
    z-index: 100;
    box-shadow: 0 0 5px var(--shadow);
    background-color: var(--nav--bg-norm);
  }
  #footer {
    align-self: end;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "header" (header))
    (ui/DIV :id "center" (center))
    (ui/DIV :id "footer" (footer))))

