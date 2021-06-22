(ns daggerml.ui
  (:refer-clojure :exclude [comment])
  (:require-macros
    [daggerml.ui :refer [defnative-element-factories with-timeout]])
  (:require
    [daggerml.cells :as c :refer [cell cell? do-watch watch=]]
    [goog.events :as events]))

;; vars ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(def ^:dynamic *custom-element* nil)

;; shadow-cljs hooks ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn ^:dev/before-load before-load
  []
  (.reload js/location))

;; Nodes ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defprotocol IDomNode
  (-node [this]))

(defn node? [this]
  (satisfies? IDomNode this))

(extend-protocol IDomNode
  string
  (-node [this]
    (.createTextNode js/document this))
  number
  (-node [this]
    (.createTextNode js/document (str this))))

(defn- ->node
  [x]
  (if (node? x) (-node x) x))

;; attributes ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmulti attr! (fn [_ k _] k) :default ::default)

(defmethod attr! ::default
  [e k v]
  (if (cell? v)
    (watch= v (attr! e k @v))
    (let [k (name k)]
      (cond (not v)   (.removeAttribute e k)
            (true? v) (.setAttribute e k k)
            :else     (.setAttribute e k v)))))

(defmethod attr! :html
  [e _ v]
  (set! (.-innerHTML e) v))

;; properties ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmulti prop! (fn [_ k _] k) :default ::default)

(defmethod prop! ::default
  [e k v]
  (if (cell? v)
    (watch= v (prop! e k @v))
    (aset e (name k) v)))

;; events ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defmulti event! (fn [_ k _] k) :default ::default)

(defmethod event! ::default
  [e k v]
  (events/listen e (name k) v))

;; built-in element constructors ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn- init!
  [e args]
  (let [attr? (map? (first args))
        attrs (when attr? (first args))
        kids  (if attr? (rest args) args)]
    (doseq [[k v] attrs]
      (cond (fn? v)       (event! e k v)
            (keyword? k)  (attr! e k v)
            (symbol? k)   (prop! e k v)))
    (doseq [k kids] (.appendChild e (->node k)))))

(defn element-factory
  [tag]
  (fn [& args]
    (doto (.createElement js/document tag) (init! args))))

(defn BODY
  [& args]
  (assert (not *custom-element*) "BODY not available inside deftag body")
  (doto (.-body js/document) (init! args)))

(defn SHADOW-ROOT
  [& args]
  (assert *custom-element* "SHADOW-ROOT not available outside deftag body")
  (doto (.-shadowRoot *custom-element*) (init! args)))

(defn COMMENT
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

(defn slot-cell
  [slot-name]
  (let [c (cell [])
        s (SLOT {:name slot-name})
        f #(reset! c (into [] (array-seq (.assignedElements s))))]
    (event! s :slotchange f)
    (specify! c
      IFn
      (-invoke
        ([this] s)
        ([this a] (init! s [a]))))))

(defn- define-property!
  [the-class property-name getter setter]
  (js/Object.defineProperty
    (.-prototype the-class)
    property-name
    #js {:get (fn [] (this-as this (getter this)))
         :set (fn [x] (this-as this (setter this x)))}))

(defn custom-element*
  [tag props attrs slots render]
  (let [tag (.toLowerCase tag)
        the-class
        (js*
          "
            (function() {
              const $reset  = ~{};
              const $cell   = ~{};
              const $slot   = ~{};
              const $watch  = ~{};
              const $props  = ~{};
              const $attrs  = ~{};
              const $slots  = ~{};
              const $render = ~{};
              return class extends HTMLElement {
                static get observedAttributes() {
                  return $attrs;
                }
                constructor() {
                  super();
                  this['_rendered'] = 0;
                  this['_props'] = $props.reduce((xs, x) => {
                    xs[x] = $cell(null);
                    return xs;
                  }, {});
                  this['_slots'] = $slots.reduce((xs, x) => {
                    xs[x] = $slot(x);
                    return xs;
                  }, {});
                  this['_connected'] = $cell.call(null, null);
                  this.attachShadow({mode: 'open'});
                }
                connectedCallback() {
                  $reset(this['_connected'], true);
                  const myself = this;
                  if (!this['_rendered']++) {
                    $attrs.forEach((x) => {
                      $watch(myself['_props'][x], (v) => {
                        if (myself[x] != v) myself[x] = v;
                        if (v === null || v === undefined) {
                          myself.removeAttribute(x);
                        } else {
                          myself.setAttribute(x, v);
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
          (into-array slots)
          render)]
    (doseq [prop props]
      (define-property! the-class prop
        (fn [this] @(aget (aget this "_props") prop))
        (fn [this x] (reset! (aget (aget this "_props") prop) x))))
    (js/window.customElements.define tag the-class)
    (element-factory tag)))
