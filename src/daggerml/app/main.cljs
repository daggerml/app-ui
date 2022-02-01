(ns daggerml.app.main
  (:require
    ["element-internals-polyfill"]
    ["webfontloader" :as wfl]
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.layer :as layer]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.dml.nav :as nav]
    [daggerml.app.dml.nav.icon :as nav-icon]
    [daggerml.app.dml.panel :as panel]
    [daggerml.cells :as c :refer [cell=]]
    [daggerml.ui :as ui]
    [daggerml.ui.attributes]))

(defn ^:dev/before-load before-load [] (.reload js/location))
(wfl/load (clj->js {:custom {:families ["VT323" "Material Icons"]}}))

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
          ::r/home (panel/LOGIN)
          ::r/dags (layout/HBOX-2
                     :style "--col1-width: 300px; --gap:0;min-height:100%;"
                     (ui/DIV
                       :style "background-color:#aaa;min-height:100%;"
                       :slot "col1"
                       "left")
                     (ui/DIV
                       :style "background-color:#ccc;min-height:100%;"
                       :slot "col2"
                       (doall (repeatedly 10 #(ui/DIV "right")))))
          nil)))))
