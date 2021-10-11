(ns daggerml.app.main
  (:require
    ["webfontloader" :as wfl]
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.layer :as layer]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.dml.nav :as nav]
    [daggerml.app.dml.nav.icon :as nav-icon]
    [daggerml.cells :as c :refer [cell=]]
    [daggerml.ui :as ui]))

(wfl/load
  (clj->js {:custom {:families ["VT323" "Material Icons"]}}))

(defn -main
  []
  (r/start!)
  (ui/BODY
    (layout/MAIN
      (nav/BAR :slot "side"
        (ui/DIV :slot "header"
          (nav-icon/HOME))
        (ui/DIV :slot "center"
          (nav-icon/DASHBOARDS)
          (nav-icon/DAGS)
          (nav-icon/ANALYTICS)
          (nav-icon/PERMISSIONS))
        (ui/DIV :slot "footer"
          (nav-icon/LOGOUT)
          (nav-icon/PREFERENCES)
          (nav-icon/SUPPORT)))
      (layer/MAIN :slot "content"
        (ui/case= (cell= (:name @r/route))
          ::r/home (layer/LOGIN)
          nil)))))
