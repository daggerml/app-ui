(ns daggerml.ui
  (:require
    [clojure.string :as string]))

(def ^:private deref*   'daggerml.cells/deref*)
(def ^:private formula  'daggerml.cells/formula)
(def ^:private cell-let 'daggerml.cells/cell-let)

;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- any-meta
  [& ks]
  (comp (apply some-fn ks) meta))

(defn- not-meta
  [& ks]
  (complement (apply any-meta ks)))

(defn- wrap-html
  [tag content]
  (format "<%s>\n%s\n</%s>" (name tag) content (name tag)))

;; macros ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmacro guard
  [& body]
  `(try ~@body (catch js/Error _#)))

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

(defmacro deftag*
  [tag
   [this [& props] [& slots] [& callbacks] [& methods]]
   & {:keys [import doc opts prefix style render]}]
  (let [doc             (if doc [doc] [])
        style           (if style [style] [])
        css-imports     (mapv #(format "@import url(%s);" %) import)
        css-defaults    []
        style-body      (string/join "\n" (concat css-imports css-defaults style))
        tag-name        (str (when prefix (str (name prefix) "-")) (name tag))
        style-sym       (gensym tag-name)
        prop-names      (map name props)
        attr-names      (->> props (filter (any-meta :attr :form)) (map name))
        slot-names      (->> slots (filter (not-meta :default)) (map name))
        callback-names  (map name callbacks)
        method-names    (map name methods)
        form-value      (some-> (filter (any-meta :form) props) first name)
        dfl-slot-name   (some-> (filter (any-meta :default) slots) first name)
        this-sym        (gensym "this")
        aget            'cljs.core/aget
        js->clj         'cljs.core/js->clj
        prop-bind       (fn [x] [x (list aget (list aget this-sym "_props") (name x))])
        slot-bind       (fn [x] [x (list aget (list aget this-sym "_slots") (name x))])]
    `(do (deftemplate ~style-sym
           ~(wrap-html :style style-body))
         (def ~tag
           ~@doc
           (custom-element*
             :tag           ~tag-name
             :opts          ~(or opts {})
             :attrs         [~@attr-names]
             :props         [~@prop-names]
             :callbacks     [~@callback-names]
             :methods       [~@method-names]
             :form-value    ~form-value
             :named-slots   [~@slot-names]
             :default-slot  ~dfl-slot-name
             :render        (fn [~this-sym]
                              (binding [*custom-element* ~this-sym]
                                (let [~this ~this-sym
                                      ~@(mapcat prop-bind props)
                                      ~@(mapcat slot-bind slots)
                                      {:strs [~@callbacks]}
                                      (~js->clj (~aget ~this-sym "_callbacks"))
                                      {:strs [~@methods]}
                                      (~js->clj (~aget ~this-sym "_methods"))]
                                  (SHADOW-ROOT (~style-sym) ~render)))))))))

(defn defdeftag*
  [skip import [tag & [maybe-doc & more :as args]]]
  (let [[doc [maybe-opts & more :as args]]
        (if (string? maybe-doc) [maybe-doc more] [nil args])
        [opts [bindings & [maybe-style & more :as args]]]
        (if (map? maybe-opts) [maybe-opts more] [nil args])
        [style [render]]
        (if (string? maybe-style) [maybe-style more] [nil args])
        prefix (-> *ns* str (string/split #"\.") (->> (drop skip) (string/join "-")))]
    `(deftag* ~tag
       ~bindings
       :import  ~import
       :doc     ~doc
       :opts    ~opts
       :prefix  ~prefix
       :style   ~style
       :render  ~render)))

(defmacro defdeftag
  [name & {:keys [skip-ns-parts css-imports]}]
  `(defmacro ~name
     "Defines a web components custom element."
     {:arglists '([tag doc? opts? [this [& props] [& slots] connected] style? render])}
     [~'& args#]
     (defdeftag* ~(or skip-ns-parts 0) ~(or css-imports #{}) args#)))
