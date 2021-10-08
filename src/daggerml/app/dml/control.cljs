(ns daggerml.app.dml.control
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :refer [cell=]]
    [daggerml.ui :as ui]))

(deftag INPUT
  [[label type autofocus tabindex state] [] connected?]
  "
  label {
    color: var(--blue-2);
  }
  input {
    outline: none;
    color: var(--blue-2);
    padding: 0.5em;
    margin: 0.5em 0 0.5em 0;
    border: 2px solid var(--blue-2);
    border-radius: 4px;
  }
  input[type='text'], input[type='password'] {
    width: 20em;
  }
  input[type='submit'] {
    background-color: var(--blue-2);
    color: white;
    width: 100%;
  }
  input:focus {
    outline: var(--yellow) solid 2px;
    outline-offset: 2px;
  }
  "
  (ui/case= type
    "submit"
    (ui/INPUT
      :type     type
      :tabindex tabindex)
    "checkbox"
    (ui/LABEL
      (ui/INPUT
        :type     type
        :tabindex tabindex)
      label)
    (ui/LABEL label
      (ui/INPUT
        :type     type
        :tabindex tabindex
        :bind     ['value :keyup state]
        :focus    (cell= (-> (and @autofocus @connected?) (doto prn)))))))

(defn TEXT
  [& attrs]
  (apply INPUT 'type "text" attrs))

(defn PASSWORD
  [& attrs]
  (apply INPUT 'type "password" attrs))

(defn CHECKBOX
  [& attrs]
  (apply INPUT 'type "checkbox" attrs))

(defn SUBMIT
  [& attrs]
  (apply INPUT 'type "submit" attrs))
