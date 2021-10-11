(ns daggerml.app.dml.control
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :refer [cell=]]
    [daggerml.ui :as ui]))

(defn FORM
  [& args]
  (doto (apply ui/FORM args)
    (ui/on! :submit #(.preventDefault %))))

(deftag INPUT
  [this [type autofocus ^:form value] [^:default label] [connected disabled] [set-error]]
  "
  :host {
    outline: none;
  }
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
  input:disabled {
    color: #666;
    background-color: #eee;
  }
  input:invalid {
    border-color: red;
  }
  "
  (let [submit!       #(some-> this .-form .requestSubmit)
        enter-submit! #(when (= (.-key %) "Enter") (submit!))]
    (ui/case= type
      "submit"
      (ui/INPUT
        :type       type
        :disabled   disabled
        :click      submit!)
      "checkbox"
      (ui/LABEL
        (ui/INPUT
          :type     type
          :disabled disabled
          :keyup    enter-submit!)
        (label))
      (ui/LABEL (label)
        (ui/INPUT
          :type     type
          :disabled disabled
          :autofocus true
          :bind     ['value :keyup value]
          :keyup    enter-submit!
          :focus    (cell= (-> (and @autofocus @connected))))))))

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
