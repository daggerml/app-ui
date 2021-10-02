(ns hooks.ui
  (:require
    [clj-kondo.hooks-api :as api]))

;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- sexpr->node
  [x]
  (cond (vector? x)   (api/vector-node (mapv sexpr->node x))
        (seq? x)      (api/list-node (map sexpr->node x))
        (keyword? x)  (api/keyword-node x)
        (string? x)   (api/string-node x)
        :else         (api/token-node x)))

(defn- defn-dom
  [tag & body]
  (list* 'defn tag ['& (gensym)] (seq body)))

;; hooks ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn specify!
  [{:keys [node]}]
  (let [[_ _ & args] (api/sexpr node)]
    {:node (sexpr->node (list* 'reify args))}))

(defn deftag
  [{:keys [node]}]
  (let [[_ tag & [display & more :as args]] (api/sexpr node)
        [_display [bindings & [s & _ :as args]]]
        (if (keyword? display) [display more] [nil args])
        [_style render] (if (string? s) args (cons nil args))]
    {:node (sexpr->node (defn-dom tag bindings render))}))

(defn defdeftag
  [{:keys [node]}]
  (let [[_ sym] (api/sexpr node)]
    {:node (sexpr->node (list 'def sym nil))}))

(defn defnative-element-factories
  [{:keys [node]}]
  (let [[_ & tags] (api/sexpr node)]
    {:node (sexpr->node (list* 'do ['defnative-element-factories] (map defn-dom tags)))}))

(defn extend-protocol*
  [{:keys [node]}]
  (let [[_ proto types & impls] (api/sexpr node)]
    {:node (sexpr->node (list* 'extend-protocol proto (mapcat #(into [%] impls) types)))}))
