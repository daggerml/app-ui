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
    --size1: var(--design--grid-size);
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
  [_ [] [] [] []]
  "
  :host {
    display: block;
    height: 100vh;
    width: 100vw;
  }
  #container {
  }
  #form {
    background-color: white;
    border: 4px solid var(--blue-2);
    border-radius: 6px;
  }
  #form #title {
    padding: 1em;
    background-color: var(--blue-2);
    color: white;
  }
  hr {
    border: 1px solid var(--blue-2);
    width: 100%;
    margin-bottom: 0.5em;
  }
  form {
    display: grid;
    grid-template-columns: 1fr;
    grid-gap: 0.5em;
    padding: 1em;
    padding-bottom: 0.5em;
  }
  dml-control-input:invalid,
  dml-control-input[internals-invalid] {
    --blue-2: red;
  }
  "
  (let [dfl       (cell= {:email "user@example.com"})
        email     (cell nil)
        password  (cell nil)
        data      (cell= {:email @email :password @password})
        errors    (cell (cycle [nil "uh oh"]))
        error     (cell= (first @errors))]
    (ui/with-interval 1000 (swap! errors next))
    (layout/CENTERED :id "container"
      (ui/DIV :id "form"
        (ui/DIV :id "title"
          (ui/B "Login"))
        (control/FORM
          :submit #(do (js/console.log
                         "form:" (js/Object.fromEntries (js/FormData. @%)))
                       (.reset @%))
          (control/TEXT
            'autofocus true
            :error error
            :name "email"
            :value (cell= (:email @dfl))
            :tabindex "1"
            :bind ['value :keyup email]
            "Email")
          (control/PASSWORD
            :name "password"
            :value (cell= (:password @dfl))
            :bind ['value :keyup password]
            "Password")
          (control/CHECKBOX
            :name "remember"
            " remember me on this device")
          (ui/HR)
          (control/SUBMIT))))))
