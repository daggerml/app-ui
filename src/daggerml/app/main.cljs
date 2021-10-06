(ns daggerml.app.main
  (:require
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.layer :as layer]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.dml.nav :as nav]
    [daggerml.app.dml.nav.icon :as nav-icon]
    [daggerml.ui :as ui]))

(defn -main
  []
  (ui/prevent-default-form-submit!)
  (r/start!)
  (ui/BODY
    (layout/MAIN :id "main-layout"
      (nav/BAR :id "main-nav" :slot "side"
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
        #_(layer/LOGIN :id "login-layer")))))
