(ns daggerml.cells
  (:require [clojure.walk :as walk]))

(defn- get-derefs
  [expr]
  (let [derefs (atom #{})
        deref? #(and (seq? %) (= `deref (first %)) (symbol? (second %)))]
    (walk/prewalk (fn [x] (when (deref? x) (swap! derefs conj (second x))) x) expr)
    @derefs))

(defmacro cell=
  [expr & [setter]]
  (let [srcs (get-derefs (walk/macroexpand-all expr))]
    `(formula [~@srcs] (fn [] ~expr) ~setter)))

(defmacro watch=
  [c & body]
  `(do-watch ~c (fn [_# _#] ~@body)))

(defmacro defc
  ([name state]
   `(def ~name (cell ~state)))
  ([name doc state]
   `(def ~name ~doc (cell ~state))))

(defmacro defc=
  ([name expr]
   `(def ~name (cell= ~expr)))
  ([name doc-or-expr expr-or-setter]
   (if (string? doc-or-expr)
     `(def ~name ~doc-or-expr (cell= ~expr-or-setter))
     `(def ~name (cell= ~doc-or-expr ~expr-or-setter))))
  ([name doc expr setter]
   `(def ~name ~doc (cell= ~expr ~setter))))
