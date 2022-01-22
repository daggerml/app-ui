(ns daggerml.app.dml.nav.icon
  (:require
    [daggerml.app.db.routes :as r]
    [daggerml.app.dml.typography :as typo]
    [daggerml.app.ui :refer [deftag]]
    [daggerml.cells :as c :refer [cell=]]
    [daggerml.ui :as ui]))

(deftag ICON
  [_ [title route icon] [] [] []]
  "
  :host {
    display:      block;
    --fg-color:   white;
    --bg-shadow:  black;
    --bg-color:   var(--nav-bg-color);
    --bg-hover:   var(--nav-bg-hover);
    --bg-active:  var(--nav-bg-active);
  }
  a {
    display: block;
    width: 100%;
    padding: 0.5em 1em;
    color: var(--fg-color);
    transition: background 0.25s ease-in-out;
  }
  a:focus           { outline: 0; }
  a:active          { transition: background-color 0.1s ease-in-out; }
  a,
  a.selected:hover,
  a.selected:active { background-color: var(--bg-color); }
  a:hover           { background-color: var(--bg-hover); }
  a:active          { background-color: var(--bg-active); }
  a.selected        { box-shadow: inset 0 0 15px var(--bg-shadow); }
  "
  (ui/A
    :tabindex "-1"
    :href     (cell= (r/href @route))
    :class    (cell= {:selected (= @route (:name @r/route))})
    (ui/B (typo/ICON 'title title 'icon icon))))

(deftag HOME
  [_ [] [] [] []]
  "
  * {
    --bg-shadow:  transparent;
    --bg-color:   var(--nav-home-color);
    --bg-hover:   var(--nav-home-hover);
    --bg-active:  var(--nav-home-active);
  }
  "
  (ICON 'route ::r/home 'title "home" 'icon "home"))

(deftag LOGOUT
  [_ [] [] [] []]
  (ICON
    'route ::none
    'title "logout"
    'icon "logout"
    :click #(do (prn :logged-out) (.preventDefault %))))

(defn- icon
  [route title icon-name]
  (ICON 'route route 'title title 'icon icon-name))

(deftag DASHBOARDS  [_ [] [] [] []] (icon ::r/dash "dashboards"  "dashboard"))
(deftag DAGS        [_ [] [] [] []] (icon ::r/dags "DAGs"        "account_tree"))
(deftag ANALYTICS   [_ [] [] [] []] (icon ::r/anal "analytics"   "area_chart"))
(deftag PERMISSIONS [_ [] [] [] []] (icon ::r/perm "permissions" "admin_panel_settings"))
(deftag PREFERENCES [_ [] [] [] []] (icon ::r/pref "preferences" "settings"))
(deftag SUPPORT     [_ [] [] [] []] (icon ::r/supp "support"     "contact_support"))
