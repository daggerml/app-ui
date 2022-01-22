(ns daggerml.app.dml.nav
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.ui :as ui]))

(deftag BAR
  [_ [] [header center footer] [] []]
  "
  :host {
    display: block;
    height: 100vh;
    --bg-shadow: var(--shadow);
    --bg-color: var(--nav-bg-color);
  }
  #container {
    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    row-gap: 0.5em;
    height: 100%;
    width: 100%;
    z-index: 100;
    box-shadow: 0 0 5px var(--bg-shadow);
    background-color: var(--bg-color);
  }
  #footer {
    align-self: end;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "header" (header))
    (ui/DIV :id "center" (center))
    (ui/DIV :id "footer" (footer))))

