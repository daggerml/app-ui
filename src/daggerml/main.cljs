(ns daggerml.main
  (:require
    [daggerml.ui    :as u :refer [BODY BUTTON DIV SHADOW-ROOT STYLE deftag]]
    [daggerml.cells :as c :refer [cell cell= watch=]]))

(deftag FOO-BAR
  "My foo-bar custom element."
  [[^:attr foo ^:attr bar baz] [slot1 slot2] connected]
  (let [colors (cell (cycle ["red" "blue" "green"]))
        color  (cell= (first @colors))]
    (watch= bar (prn :bar-prop @bar))
    (watch= connected (when @connected (prn :connected)))
    (watch= slot2 (prn :slot2 @slot2))
    (SHADOW-ROOT
      (STYLE ":host{display:block;}")
      (DIV {:style (cell= (str "padding: 6px; color: " @color ";"))}
        (slot1)
        (slot2)
        (DIV {:style "padding-top: 4px; text-align: center;"}
          (BUTTON {:click #(swap! colors rest)} "CHANGE COLOR"))))))

(defn -main
  []
  (BODY
    (FOO-BAR {'id "foobar" :class "omg lol" 'foo {:foobar true} 'bar 100 'baz 200}
      (DIV {:slot "slot2"} "one")
      (DIV {:slot "slot2"} "two")
      (DIV {:slot "slot1"} "three"))))
