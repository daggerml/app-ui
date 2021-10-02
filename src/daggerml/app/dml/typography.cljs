(ns daggerml.app.dml.typography
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.ui :refer [SPAN]]))

(deftag ICON
  [[^:attr title ^:attr icon] [] _]
  (SPAN :class "material-icons" :title title icon))
