(ns daggerml.app.ui
  (:require
    [daggerml.ui :refer [defdeftag]]))

(defdeftag deftag
  :skip-ns-parts 2
  :import #{"/css/main.css"})
