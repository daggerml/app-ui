(ns daggerml.app.db.routes
  (:require
    [daggerml.cells :as c]
    [reitit.core :as r]
    [reitit.frontend :as rf]
    [reitit.frontend.easy :as rfe]))

(def routes
  [["/analytics"    ::anal]
   ["/dag"          ::dags]
   ["/dag/{id}"     ::dag]
   ["/dashboard"    ::dash]
   ["/home"         ::home]
   ["/permissions"  ::perm]
   ["/preferences"  ::pref]
   ["/support"      ::supp]])

(def route
  (c/cell nil))

;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(def ^:private router
  (rf/router routes {:syntax :bracket}))

(defn- match->route
  [{{:keys [name]} :data :keys [path path-params query-params]}]
  {:name          name
   :path          path
   :params        (merge {} query-params path-params)
   :path-params   path-params
   :query-params  query-params})

(defn- set-route!
  [match history]
  (reset! route (-> (match->route match) (assoc :history history))))

;; api ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn start!
  []
  (rfe/start! router set-route! {}))

(defn href
  ([name]
   (href name {}))
  ([name path-params]
   (href name path-params {}))
  ([name path-params query-params]
   (str "#" (-> (r/match-by-name router name path-params)
                (r/match->path query-params)))))
