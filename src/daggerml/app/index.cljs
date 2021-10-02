(ns daggerml.app.index
  (:require
    [daggerml.app.db.routes :as routes]
    [daggerml.app.dml.layer :as layer]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.dml.nav :as nav]
    [daggerml.cells :as c]
    [daggerml.ui :as ui]))

(defn -main
  []
  (ui/prevent-default-form-submission)
  (routes/start)
  (ui/BODY
    (layout/MAIN :id "main-layout"
      (nav/BAR :id "main-nav" :slot "side"
        (ui/DIV :slot "header"
          (nav/ICON :theme "home" :href "#" :title "home" :icon "home"))
        (ui/DIV :slot "center"
          (nav/ICON :href "#" :title "dashboards"   :icon "dashboard")
          (nav/ICON :href "#" :title "DAGs"         :icon "account_tree")
          (nav/ICON :href "#" :title "analytics"    :icon "area_chart")
          (nav/ICON :href "#" :title "users"        :icon "admin_panel_settings"))
        (ui/DIV :slot "footer"
          (nav/ICON :href "#" :title "logout"       :icon "logout")
          (nav/ICON :href "#" :title "preferences"  :icon "settings")
          (nav/ICON :href "#" :title "help"         :icon "help")))
      (layer/MAIN :slot "content"
        (layer/LOGIN :id "login-layer")))))
