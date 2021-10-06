(ns daggerml.app.dml.layer
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :refer [cell cell=]]
    [daggerml.ui :as ui]))

(deftag MAIN :block
  [[] [^:default content] _]
  "
  #container {
    --size1: var(--design--grid-size);
    --size2: calc(var(--size1) / 10);
    --size3: calc(var(--size1) - 2px);
    min-height: 100vh;
    width: 100vw;
    background:
      linear-gradient(-90deg, rgba(0,0,0,.05) 1px, transparent 1px),
      linear-gradient(rgba(0,0,0,.05) 1px, transparent 1px),
      linear-gradient(-90deg, rgba(0, 0, 0, .04) 1px, transparent 1px),
      linear-gradient(rgba(0,0,0,.04) 1px, transparent 1px),
      linear-gradient(transparent 3px, var(--design--bg) 3px, var(--design--bg) var(--size3), transparent var(--size3)),
      linear-gradient(-90deg, #aaa 1px, transparent 1px),
      linear-gradient(-90deg, transparent 3px, var(--design--bg) 3px, var(--design--bg) var(--size3), transparent var(--size3)),
      linear-gradient(#aaa 1px, transparent 1px),
      var(--design--bg);
    background-size:
      var(--size2) var(--size2),
      var(--size2) var(--size2),
      var(--size1) var(--size1),
      var(--size1) var(--size1),
      var(--size1) var(--size1),
      var(--size1) var(--size1),
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
    min-height: 100vh;
    width: 100vw;
    z-index: 1;
  }
  "
  (ui/DIV :id "container"
    (ui/DIV :id "watermark" "DAGGERML")
    (ui/DIV :id "content" (content))))

(deftag LOGIN :block
  [[] [] _]
  "
  #container {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    grid-template-rows: 1fr auto 1fr;
    justify-items: center;
    align-items: center;
    height: 100%;
    width: 100%;
  }
  #form {
    grid-column: 2;
    grid-row: 2;
  }
  "
  (let [c (cell "asdf")]
    (cell= (prn :c @c))
    (ui/DIV :id "container"
      (ui/DIV :id "form"
        (ui/FORM
          (ui/LABEL "Email" (ui/INPUT :type "test" :bind ['value :keyup c]))
          (ui/BR)
          (ui/LABEL "Password" (ui/INPUT :type "password")))))))
