(ns daggerml.cells-test
  (:require [cljs.test :refer [deftest testing is]]
            [daggerml.cells :as c :refer [defc defc= cell cell= cell? formula? do-watch]]))

(deftest input-cell
  (let [x (cell 100)]
    (testing "input cell was created"
      (is (cell? x)))
    (testing "deref returns cell state"
      (is (= 100 @x)))
    (testing "reset! replaces cell state"
      (reset! x 200)
      (is (= 200 @x)))
    (testing "swap! updates cell state"
      (swap! x inc)
      (is (= 201 @x)))))

(deftest formula-cell
  (let [x (cell 100)
        y (cell= (+ 1 @x))]
    (testing "formula cell was created"
      (is (formula? y)))
    (testing "deref returns formula state"
      (is (= 101 @y)))
    (testing "change to input cell propagates to formula cell"
      (swap! x inc)
      (is (= 102 @y))
      (reset! x 42)
      (is (= 43 @y)))
    (testing "error is thrown when attempting to swap! or reset! formula cell"
      (is (thrown? js/Error (reset! y 0)))
      (is (thrown? js/Error (swap! y inc))))))

(deftest lens-cell
  (let [x (cell {:a {:b 100}})
        y (cell= (-> @x :a :b) #(swap! x assoc-in [:a :b] %))]
    (testing "lens setter fn updates root cells"
      (is (= 100 @y))
      (swap! y inc)
      (is (= 101 @y))
      (is (= {:a {:b 101}} @x)))))

(deftest def-macros
  (declare foo bar baz baf) ;; linter
  (defc foo 100)
  (defc bar "barp" 200)
  (defc= baz [@foo @bar])
  (defc= baf (conj @baz 300))
  (testing "def macros define named input and formula cells"
    (is (= [100 200 300] @baf))))

(deftest glitch-elimination
  (testing "formula updates only when sources change"
    (let [w (atom 0)
          x (cell 100)
          _ (cell= (do (swap! w inc) (+ 1 @x)))]
      (is (= @w 1))
      (swap! x identity)
      (is (= @w 1))
      (swap! x inc)
      (is (= @w 2))))
  (testing "the triangle test"
    (let [w (atom 0)
          x (cell 100)
          y (cell= (inc @x))
          z (cell= (do (swap! w inc) [@x @y]))]
      (is (= 1 @w))
      (is (= [100 101] @z))
      (swap! x inc)
      (is (= 2 @w))
      (is (= [101 102] @z)))))

(deftest watches
  (let [w   (atom [])
        w'  (atom [])
        x   (cell 100)
        y   (cell= (+ 1 @x))
        k   (do-watch y #(swap! w conj [%1 %2]))
        k'  (do-watch y 100 #(swap! w' conj [%1 %2]))]
    (testing "watch fires once when added"
      (is (= [[nil 101]] @w))
      (is (= [[100 101]] @w')))
    (testing "watch fires after each subsequent change"
      (swap! x inc)
      (is (= [[nil 101] [101 102]] @w))
      (is (= [[100 101] [101 102]] @w')))
    (testing "watch doesn't fire after removal"
      (remove-watch y k)
      (remove-watch y k')
      (swap! x inc)
      (is (= [[nil 101] [101 102]] @w))
      (is (= [[100 101] [101 102]] @w')))))
