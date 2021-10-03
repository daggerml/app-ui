(ns daggerml.app.dml.nav
  (:require
    [daggerml.app.dml.typography :as typo]
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :as cell :refer [cell=]]
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

(deftag ICON :block
  [[^:attr title ^:attr href ^:attr icon ^:attr theme] [] _]
  "
  a {
    display: block;
    width: 100%;
    padding: 0.5em 1em;
    color: white;
    transition: background 0.5s, border 0.5s;
  }
  a:focus         { outline: 0; }
  a:active        { transition: background-color 0s; }
  a.norm          { background-color: var(--nav--bg-norm); }
  a.home          { background-color: var(--nav--bg-home); }
  a.norm:hover    { background-color: var(--nav--bg-norm--hover); }
  a.norm:active   { background-color: var(--nav--bg-norm--active); }
  a.home:hover    { background-color: var(--nav--bg-home--hover); }
  a.home:active   { background-color: var(--nav--bg-home--active); }
  "
  (ui/A
   :href href
   :class (cell= (or @theme "norm"))
   (ui/B (typo/ICON :title title :icon icon))))
