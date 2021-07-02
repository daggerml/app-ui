(ns daggerml.cells
  (:require-macros [daggerml.cells :refer [with-let]]))

(declare Cell cell?)

(defn safe-nth  [x i] (try (nth x i) (catch js/Error _)))
(defn cell?     [x]   (and (= (type x) Cell) x))
(defn formula?  [x]   (and (cell? x) (.-thunk ^Cell x) x))
(defn lens?     [x]   (and (cell? x) (.-setter ^Cell x) x))
(defn input?    [x]   (and (cell? x) (not (formula? x)) x))
(defn deref*    [x]   (if (satisfies? cljs.core/IDeref x) @x x))

(defn- update-state!
  [^Cell this new-state queue]
  (let [old-state (.-state this)]
    (when (not= new-state old-state)
      (set! (.-state this) new-state)
      (-notify-watches this old-state new-state)
      (let [sinks (.-sinks this)]
        (dotimes [i (alength sinks)]
          (let [sink (aget sinks i)]
            (when (= -1 (.indexOf queue sink))
              (.push queue sink))))))
    queue))

(defn- propagate!
  [^Cell this new-state]
  (let [queue (update-state! this new-state (array))]
    (loop [queue queue]
      (when-let [c ^Cell (.shift queue)]
        (recur (update-state! c ((.-thunk c)) queue))))))

(deftype Cell [state sources sinks thunk watches setter]
  cljs.core/IPrintWithWriter
  (-pr-writer [_ w _]
    (write-all w "#object [daggerml.cells.Cell " (pr-str state) "]"))

  cljs.core/IDeref
  (-deref [_] state)

  cljs.core/IReset
  (-reset! [this x]
    (cond (lens? this)  (setter x)
          (input? this) (propagate! this x)
          :else         (throw (js/Error. "can't swap! or reset! formula cell")))
    state)

  cljs.core/ISwap
  (-swap! [this f]        (reset! this (f state)))
  (-swap! [this f a]      (reset! this (f state a)))
  (-swap! [this f a b]    (reset! this (f state a b)))
  (-swap! [this f a b xs] (reset! this (apply f state a b xs)))

  cljs.core/IWatchable
  (-notify-watches [this old-val new-val]
    (doseq [[key f] watches]
      (f key this old-val new-val)))
  (-add-watch [this k f]
    (set! (.-watches this) (assoc watches k f)))
  (-remove-watch [this k]
    (set! (.-watches this) (dissoc watches k))))

(defn cell
  [state]
  (Cell. state (array) (array) nil {} nil))

(defn formula
  ([sources thunk]
   (formula sources thunk nil))
  ([sources thunk setter]
   (with-let [this (cell (thunk))]
     (set! (.-thunk this) thunk)
     (set! (.-setter this) setter)
     (doseq [src sources]
       (when (cell? src)
         (.push (.-sinks ^Cell src) this))))))

(defn do-watch
  ([ref f]
   (do-watch ref nil f))
  ([ref init f]
   (with-let [k (gensym)]
     (add-watch ref k #(f %3 %4))
     (f init @ref))))

(defn cell-map
  [f c]
  (let [cseq (formula [c] #(seq @c))]
    (->> (range 0 (count @cseq))
         (map (fn [i] (formula [cseq] (fn [] (f (safe-nth @cseq i)))))))))
