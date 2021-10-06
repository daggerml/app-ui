(ns daggerml.app.dml.typography
  (:require
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :as c :refer [cell=]]
    [daggerml.ui :refer [SPAN]]))

(deftag ICON
  [[title icon] [] _]
  (SPAN
    :class "material-icons"
    :title title
    (cell= (some-> @icon name))))
