(ns daggerml.ui.attributes
  (:require
    [daggerml.ui :as ui :refer [do! on! bind guard with-timeout]]
    [goog.dom.classlist :as domcl]
    [goog.events :as events]))

;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- normalize-class
  [x]
  (cond (map? x)    (reduce-kv #(assoc %1 (name %2) %3) {} x)
        (seq? x)    (zipmap (map name x) (repeat true))
        (string? x) (zipmap (.split x #"\s+") (repeat true))
        :else       {}))

;; do! methods ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmethod do! :class
  [e _ v v']
  (let [p (normalize-class v)
        q (normalize-class v')]
    (doseq [k (reduce into #{} (map keys [p q]))]
      (domcl/enable e k (boolean (q k))))))

(defmethod do! :focus
  [e _ _ v']
  (when v' (with-timeout 0 (guard (doto e .focus .select)))))

(defmethod do! :error
  [e _ _ v']
  (guard (.setError ^js e v')))

(defmethod do! :bind
  [e _ _ [k' e' c']]
  (bind e k' e' c'))
