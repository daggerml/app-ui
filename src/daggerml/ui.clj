(ns daggerml.ui)

(defmacro with-timeout
  [ms & body]
  `(js/setTimeout (fn [] ~@body) ~ms))

(defmacro with-interval
  [ms & body]
  `(js/setInterval (fn [] ~@body) ~ms))

(defmacro defnative-element-factories
  [& tags]
  `(do ~@(map (fn [tag] `(def ~tag (element-factory ~(.toLowerCase (name tag))))) tags)))

(defmacro deftag
  "Defines a custom element named <tag> and a constructor function of the same
   name. The <props> and <slots> arguments are bound to cells which update the
   element's properties and slots bi-directionally. The <connected> argument is
   bound to a cell indicating the element's connected/disconnected state. The
   <props> may have ^:attr meta, in which case the property will be synced with
   an attribute of the same name, bi-directionally."
  {:arglists '([tag [[& props] [& slots] connected] & body])}
  [tag & [maybe-doc & more :as args]]
  (let [doc         (if (string? maybe-doc) [maybe-doc] [])
        [[[& props] [& slots] connected] & body] (if (seq doc) more args)
        tag-name    (name tag)
        prop-names  (map name props)
        attr-names  (keep #(when (:attr (meta %)) (name %)) props)
        slot-names  (map name slots)
        this-sym    (gensym "this")
        aget        'cljs.core/aget
        prop-bind   (fn [x] [x (list aget (list aget this-sym "_props") (name x))])
        slot-bind   (fn [x] [x (list aget (list aget this-sym "_slots") (name x))])]
    `(def ~tag
       ~@doc
       (custom-element*
         ~tag-name
         [~@prop-names]
         [~@attr-names]
         [~@slot-names]
         (fn [~this-sym]
           (binding [*custom-element* ~this-sym]
             (let [~@(mapcat prop-bind props)
                   ~@(mapcat slot-bind slots)
                   ~connected (~aget ~this-sym "_connected")]
               ~@body)))))))

(comment

  (require '[clojure.pprint :refer [pprint]])

  (pprint
    (macroexpand-1
      '(defcustom foo-bar
         [[foo bar baz] [slot1 slot2] SHADOW connected]
         (SHADOW
           (STYLE
             ":host { color: red; }")
           (DIV
             "OMG"
             (SLOT {:name "foo" :slotchange #(prn :slot-foo)})
             (SLOT {:name "bar" :slotchange #(prn :slot-bar)}))))
)))
