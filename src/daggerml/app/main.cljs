(ns daggerml.app.main
  (:require
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.layer :as layer]
    [daggerml.app.dml.layout :as layout]
    [daggerml.app.dml.nav :as nav]
    [daggerml.ui :as ui]))

(defn -main
  []
  (ui/prevent-default-form-submit!)
  (r/start!)
  (ui/BODY
    (layout/MAIN :id "main-layout"
      (nav/BAR :id "main-nav" :slot "side"
        (ui/DIV :slot "header"
          (nav/ICON :href (r/href ::r/home) :title "home" :icon "home" :theme "home"))
        (ui/DIV :slot "center"
          (nav/ICON :href (r/href ::r/dash) :title "dashboards" :icon "dashboard")
          (nav/ICON :href (r/href ::r/dags) :title "DAGs" :icon "account_tree")
          (nav/ICON :href (r/href ::r/anal) :title "analytics" :icon "area_chart")
          (nav/ICON :href (r/href ::r/perm) :title "permissions" :icon "admin_panel_settings"))
        (ui/DIV :slot "footer"
          (nav/ICON :href "#" :title "logout" :icon "logout")
          (nav/ICON :href (r/href ::r/pref) :title "preferences" :icon "settings")
          (nav/ICON :href (r/href ::r/supp) :title "support" :icon "contact_support")))
      (layer/MAIN :slot "content"
        #_(layer/LOGIN :id "login-layer")))))
