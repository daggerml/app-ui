(ns daggerml.app.dml.layout
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :refer [cell=]]
    [daggerml.ui :as ui :refer [when=]]))

(deftag MAIN
  [_ [] [side content] [] []]
  "
  :host { display: block; }
  #container {
  }
  #side {
    position: fixed;
    height: 100vh;
    width: var(--main-layout-side-width);
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

(deftag VBOX
  [_ [] [^:default content] [] []]
  "
  :host {
    display: block;
    --gap: 0.5em;
    --padding: 1em;
  }
  #container {
    display: grid;
    grid-template-columns: 1fr;
    grid-gap: var(--gap);
    padding: var(--padding);
    padding-bottom: var(--gap);
  }
  "
  (ui/DIV :id "container" (content)))

(deftag PANEL
  [this [] [title content] [] []]
  "
  :host {
    --padding: 1em;
    --fg-color: var(--primary-3);
    --bg-color: white;
  }
  #container {
    background-color: var(--bg-color);
    border: 4px solid var(--fg-color);
    border-radius: 6px;
  }
  #title {
    padding: var(--padding);
    color: var(--bg-color);
    background-color: var(--fg-color);
  } 
  #content {
    padding-top: calc(var(--padding) / 2);
  }
  "
  (let [title-hidden? (cell= (not (seq @title)))]
    (ui/DIV :id "container"
      (ui/DIV :id "title" :hidden title-hidden? (title))
      (ui/DIV :id "content" (content)))))

(deftag FORM-BODY
  [this [] [controls buttons] [] []]
  "
  :host {
    --fg-color: var(--primary-3);
  }
  hr {
    margin-top: 1em;
    margin-bottom: 0;
    border: 1px solid var(--fg-color);
    width: 100%;
  }
  "
  (VBOX
    (controls)
    (ui/HR)
    (buttons)))
