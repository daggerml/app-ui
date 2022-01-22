(ns daggerml.app.dml.panel
  (:require
    [daggerml.app.dml.control :as control]
    [daggerml.app.dml.layer :as layer]
    [daggerml.ui :as ui]))

(ui/defstyle login-styles
  "
  form * {
    color: var(--primary-3);
  }

  a {
    outline: none;
  }

  a:hover {
    color: var(--primary-2);
  }

  a:active {
    color: var(--primary-1);
  }

  input {
    outline: none;
    color: var(--primary-3);
    padding: 0.5em;
    margin: 0.5em 0 0.5em 0 !important;
    border: 2px solid var(--primary-3);
    border-radius: 4px;
  }

  input[type='text'], input[type='password'] {
    width: 20em;
  }

  input[type='submit'] {
    background-color: var(--primary-3);
    color: white;
    width: 100%;
  }

  input:focus, a:focus {
    outline: var(--yellow) solid 2px;
    outline-offset: 2px;
  }

  input:disabled {
    color: #666;
    background-color: #eee;
  }

  input:invalid {
    border-color: red;
  }

  input:focus {
    outline: var(--yellow) solid 2px;
    outline-offset: 2px;
  }
  "
  )

(defn LOGIN
  []
  (control/FORM
    :submit #(prn :form (some-> @% (ui/form-data true)))
    (login-styles)
    (layer/LOGIN
      (ui/LABEL
        :slot "email"
        "Email"
        (ui/INPUT
          :type "text"
          :autofocus true
          :name "email"
          :tabindex "1"))
      (ui/LABEL
        :slot "password"
        "Password"
        (ui/INPUT
          :type "password"
          :name "password"))
      (ui/A
        :slot "remember"
        :href "#/forgot"
        "Request a password reset.")
      (ui/INPUT
        :slot "submit"
        :type "submit"
        :value "Go!"))))
