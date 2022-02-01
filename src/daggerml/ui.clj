(ns daggerml.ui
  (:require
    [clojure.java.io :as io]
    [clojure.pprint]
    [clojure.string :as string]))

(def ^:private deref*   'daggerml.cells/deref*)
(def ^:private formula  'daggerml.cells/formula)
(def ^:private cell-let 'daggerml.cells/cell-let)

;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- gen-ifn-nonvariadic-arities [f]
  (for [arity (range 1 21),
        :let [args (repeatedly arity gensym)]]
    `([~@args] (~f ~@args))))

(defn- gen-ifn-variadic-arity [f]
  (let [args (repeatedly 22 gensym)]
    `([~@args] (apply ~f ~@args))))

(defn- gen-ifn-invoke [f]
  `(~'-invoke
     ~@(gen-ifn-nonvariadic-arities f)
     ~(gen-ifn-variadic-arity f)))

(defn- any-meta
  [& ks]
  (comp (apply some-fn ks) meta))

(defn- not-meta
  [& ks]
  (complement (apply any-meta ks)))

(defn- make-tag-name
  [skip tag]
  (-> *ns* str (string/split #"\.") (conj (name tag)) (->> (drop skip) (string/join "-"))))

(defn- ->css*
  [x]
  (cond (nil? x)      x
        (string? x)   x
        (number? x)   (str x)
        (keyword? x)  (str (if (namespace x) ":" "") (name x))
        (symbol? x)   (name x)))

(defn- ->css
  [x]
  (-> (fn [xs k v]
        (if (map? v)
          (str xs (->css* k) "{" (->css v) "}\n")
          (str xs (->css* k) ":" (->css* v) ";")))
      (reduce-kv "" x)
      (->> (apply str))))

;; macros ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmacro aget-in
  [obj & ks]
  `(some-> ~obj ~@(map (fn [x] `(cljs.core/aget ~(name x))) ks)))

(defmacro resource-str
  [path]
  (some-> path io/resource slurp))

(defmacro guard
  [& body]
  `(try ~@body (catch js/Error _#)))

(defmacro extend-protocol*
  [protocol [& types] & protocol-methods]
  `(extend-protocol ~protocol
     ~@(mapcat #(into [%] protocol-methods) types)))

(defmacro extend-protocol-ifn
  [type f]
  `(cljs.core/extend-protocol cljs.core/IFn
     ~type
     ~(gen-ifn-invoke f)))

(defmacro extend-type-ifn
  [type f]
  `(cljs.core/extend-type ~type
     cljs.core/IFn
     ~(gen-ifn-invoke f)))

(defmacro specify-ifn!
  [obj f]
  (let [f' (gensym "f")]
    `(let [~f' ~f]
       (cljs.core/specify! ~obj
         cljs.core/IFn
         ~(gen-ifn-invoke f')))))

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

(defmacro defstyle
  [name style-body]
  `(def ~name (define-style-template ~style-body)))

(defmacro deftag
  {:arglists '([tag doc? opts? [this [& props] [& slots] [& callbacks] [& methods]] style? & body])}
  [tag & [doc? & more :as xs]]
  (let [[doc [opts? & more :as xs]]                 (if (string? doc?)      [[doc?] more]   [[] xs])
        [opts [bindings & [style? & more :as xs]]]  (if (map? opts?)        [opts? more]    [{} xs])
        [style body]                                (cond (string? style?)  [[style?] more]
                                                          (map? style?)     [[(->css style?)] more]
                                                          :else             [[] xs])
        [this [& props] [& slots] [& callbacks] [& methods]] bindings
        default-opts    {:skip-ns-parts 0 :css-imports #{} :style-templates #{}}
        opts            (merge default-opts (:daggerml.ui/options (meta tag)) opts)
        tag-name        (make-tag-name (:skip-ns-parts opts) tag)
        css-imports     (mapv #(format "@import url(%s);" %) (:css-imports opts))
        style-templates (mapv list (:style-templates opts))
        style-body      (string/join "\n" (concat css-imports style))
        template-sym    (gensym (str tag-name "-style"))
        hook-sym        (gensym "hooks")
        prop-names      (map name props)
        attr-names      (->> props (filter (any-meta :attr :form)) (map name))
        slot-names      (->> slots (filter (not-meta :default)) (map name))
        callback-names  (map name callbacks)
        method-names    (map name methods)
        form-value      (some-> (filter (any-meta :form) props) first name)
        dfl-slot-name   (some-> (filter (any-meta :default) slots) first name)
        hook-bind       (fn [hooks k] (fn [sym] [sym `(aget-in ~hooks ~(name k) ~(name sym))]))]
    `(do (defstyle ~template-sym ~style-body)
         (def ~tag
           ~@doc
           (custom-element
             :tag           ~tag-name
             :attrs         [~@attr-names]
             :props         [~@prop-names]
             :callbacks     [~@callback-names]
             :methods       [~@method-names]
             :form-value    ~form-value
             :named-slots   [~@slot-names]
             :default-slot  ~dfl-slot-name
             :render        (fn [~this ~hook-sym]
                              (let [~@(mapcat (hook-bind hook-sym "props") props)
                                    ~@(mapcat (hook-bind hook-sym "slots") slots)
                                    ~@(mapcat (hook-bind hook-sym "callbacks") callbacks)
                                    ~@(mapcat (hook-bind hook-sym "methods") methods)]
                                (SHADOW-ROOT ~@style-templates (~template-sym) ~@body))))))))

(defn emit-deftag
  [options [tag & args]]
  `(deftag ~(vary-meta tag assoc :daggerml.ui/options options) ~@args))

(defmacro defdeftag
  "Defines a macro which calls daggerml.ui/deftag with the given options."
  {:arglists '([name doc? options?])}
  [name & [doc? & more :as xs]]
  (let [[doc [options]] (if (string? doc?) [doc? more] [nil xs])
        {doc' :doc :keys [arglists]} (meta #'deftag)]
    `(defmacro ~name
       ~@(or doc doc')
       {:arglists '~arglists}
       [~'& args#]
       (emit-deftag ~options args#))))

