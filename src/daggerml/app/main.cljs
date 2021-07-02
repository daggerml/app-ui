(ns daggerml.app.main
  (:require
    [daggerml.cells :as cell :refer [cell cell=]]
    [daggerml.ui :as ui :refer [deftag deftemplate if= when= for= cond= case=
                                A BODY BUTTON DIV FOOTER H1 HEADER LI MAIN NAV
                                P SHADOW-ROOT STYLE UL]]))

(deftemplate main-layout-style
  "
  <style>
    @import url(/css/main.css);
    :host { display: block }
    #container {
      display: grid;
      grid: 'head' auto
            'nav'  auto
            'main' 1fr
            'foot' auto
            / 1fr;
      height: 100%;
      min-width: 100%;
    }
    @media (min-width: 960px) {
      #container {
        grid: 'head head' auto
              'nav  main' 1fr
              'foot foot' auto
              / min-content 1fr;
      }
    }
    #head { max-width: 12em; grid-area: head; z-index: 1; box-shadow: 1px 1px 3px var(--gray-900); }
    #nav  { grid-area: nav; z-index: 1; box-shadow: 1px 1px 3px var(--gray-900); }
    #main { grid-area: main }
    #foot { grid-area: foot; z-index: 1; }
  </style>
  ")

(deftag MAIN-LAYOUT
  [[] [head nav main foot] _]
  (SHADOW-ROOT
    (main-layout-style)
    (DIV :id "container"
      (DIV :id "head" (head))
      (DIV :id "nav"  (nav))
      (DIV :id "main" (main))
      (DIV :id "foot" (foot)))))

(deftemplate main-style
  "
  <style>
    main-layout { height: 100vh; }
    header      { display: flex; padding: 0.5em; height: min-content;
                  background: linear-gradient(var(--gray-700), var(--gray-800));
                }
    main        { height: 100%; padding: 1em; background-color: white; }
    nav         { height: 100%; padding: 0.5em 0; background-color: var(--gray-600);
                  color: var(--indigo-200); width: 100%; }
    footer      { padding: 1em; background-color: var(--gray-600)}
    button      { padding: 0.5em 1em; color: var(--gray-400); }
    p           { padding-bottom: 1em; text-align: justify; color: var(--gray-800); }
    a           { display: block; width: 100%; min-width: 12em; padding: 0.5em 1em;
                  border: 2px solid var(--gray-600); background-color: var(--gray-600);
                  transition: background 0.5s, border 0.5s; }
    a:hover     { background-color: var(--gray-700); color: var(--indigo-200);
                  border-color: var(--gray-700); }
    a:focus     { outline: 0; border: 2px solid var(--indigo-300); }
    a:active    { background-color: var(--gray-500); transition: background-color 0s; }
  </style>
  ")

(defn -main
  []
  (BODY
    (main-style)
    (MAIN-LAYOUT
      (HEADER :slot "head"
        (BUTTON "+")
        (BUTTON "-"))
      (NAV :slot "nav"
        (UL
          (LI (A :class "ripple" :href "#" "Foo"))
          (LI (A :class "ripple" :href "#" :title "This is a mouseover text and it is kind of long." "Bar"))
          (LI (A :class "ripple" :href "#" "Baz"))))
      (MAIN :slot "main"
        (P "Call me Ishmael. Some years ago—never mind how long
            precisely—having little or no money in my purse, and
            nothing particular to interest me on shore, I thought
            I would sail about a little and see the watery part
            of the world. It is a way I have of driving off the
            spleen and regulating the circulation. Whenever I find
            myself growing grim about the mouth; whenever it is
            a damp, drizzly November in my soul; whenever I find
            myself involuntarily pausing before coffin warehouses,
            and bringing up the rear of every funeral I meet; and
            especially whenever my hypos get such an upper hand
            of me, that it requires a strong moral principle to
            prevent me from deliberately stepping into the street,
            and methodically knocking people’s hats off—then,
            I account it high time to get to sea as soon as I
            can. This is my substitute for pistol and ball. With
            a philosophical flourish Cato throws himself upon his
            sword; I quietly take to the ship. There is nothing
            surprising in this. If they but knew it, almost all
            men in their degree, some time or other, cherish very
            nearly the same feelings towards the ocean with me.")
        (P "There now is your insular city of the Manhattoes, belted
            round by wharves as Indian isles by coral
            reefs—commerce surrounds it with her surf. Right
            and left, the streets take you waterward. Its extreme
            downtown is the battery, where that noble mole is
            washed by waves, and cooled by breezes, which a few
            hours previous were out of sight of land. Look at the
            crowds of water-gazers there.")
        (P "Circumambulate the city of a dreamy Sabbath afternoon. Go
            from Corlears Hook to Coenties Slip, and from thence,
            by Whitehall, northward. What do you see?—Posted
            like silent sentinels all around the town, stand
            thousands upon thousands of mortal men fixed in ocean
            reveries. Some leaning against the spiles; some seated
            upon the pier-heads; some looking over the bulwarks
            of ships from China; some high aloft in the rigging,
            as if striving to get a still better seaward peep. But
            these are all landsmen; of week days pent up in lath
            and plaster—tied to counters, nailed to benches,
            clinched to desks. How then is this? Are the green
            fields gone? What do they here?"))
      #_(FOOTER :slot "foot" "Footer"))))
