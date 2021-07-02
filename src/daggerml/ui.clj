(ns daggerml.ui
  (:require
    [clojure.string :as string]))

(def ^:private deref*   'daggerml.cells/deref*)
(def ^:private formula  'daggerml.cells/formula)
(def ^:private cell-let 'daggerml.cells/cell-let)

(defmacro extend-protocol*
  [protocol [& types] & protocol-methods]
  `(extend-protocol ~protocol
     ~@(mapcat #(into [%] protocol-methods) types)))

(defmacro with-let
  [[name value & bindings] & body]
  `(let [v# ~value, ~name v#, ~@bindings] ~@body v#))

(defmacro with-timeout
  [ms & body]
  `(js/setTimeout (fn [] ~@body) ~ms))

(defmacro with-interval
  [ms & body]
  `(js/setInterval (fn [] ~@body) ~ms))

(defmacro for=
  [[bindings items] body]
  `(loop-tpl*
     ~items
     (fn [item#] (~cell-let [~bindings item#] ~body))))

(defmacro if=
  [predicate consequent & [alternative]]
  `(let [prd# ~predicate
         con# (delay ~consequent)
         alt# (delay ~alternative)]
     (~formula [prd#] #(force (if (~deref* prd#) con# alt#)))))

(defmacro when=
  [predicate & body]
  `(if= ~predicate (do ~@body)))

(defmacro cond=
  [& clauses]
  (assert (even? (count clauses)))
  (let [[conds tpls] (apply map vector (partition 2 clauses))
        cond-syms (repeatedly (count conds) gensym)
        tpl-syms  (repeatedly (count tpls) gensym)
        conds'    (map (fn [x] `(~deref* ~x)) cond-syms)
        tpls'     (map (fn [x] `(delay ~x)) tpls)]
    `(let [~@(interleave cond-syms conds)
           ~@(interleave tpl-syms tpls')]
       (~formula [~@cond-syms] #(force (cond ~@(interleave conds' tpl-syms)))))))

(defmacro case=
  [expr & clauses]
  (let [[cases tpls] (apply map vector (partition 2 clauses))
        default   (when (odd? (count clauses)) (last clauses))
        tpls      (conj (vec tpls) default)
        expr-sym  (gensym)
        tpl-syms  (repeatedly (count tpls) gensym)
        expr'     `(~deref* ~expr-sym)
        tpls'     (mapv (fn [x] `(delay ~x)) tpls)]
    `(let [~expr-sym ~expr
           ~@(interleave tpl-syms tpls')]
       (~formula
         [~expr-sym]
         #(force (case ~expr' ~@(interleave cases tpl-syms) ~(last tpl-syms)))))))

(defmacro defnative-element-factories
  [& tags]
  `(do ~@(map (fn [tag] `(def ~tag (element-factory ~(.toLowerCase (name tag))))) tags)))

(defmacro deftemplate
  [name inner-html]
  `(def ~name (define-template ~inner-html)))

(defmacro deftag
  "Defines a custom element named <tag> and a constructor function of the same
   name. The <props> and <slots> arguments are bound to cells which update the
   element's properties and slots bi-directionally. The <connected> argument is
   bound to a cell indicating the element's connected/disconnected state. The
   <props> may have ^:attr meta, in which case the property will be synced with
   an attribute of the same name, bi-directionally."
  {:arglists '([tag doc? config? [[& props] [& slots] connected] & body])}
  [tag & [maybe-doc & more :as args]]
  (let [doc           (if (string? maybe-doc) [maybe-doc] [])
        [[[& props] [& slots] connected] & body] (if (seq doc) more args)
        tag-name      (name tag)
        prop-names    (map name props)
        attr-names    (keep #(when (:attr (meta %)) (name %)) props)
        slot-names    (keep #(when (not (:default (meta %))) (name %)) slots)
        dfl-slot-name (first (keep #(when (:default (meta %)) (name %)) slots))
        this-sym      (gensym "this")
        aget          'cljs.core/aget
        prop-bind     (fn [x] [x (list aget (list aget this-sym "_props") (name x))])
        slot-bind     (fn [x] [x (list aget (list aget this-sym "_slots") (name x))])]
    `(def ~tag
       ~@doc
       (custom-element*
         ~tag-name
         [~@prop-names]
         [~@attr-names]
         [~@slot-names]
         ~dfl-slot-name
         (fn [~this-sym]
           (binding [*custom-element* ~this-sym]
             (let [~@(mapcat prop-bind props)
                   ~@(mapcat slot-bind slots)
                   ~connected (~aget ~this-sym "_connected")]
               ~@body)))))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; css ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmacro defstyles
  [& kvs]
  `(swap! styles merge ~(into {} (map vec (partition 2 kvs)))))
