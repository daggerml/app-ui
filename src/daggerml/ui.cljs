(ns daggerml.ui
  (:require-macros
    [daggerml.ui :refer [defnative-element-factories with-let extend-protocol*]])
  (:require
    [clojure.walk :as walk]
    [daggerml.cells :as c :refer [cell cell? cell= do-watch]]
    [garden.core :as g]
    [goog.dom.classlist :as domcl]
    [goog.events :as events]))

(declare bind ->node do! element on! SLOT compile-styles)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; vars ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(def ^:dynamic *custom-element* nil)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; shadow-cljs hooks ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn ^:dev/before-load before-load
  []
  (.reload js/location))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; helpers ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- child-vec
  [this]
  (let [x (.-childNodes this)]
    (areduce x i ret [] (conj ret (.item x i)))))

(defn- vflatten
  ([x] (persistent! (vflatten (transient []) x)))
  ([acc x] (if (sequential? x) (reduce vflatten acc x) (conj! acc x))))

(defn- remove-nil [nodes]
  (reduce #(if %2 (conj %1 %2) %1) [] nodes))

(defn- compact-kids
  [kids]
  (->>
    (vflatten kids)
    (remove-nil)
    (mapv ->node)))

(defn- set-dom-children!
  [elem new-kids]
  (let [new-kids (compact-kids new-kids)
        new?     (set new-kids)]
    (loop [[new-kid & nks]              new-kids
           [old-kid & oks :as old-kids] (child-vec elem)]
      (when (or new-kid old-kid)
        (cond
          (= new-kid old-kid) (recur nks oks)
          (not old-kid)       (do (.appendChild elem new-kid)
                                  (recur nks oks))
          (not new-kid)       (do (when-not (new? old-kid) (.removeChild elem old-kid))
                                  (recur nks oks))
          :else               (do (.insertBefore elem new-kid old-kid)
                                  (recur nks old-kids)))))))

(defn- prop?
  [x]
  (or (keyword? x) (symbol? x)))

(defn- get-prop
  [e k]
  (if (keyword? k) (.getAttribute e (name k)) (aget e (name k))))

(defn- set-prop
  [e k v]
  ((get-method do! ::default) e k (get-prop e k) v))

(defn- parse-args
  [args]
  (loop [attr (transient {})
         kids (transient [])
         [arg & args] args]
    (if-not (or arg args)
      [(persistent! attr) (persistent! kids)]
      (cond (map? arg)    (recur (reduce-kv assoc! attr arg) kids args)
            (set? arg)    (recur (reduce #(assoc! %1 %2 true) attr arg) kids args)
            (prop? arg)   (recur (assoc! attr arg (first args)) kids (rest args))
            (seq? arg)    (recur attr (reduce conj! kids (vflatten arg)) args)
            (vector? arg) (recur attr (reduce conj! kids (vflatten arg)) args)
            :else         (recur attr (conj! kids arg) args)))))

(defn- define-property!
  [the-class property-name getter setter]
  (js/Object.defineProperty
    (.-prototype the-class)
    property-name
    #js {:get (fn [] (this-as this (getter this)))
         :set (fn [x] (this-as this (setter this x)))}))

(defn- slot-cell
  [& [slot-name]]
  (let [c (cell [])
        s (if slot-name (SLOT {:name slot-name}) (SLOT))
        f #(reset! c (into [] (array-seq (.assignedElements s))))]
    (on! s :slotchange f)
    (specify! c
      IFn
      (-invoke
        ([this] s)
        ([this a] (doto s (element [a])))))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; protocols ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defprotocol IDomNode
  (-node [this]))

(extend-protocol IDomNode
  js/DocumentFragment
  (-node [this]
    (child-vec this))
  string
  (-node [this]
    (.createTextNode js/document this))
  number
  (-node [this]
    (.createTextNode js/document (str this))))

(defprotocol IDomElement
  (-proxy-kids    [this])
  (-append-child  [this child])
  (-remove-child  [this child])
  (-replace-child [this new existing])
  (-insert-before [this new existing]))

(extend-protocol* IDomElement
  [js/Element js/ShadowRoot]
  (-proxy-kids
    ([this]
     (if-let [hl-kids (.-proxyKids this)] hl-kids
       (with-let [kids (atom (child-vec this))]
         (set! (.-proxyKids this) kids)
         (do-watch kids #(set-dom-children! this %2))))))
  (-append-child
    ([this child]
     (with-let [child child]
       (let [kids (-proxy-kids this)
             i    (count @kids)]
         (if (cell? child)
           (do-watch child #(swap! kids assoc i %2))
           (swap! kids assoc i child))))))
  (-remove-child
    ([this child]
     (with-let [child child]
       (let [kids (-proxy-kids this)
             before-count (count @kids)]
         (if (cell? child)
           (swap! kids #(vec (remove (partial = @child) %)))
           (swap! kids #(vec (remove (partial = child) %))))))))
  (-replace-child
    ([this new existing]
     (with-let [existing existing]
       (swap! (-proxy-kids this) #(mapv (fn [el] (if (= el existing) new el)) %)))))
  (-insert-before
    ([this new existing]
     (with-let [new new, ins #(if (= % existing) [new %] [%])]
       (cond
         (not existing)       (swap! (-proxy-kids this) conj new)
         (not= new existing)  (swap! (-proxy-kids this) #(vec (mapcat ins %))))))))

(extend-type js/Event
  cljs.core/IDeref
  (-deref [this] (.-target this)))

(defn element?
  [this]
  (and
    (instance? js/Element this)
    (satisfies? IDomElement this)))

(defn native?
  [elem]
  (and
    (instance? js/Element elem)
    (not (element? elem))))

(defn native-node?
 [node]
 (and
  (instance? js/Node node)
  (not (element? node))))


(defn node? [this]
  (satisfies? IDomNode this))

(defn ->node
  [x]
  (if (node? x) (-node x) x))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; multimethods ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmulti do! (fn [_e k _v _v'] k) :default ::default)

(defmethod do! ::default
  [e k _v v']
  (if (keyword? k)
    (let [k (name k)]
      (cond (not v')    (.removeAttribute e k)
            (true? v')  (.setAttribute e k k)
            :else       (.setAttribute e k v')))
    (aset e (name k) v')))

(defn- normalize-class
  [x]
  (cond (map? x)    (reduce-kv #(assoc %1 (name %2) %3) {} x)
        (seq? x)    (zipmap (map name x) (repeat true))
        (string? x) (zipmap (.split x #"\s+") (repeat true))
        :else       {}))

(defmethod do! :class
  [e _ v v']
  (let [p (normalize-class v)
        q (normalize-class v')]
    (doseq [k (reduce into #{} (map keys [p q]))]
      (domcl/enable e k (boolean (q k))))))

(defmethod do! :style
  [e k v v']
  (let [v'' (compile-styles v')]
    ((get-method do! ::default) e k v v'')))

(defmethod do! :bind
  [e _ _ [k' e' c']]
  (bind e k' e' c'))

(defmulti on! (fn [_e k _f] k) :default ::default)

(defmethod on! ::default
  [e k f]
  (events/listen e (name k) f))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; built-in element constructors ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn element
  [e args]
  (let [[attrs kids] (parse-args args)]
    (doseq [[k v] attrs]
      (cond (fn? v)   (on! e k v)
            (cell? v) (do-watch v #(do! e k %1 %2))
            :else     (do! e k nil v)))
    (doseq [k kids] (-append-child e (->node k)))))

(defn element-factory
  [tag]
  (fn [& args]
    (doto (.createElement js/document tag) (element args))))

(defn BODY
  [& args]
  (assert (not *custom-element*) "BODY not available inside deftag body")
  (doto (.-body js/document) (element args)))

(defn SHADOW-ROOT
  [& args]
  (assert *custom-element* "SHADOW-ROOT not available outside deftag body")
  (doto (.-shadowRoot *custom-element*) (element args)))

(defn !--
  [text]
  (.createComment js/document text))

(defnative-element-factories
  A           DATA        H4          MENU        RT          TD
  ABBR        DATALIST    H5          MENUITEM    RTC         TEMPLATE
  ADDRESS     DD          H6          META        RUBY        TEXTAREA
  AREA        DEL         HEADER      METER       S           TFOOT
  ARTICLE     DETAILS     HGROUP      MULTICOL    SAMP        TH
  ASIDE       DFN         HR          NAV         SCRIPT      THEAD
  AUDIO       DIALOG      I           NOFRAMES    SECTION     TIME
  B           DIV         IFRAME      NOSCRIPT    SELECT      TITLE
  BASE        DL          IMG         OBJECT      SHADOW      TR
  BDI         DT          INPUT       OL          SLOT        TRACK
  BDO         EM          INS         OPTGROUP    SMALL       U
  BLOCKQUOTE  EMBED       KBD         OPTION      SOURCE      UL
  BR          FIELDSET    KEYGEN      OUTPUT      SPAN        VAR
  BUTTON      FIGCAPTION  LABEL       P           STRONG      VIDEO
  CANVAS      FIGURE      LEGEND      PARAM       STYLE       WBR
  CAPTION     FOOTER      LI          PICTURE     SUB
  CITE        FORM        LINK        PRE         SUMMARY
  CODE        H1          MAIN        PROGRESS    SUP
  COL         H2          MAP         Q           TABLE
  COLGROUP    H3          MARK        RP          TBODY                       )

(def define-template
  (memoize
    (fn [body-text]
      (let [tpl (TEMPLATE)]
        (set! (.-innerHTML tpl) body-text)
        #(.cloneNode (.-content tpl) true)))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; custom element definition ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn custom-element*
  [tag props attrs named-slots default-slot render]
  (let [tag (.toLowerCase tag)
        the-class
        (js*
          "
          (function() {
            const $reset    = ~{};
            const $cell     = ~{};
            const $slot     = ~{};
            const $watch    = ~{};
            const $props    = ~{};
            const $attrs    = ~{};
            const $slots    = ~{};
            const $dfl_slot = ~{};
            const $render   = ~{};
            return class extends HTMLElement {
              static get observedAttributes() {
                return $attrs;
              }
              constructor() {
                super();
                // rendering is only performed once in the element lifecycle
                this['_rendered'] = 0;
                // allocate a cell for each managed property
                this['_props'] = $props.reduce((xs, x) => {
                  xs[x] = $cell(null);
                  return xs;
                }, {});
                // allocate a slot-cell for each slot
                this['_slots'] = $slots.reduce((xs, x) => {
                  xs[x] = $slot(x);
                  return xs;
                }, {});
                // allocate a slot-cell for the default slot if there is one
                if ($dfl_slot) this['_slots'][$dfl_slot] = $slot();
                // allocate a cell indicating whether the element is mounted
                this['_connected'] = $cell(null);
                this.attachShadow({mode: 'open'});
              }
              connectedCallback() {
                $reset(this['_connected'], true);
                const myself = this;
                // only performed once in the element lifecycle
                if (!this['_rendered']++) {
                  // attributes are bi-directionally bound to properties
                  $attrs.forEach((x) => {
                    $watch(myself['_props'][x], (oldVal, newVal) => {
                      if (myself[x] !== newVal) myself[x] = newVal;
                      if (newVal === null || newVal === undefined) {
                        myself.removeAttribute(x);
                      } else {
                        myself.setAttribute(x, newVal);
                      }
                    });
                  });
                  $render(this);
                }
              }
              disconnectedCallback() {
                $reset(this['_connected'], false);
              }
              attributeChangedCallback(name, oldval, newval) {
                // attributes are bi-directionally bound to properties
                if (newval != oldval) this[name] = newval;
              }
            };
          })();
          "
          reset!
          cell
          slot-cell
          do-watch
          (into-array props)
          (into-array attrs)
          (into-array named-slots)
          default-slot
          render)]
    (doseq [prop props]
      (define-property! the-class prop
        (fn [this] @(aget (aget this "_props") prop))
        (fn [this x] (reset! (aget (aget this "_props") prop) x))))
    (js/window.customElements.define tag the-class)
    (element-factory tag)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; dynamic child nodes sequence ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn loop-tpl*
  [items tpl]
  (let [els         (cell [])
        itemsv      (cell= (vec @items))
        items-count (cell= (count @items))]
    (do-watch items-count
      (fn [_ n]
        (when (< (count @els) n)
          (doseq [i (range (count @els) n)]
            (swap! els assoc i (tpl (cell= (get @itemsv i nil))))))))
    (cell= (subvec @els 0 (min @items-count (count @els))))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; css ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- get-style
  [k]
  (or (and (keyword? k) (namespace k) (str "var(--" (name k) ")")) k))

(defn compile-styles
  [xs]
  (->> (if (sequential? xs) xs [xs])
       (walk/postwalk get-style)
       (apply g/style)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; utilities ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn bind
  [elem k e c]
  (with-let [_ elem]
    (do-watch c #(set-prop elem k %2))
    (events/listen elem (name e) #(reset! c (get-prop elem k)))))

(defn prevent-default-form-submit!
  []
  (let [prevent? #(not (or (get-prop @% :action) (get-prop @% :method)))]
    (on! (.-body js/document) :submit #(when (prevent? %) (.preventDefault %)))))
