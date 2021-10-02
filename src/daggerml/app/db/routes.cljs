(ns daggerml.app.db.routes
  (:require
    [daggerml.cells :as c]
    [reitit.core :as r]
    [reitit.frontend :as rf]
    [reitit.frontend.easy :as rfe]))

(def route
  (c/cell nil))

(def routes
  [["/home"       ::home]
   ["/dag"        ::dags]
   ["/dag/{id}"   ::dag]])

(def router
  (rf/router routes {:syntax :bracket}))

(defn match-by-path
  [& xs]
  (apply r/match-by-path router xs))

(defn match-by-name
  [& xs]
  (apply r/match-by-name router xs))

(defn href
  ([name]
   (href name {}))
  ([name path-params]
   (href name path-params {}))
  ([name path-params query-params]
   (-> (match-by-name name path-params) (r/match->path query-params))))

(defn match->route
  [{{:keys [name]} :data :keys [path path-params query-params]}]
  {:name          name
   :path          path
   :params        (merge {} query-params path-params)
   :path-params   path-params
   :query-params  query-params})

(defn set-route!
  [match history]
  (reset! route (-> (match->route match) (assoc :history history))))

(defn start
  []
  (rfe/start! router set-route! {}))
