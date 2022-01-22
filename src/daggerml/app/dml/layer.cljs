(ns daggerml.app.dml.layer
  (:require
    [daggerml.app.dml.control :as control]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :refer [cell cell=]]
    [daggerml.ui :as ui]))

(deftag MAIN
  [_ [] [^:default content] [] []]
  "
  :host {
    display: block;
    height: 100vh;
    width: 100vw;
  }
  #container {
    --size1: var(--design-grid-size);
    --size2: calc(var(--size1) / 5);
    --size3: calc(var(--size1) - 2px);
    min-height: 100vh;
    padding-left: 56px;
    width: 100vw;
    background:
      linear-gradient(-90deg, rgba(215,229,204,0.5) 1px, transparent 1px),
      linear-gradient(rgba(215,229,204,0.5) 1px, transparent 1px),
      linear-gradient(-90deg, rgba(0,0,0,.04) 1px, transparent 1px),
      linear-gradient(rgba(0,0,0,.04) 1px, transparent 1px),
      #eaf4dc;
    background-size:
      var(--size2) var(--size2),
      var(--size2) var(--size2),
      var(--size1) var(--size1),
      var(--size1) var(--size1);
  }
  #watermark {
    position: absolute;
    top: 110px;
    left: 0;
    width: 100%;
    font-family: 'VT323', monospace;
    font-size: 220px;
    text-align: center;
    color: rgba(0, 0, 0, 0.05);
  }
  #content {
    position: absolute;
    top: 0;
    left: 0;
    min-height: 100%;
    width: 100%;
    z-index: 1;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "watermark" "DAGGERML")
    (ui/DIV :id "content" (content))))

(deftag LOGIN
  [_ [] [email password remember submit] [] []]
  "
  :host {
    display: block;
    height: 100vh;
    width: 100vw;
    --color: var(--primary-3);
  }
  ::slotted(*) {
  }
  "
  (layout/CENTERED
    (layout/PANEL
      (ui/B :slot "title" "Login")
      (layout/FORM-BODY :slot "content"
        (email :slot "controls")
        (password :slot "controls")
        (remember :slot "controls")
        (submit :slot "buttons")))))
