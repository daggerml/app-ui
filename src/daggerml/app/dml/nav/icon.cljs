(ns daggerml.app.dml.nav.icon
  (:require
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.typography :as typo]
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :as c :refer [cell=]]
    [daggerml.ui :as ui]))

(deftag BASE
  [_ [title route icon theme] [] [] []]
  "
  :host { display: block; }
  a {
    display: block;
    width: 100%;
    padding: 0.5em 1em;
    color: white;
    transition: background 0.5s, border 0.5s;
  }
  a:focus         { outline: 0; }
  a:active        { transition: background-color 0s; }
  a.norm, a.norm.selected:hover, a.norm.selected:active {
    background-color: var(--nav--bg-norm);
  }
  a.home          { background-color: var(--nav--bg-home); }
  a.norm:hover    { background-color: var(--nav--bg-norm--hover); }
  a.norm:active   { background-color: var(--nav--bg-norm--active); }
  a.home:hover    { background-color: var(--nav--bg-home--hover); }
  a.home:active   { background-color: var(--nav--bg-home--active); }
  a.norm.selected { box-shadow: inset 0 0 15px black; }
  "
  (ui/A
    :tabindex "-1"
    :href     (cell= (r/href @route))
    :class    (cell= {(or @theme :norm) true :selected (= @route (:name @r/route))})
    (ui/B (typo/ICON 'title title 'icon icon))))

(defn- icon
  ([route title icon-name]
   (icon route title icon-name nil))
  ([route title icon-name theme]
   (BASE 'route route 'title title 'icon icon-name 'theme theme)))

(defn LOGOUT
  []
  (BASE
    'route ::none
    'title "logout"
    'icon "logout"
    :click #(do (prn :logged-out) (.preventDefault %))))

(deftag HOME        [_ [] [] [] []] (icon ::r/home "home"        "home"                "home"))
(deftag DASHBOARDS  [_ [] [] [] []] (icon ::r/dash "dashboards"  "dashboard"))
(deftag DAGS        [_ [] [] [] []] (icon ::r/dags "DAGs"        "account_tree"))
(deftag ANALYTICS   [_ [] [] [] []] (icon ::r/anal "analytics"   "area_chart"))
(deftag PERMISSIONS [_ [] [] [] []] (icon ::r/perm "permissions" "admin_panel_settings"))
(deftag PREFERENCES [_ [] [] [] []] (icon ::r/pref "preferences" "settings"))
(deftag SUPPORT     [_ [] [] [] []] (icon ::r/supp "support"     "contact_support"))
