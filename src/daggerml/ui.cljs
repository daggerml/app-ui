(ns daggerml.ui
  (:require-macros
    [daggerml.ui :as ui :refer [guard with-let with-timeout]])
  (:require
    ["element-internals-polyfill"]
    [daggerml.cells :as c :refer [cell cell? cell= do-watch]]
    [goog.dom.classlist :as domcl]
    [goog.events :as events]))

(declare bind ->node do! element on! SLOT)

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
  ([the-class property-name getter]
   (define-property! the-class property-name getter nil))
  ([the-class property-name getter setter]
   (js/Object.defineProperty
     (.-prototype the-class)
     property-name
     (clj->js (cond-> {:enumerable true}
                getter (assoc :get (fn [] (this-as this (getter this))))
                setter (assoc :set (fn [x] (this-as this (setter this x)))))))))

(defn define-read-only-properties!
  [the-class already-defined-props & args]
  (let [pairs (partition 2 args)]
    (doseq [[prop getter] pairs]
      (when-not (already-defined-props prop)
        (define-property! the-class prop getter)))))

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

(ui/extend-protocol* IDomElement
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

(extend-type events/BrowserEvent
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

(defn name*
  [x]
  (try (name x) (catch js/Error _ (str x))))

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

(defmethod do! :focus
  [e _ _ v']
  (when v' (with-timeout 0 (guard (doto e .focus .select)))))

(defmethod do! :error
  [e _ _ v']
  (.setError ^js e v'))

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

(ui/defnative-element-factories
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
  [& {:keys [tag opts attrs props callbacks methods form-value named-slots default-slot render]}]
  (let [tag (.toLowerCase tag)
        the-class
        (js*
          "
          (function() {
            const $opts       = ~{};
            const $formVal    = ~{};
            const $reset      = ~{};
            const $deref      = ~{};
            const $js2clj     = ~{};
            const $cell       = ~{};
            const $slot       = ~{};
            const $watch      = ~{};
            const $attrs      = ~{};
            const $props      = ~{};
            const $slots      = ~{};
            const $dfl_slot   = ~{};
            const $callbacks  = ~{};
            const $methods    = ~{};
            const $render     = ~{};

            const $typeof = x => Object.prototype.toString.call(x).slice(8, -1);

            const $state2value = (x) => {
              switch ($typeof(x)) {
                case 'File':
                case 'FormData':
                case 'String':
                  return x;
                case 'Null':
                case 'Undefined':
                  return '';
                default:
                  return '' + x;
              }
            }

            const $kebabMethodName = {
              'set-error': 'setError',
            }

            return class extends HTMLElement {

              // returns array of attr names that will be observed
              static get observedAttributes() {
                return $attrs;
              }

              // FACE: form attached custom element
              static formAssociated = !!$formVal;

              constructor() {
                super();

                const myself = this;

                // provides access to form-related internals
                if ($formVal) this['_internals'] = this.attachInternals();

                // rendering is only performed once in the element lifecycle
                this['_rendered'] = 0;

                // allocate a cell for each managed property
                this['_props'] = $props.reduce((xs, x) => {
                  xs[x] = $cell(null);
                  return xs;
                }, {});

                // allocate a slot-cell for each named slot
                this['_slots'] = $slots.reduce((xs, x) => {
                  xs[x] = $slot(x);
                  return xs;
                }, {});

                // allocate a slot-cell for the default slot if there is one
                if ($dfl_slot) this['_slots'][$dfl_slot] = $slot();

                this['_callbacks'] = $callbacks.reduce((xs, x) => {
                  xs[x] = $cell(null);
                  return xs;
                }, {});

                this['_methods'] = $methods.reduce((xs, x) => {
                  let m = $kebabMethodName[x];
                  if (m) xs[x] = myself[m].bind(myself);
                  return xs;
                }, {});

                this.attachShadow({mode: 'open'});
              }

              connectedCallback() {
                const myself = this;

                const cb = this['_callbacks']['connected'];
                if (cb) $reset(cb, true);

                // ensures performed at most once in the element lifecycle
                if (!this['_rendered']++) {
                  if ($formVal) {
                    let fv = this['_props'][$formVal];

                    if ($deref(fv) == null) $reset(fv, this.getAttribute($formVal));

                    $watch(fv, (oldVal, newVal) => {
                      const v = $state2value(newVal);
                      this['_internals']['setFormValue'](v);
                    });
                  }
                  $render(this);
                }
              }

              disconnectedCallback() {
                const cb = this['_callbacks']['connected'];
                if (cb) $reset(cb, false);
              }

              attributeChangedCallback(name, oldval, newval) {
                let cb = this['_callbacks']['attribute-changed'];
                if (cb) $reset(cb, $js2clj([name, oldval, newval]));
              }

              formAssociatedCallback(form) {
                const cb = this['_callbacks']['form-associated'];
                if (cb) $reset(cb, form);
              }

              formDisabledCallback(disabled) {
                const cb = this['_callbacks']['disabled'];
                if (cb) $reset(cb, disabled);
              }

              formResetCallback() {
                if ($formVal) $reset(this['_props'][$formVal], this.getAttribute($formVal));
              }

              formStateRestoreCallback(state, mode) {
                if ($formVal) $reset(this['_props'][$formVal], state);
              }

              checkValidity() {
                if ($formVal) return this['_internals']['checkValidity']();
              }

              reportValidity() {
                if ($formVal) return this['_internals']['reportValidity']();
              }

              setError(message) {
                if ($formVal) {
                  if (message) {
                    this['_internals']['setValidity']({customError: true}, message);
                  } else {
                    this['_internals']['setValidity']({});
                  }
                }
              }
            };
          })();
          "
          (clj->js opts)
          form-value
          reset!
          deref
          js->clj
          cell
          slot-cell
          do-watch
          (into-array attrs)
          (into-array props)
          (into-array named-slots)
          default-slot
          (into-array callbacks)
          (into-array methods)
          render)]
    (doseq [prop props]
      (define-property! the-class prop
        (fn [this] @(aget (aget this "_props") prop))
        (fn [this x] (reset! (aget (aget this "_props") prop) x))))
    (when form-value
      (define-read-only-properties!
        the-class (set props)
        "form"              #(-> % (aget "_internals") (aget "form"))
        "name"              #(-> % (.getAttribute "name"))
        "type"              #(.-localName %)
        "validity"          #(-> % (aget "_internals") (aget "validity"))
        "validationMessage" #(-> % (aget "_internals") (aget "validationMessage"))
        "willValidate"      #(-> % (aget "_internals") (aget "willValidate"))))
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
;; utilities ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn bind
  [elem k e c]
  (with-let [_ elem]
    (do-watch c #(set-prop elem k %2))
    (events/listen elem (name e) #(reset! c (get-prop elem k)))))
