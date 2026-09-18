"""De verhaalpatronen van de gratis verteller.

Een patroon is de vorm van een verhaal, niet het verhaal zelf. De vorm
"iemand krijgt hulp en belooft er iets voor terug" bestaat in elke traditie
ter wereld; welke mensen, welke plek en welk wezen erin voorkomen komt uit
`folk_bank.py`. Dezelfde vorm levert daardoor in Noorwegen een ander verhaal
op dan in Ierland.

Hoe een patroon eruitziet
-------------------------

`scenes` zijn de plekken. `role` verwijst naar de landschapstabel van de
traditie; `subjects` zijn de silhouetten, met hun plek, hoogte en diepte.

`arc` is het verhaal op volgorde. Elke regel levert één of meer beats:

    mode    welke soort beat (title, open, tell, turn, speech, close, moral)
    scene   in welke plek hij speelt
    lines   de mogelijke zinnen; er wordt er één gekozen
    count   hoeveel zinnen deze stap minstens oplevert
    grow    of deze stap langer mag worden als het verhaal nog kort is
    pool    uit welke gedeelde voorraad bijgevuld mag worden

De slots tussen accolades worden ingevuld met de gekozen traditie:
{hero} {Hero} {role} {place} {water} {wild} {home} {the_home} {being}
{the_being} {token} {season} {beast} {he} {him} {his} {He} {His}
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
#  1. De afspraak bij het water
# ---------------------------------------------------------------------------

BARGAIN = {
    "key": "bargain",
    "role_kind": "water",
    "idea": "Iemand krijgt hulp van een wezen bij het water en belooft er iets voor terug",
    "titles": [
        "The Bargain at {place}",
        "The {Role} of {place}",
        "What Was Promised at {place}",
        "The {Role} and {the_Being}",
    ],
    "description": [
        "A {role} at {place} is helped out of a bad season by something that "
        "speaks to {him} from {water}, and pays for the help with a promise "
        "made too quickly. {origin_sentence} This is a retelling in our own "
        "words, not a translation of any single version.",
    ],
    "tags": ["bargain", "folk tale", "water spirit"],
    "scenes": [
        {"role": "home", "time": ["dawn", "day"], "weather": "none",
         "caption": "{place}",
         "subjects": [("home", 0.24, 0.11, 0.88), ("hero", 0.62, 0.10, 0.94)]},
        {"role": "water", "time": ["day", "overcast"], "weather": "none",
         "caption": None,
         "subjects": [("rowboat", 0.46, 0.07, 0.62)]},
        {"role": "water", "time": ["dusk", "moonlit"], "weather": "mist",
         "caption": None,
         "subjects": [("being", 0.38, "being", 0.80), ("hero", 0.70, 0.11, 0.93)]},
        {"role": "village", "time": "day", "weather": "none",
         "caption": "The good years",
         "subjects": [("home", 0.44, 0.15, 0.75), ("oak", 0.78, 0.20, 0.93)]},
        {"role": "water", "time": ["night", "storm"], "weather": "rain",
         "caption": None,
         "subjects": [("being", 0.44, "being", 0.78), ("hero", 0.24, 0.11, 0.94)]},
        {"role": "home", "time": ["dawn", "winter"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.30, 0.10, 0.90)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "There was {a_role} at {place} who lived alone in {home} at the edge of {water}.",
            "{Hero} was {a_role} at {place}, and had been one since {he} was old enough to be useful.",
            "The house stood where the track ran out, with {water} in front of it and the hill behind.",
            "{He} had the house from {his} father and the work with it, and neither had improved in the meantime.",
            "It was not a poor living, but it was the kind that goes wrong all at once.",
            "In a good year there was enough. That year was not a good year.",
        ]},
        {"mode": "tell", "scene": 1, "count": 3, "grow": True, "pool": "work", "lines": [
            "Every morning {hero} went down to {water} before the light and came back when it went.",
            "The season had been wrong from the start: too much weather early, and then none at all.",
            "By {season} there was nothing coming in, and what was put by was going out.",
            "{He} went further out than {he} should have, on days {he} should not have gone at all.",
            "Other people at {place} were having the same year, which is a comfort and no help.",
            "The mending got done because there was nothing else to do.",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "pool": "land", "lines": [
            "{water} at that time of year goes the colour of slate and stays that way for weeks.",
            "You can see the bottom in the shallows and nothing at all ten yards out.",
            "There is a place where the water turns back on itself, and everyone at {place} keeps off it.",
            "The wind comes down off {wild} in the afternoon, every afternoon, and stops at dark.",
        ]},
        {"mode": "turn", "scene": 2, "count": 1, "lines": [
            "Then one evening {hour}, something spoke to {him} from {water}.",
            "It was {season}, {hour}, when {hero} heard {his} own name come up off the water.",
            "{He} was alone on {water} when a voice asked {him} what {he} was looking for.",
        ]},
        {"mode": "tell", "scene": 2, "count": 2, "grow": True, "pool": "dread", "lines": [
            "{Hero} did not answer at first. There is no good answer to a voice with nobody under it.",
            "When {he} looked, there was {being} standing where no one could stand.",
            "It did not come closer and it did not go away.",
            "{He} had heard of such things at {place}, the way everybody has, and had not believed it on a fine day.",
        ]},
        {"mode": "speech", "scene": 2, "count": 1, "lines": [
            "\"I can make the water give,\" it said. \"You would not have another year like this one.\"",
            "\"There is nothing wrong with you that I cannot mend,\" it said. \"Only ask.\"",
            "\"You are working hard for nothing,\" it said. \"That can be changed tonight.\"",
        ]},
        {"mode": "tell", "scene": 2, "count": 2, "grow": True, "lines": [
            "{Hero} asked what it wanted, because nothing is given.",
            "It named its price, and the price sounded like nothing at all.",
            "That is how such a price always sounds when you are cold and it is late.",
            "{He} was to give up the first thing that greeted {him} at {his} own door.",
            "{He} thought of the dog, and said yes, and did not think past the dog.",
        ]},
        {"mode": "speech", "scene": 2, "count": 1, "lines": [
            "\"Say it out loud,\" it said, \"or it does not hold.\"",
            "\"Then say the word,\" it said, \"and go home, and sleep.\"",
        ]},
        {"mode": "tell", "scene": 2, "count": 1, "grow": True, "lines": [
            "{Hero} said the word. It was one word, and {he} said it quietly, and it was said.",
            "The water closed. There was nothing standing on it any more.",
            "{He} rowed back with {his} hands shaking, and told nobody.",
        ]},
        {"mode": "turn", "scene": 3, "count": 1, "lines": [
            "From that season on, everything {he} touched came good.",
            "After that, {hero} could not have failed if {he} had tried.",
            "The luck came in like weather, and it did not go out again.",
        ]},
        {"mode": "tell", "scene": 3, "count": 4, "grow": True, "pool": "work", "lines": [
            "The nets came up full when other people's came up empty.",
            "{He} put a new roof on {the_home}, and then a second room under it.",
            "People at {place} said {he} had found a run of fish that nobody else knew about, and {he} let them say it.",
            "In three years {he} had more than {his} father had in thirty.",
            "{He} married, and there was a child in the house, and the house was warm.",
            "Nothing was asked of {him} in all that time.",
            "{He} kept {token} from that night in a box, and did not look at it often.",
        ]},
        {"mode": "tell", "scene": 3, "count": 2, "grow": True, "pool": "waiting", "lines": [
            "It is possible to stop thinking about a thing if the thing does not remind you.",
            "{He} came to believe, in the way people do, that it had been a bad evening and nothing more.",
            "The word {he} had said got smaller every year until it was a word {he} had almost not said.",
        ]},
        {"mode": "turn", "scene": 4, "count": 1, "lines": [
            "Then one night in {season}, the weather turned, and {he} came home late.",
            "It was seven years to the day when {he} came up from {water} in the dark.",
            "The night it came due, the rain was coming across {water} in sheets.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "pool": "dread", "lines": [
            "The door of {the_home} opened before {he} reached it.",
            "It was the child who came out to meet {him}, running, glad, calling {his} name.",
            "{Hero} stopped where {he} was, in the rain, and understood what {he} had said, and to whom.",
            "Behind {him}, out on the water, something was waiting that had waited seven years already.",
            "{He} did not turn round. Not turning round was all {he} had.",
        ]},
        {"mode": "speech", "scene": 4, "count": 1, "lines": [
            "\"You said the word,\" the voice said, from the water. \"I have not been in a hurry.\"",
            "\"I take what greeted you,\" it said. \"You knew that when you said it.\"",
        ]},
        {"mode": "tell", "scene": 4, "count": 2, "grow": True, "lines": [
            "{Hero} offered everything {he} had instead: the boat, the house, the years {he} had left.",
            "The voice was not interested in any of it, and said so plainly.",
            "So {he} did the only thing that was left, and went down to the water {himself}.",
            "What was agreed was one who greeted {him}, and {he} greeted it first, and out loud.",
        ]},
        {"mode": "close", "scene": 5, "count": 2, "grow": True, "pool": "aftermath", "lines": [
            "In the morning the boat was drawn up where it always was, and the house was warm, and {hero} was not in it.",
            "The child grew up at {place} and had the house and never knew what it had cost.",
            "The luck stayed. That is the part people find hardest to believe.",
            "They say the water at {place} has been quiet ever since, and quiet in that place is not the same as calm.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "A promise costs nothing on the evening you make it. That is not the evening it is collected.",
            "What is given for nothing is not given for nothing. It is only given before the price is read out.",
            "The old tellers did not put a lesson on the end of this one. They let the seven years do it.",
        ]},
    ],
}


# ---------------------------------------------------------------------------
#  2. De ene regel
# ---------------------------------------------------------------------------

ONE_RULE = {
    "key": "one-rule",
    "being_kinds": ["woman", "man", "monk", "traveller", "rider", "child", "giant"],
    "idea": "Een geschenk met één voorwaarde, en de voorwaarde wordt gebroken",
    "titles": [
        "The One Rule",
        "The Gift at {place}",
        "What {hero} Was Told Not to Do",
        "The {Role}'s Luck",
    ],
    "description": [
        "Something is given to {a_role} at {place} on one condition, and the "
        "condition holds for exactly as long as anybody can bear it. "
        "{origin_sentence} Retold here in our own words."
    ],
    "tags": ["folk tale", "the one rule", "broken promise"],
    "scenes": [
        {"role": "wild", "time": ["day", "overcast"], "weather": "none",
         "caption": None,
         "subjects": [("hero", 0.34, 0.11, 0.92), ("dead_tree", 0.74, 0.18, 0.86)]},
        {"role": "wild", "time": ["dusk", "moonlit"], "weather": "mist",
         "caption": None,
         "subjects": [("being", 0.52, "being", 0.82)]},
        {"role": "home", "time": "day", "weather": "none",
         "caption": "{place}",
         "subjects": [("home", 0.40, 0.14, 0.82), ("hero", 0.68, 0.10, 0.93)]},
        {"role": "village", "time": ["day", "overcast"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.30, 0.13, 0.78), ("well", 0.62, 0.08, 0.90)]},
        {"role": "wild", "time": ["storm", "night"], "weather": "rain",
         "caption": None,
         "subjects": [("hero", 0.42, 0.12, 0.93)]},
        {"role": "home", "time": ["dusk", "winter"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.36, 0.12, 0.86)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "{Hero} was {a_role} at {place}, and not a lucky one.",
            "There was a house at {place} with one room and a great deal of weather in it.",
            "{He} worked {wild} in the season for it and took what work there was in between.",
            "There were three of them in the house and food for two, most weeks.",
            "Nobody at {place} thought {he} would come to anything, and they were not unkind about it.",
        ]},
        {"mode": "tell", "scene": 0, "count": 3, "grow": True, "pool": "work", "lines": [
            "{He} went up into {wild} before it was light and came down again with what {he} could carry.",
            "The work was hard in the way that does not get easier with practice.",
            "In {season} the ground turns and everything takes twice as long.",
            "{He} was not idle and {he} was not stupid. {He} was only unlucky, which is worse.",
            "Whatever {he} put by went on something that broke.",
        ]},
        {"mode": "turn", "scene": 1, "count": 1, "lines": [
            "Then one evening in {wild}, {he} came on {being} sitting where nothing should have been sitting.",
            "It was {hour} when {being} stepped out of {wild} and stood in the path.",
            "{He} took a way home {he} had never taken, and that is where {he} met {being}.",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "pool": "dread", "lines": [
            "It knew {his} name, and that was the first thing wrong with it.",
            "It asked {him} for something small, and {he} gave it, because it cost nothing.",
            "Afterwards {he} could not remember what it had looked like, only what it had said.",
            "Nothing in {wild} made a sound the whole time it spoke.",
        ]},
        {"mode": "speech", "scene": 1, "count": 1, "lines": [
            "\"You have been decent to me,\" it said, \"so I will be the same to you.\"",
            "\"Take this,\" it said, \"and your house will not be cold again.\"",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "lines": [
            "It gave {him} {token}, and told {him} what it would do.",
            "Then it told {him} the one rule, and it said the rule only once.",
            "{He} was never to count what came of it. Not out loud, not in {his} head, not on paper.",
            "{He} said that was easy. It said that everybody says so.",
        ]},
        {"mode": "turn", "scene": 2, "count": 1, "lines": [
            "And it was true. From that week, the house at {place} was never short.",
            "What it promised, it did, and it did it quietly.",
        ]},
        {"mode": "tell", "scene": 2, "count": 4, "grow": True, "pool": "work", "lines": [
            "There was always a little more in the store than there had been the day before.",
            "Not a great deal. Never enough to be talked about. Only never less.",
            "{He} mended the roof, and then the wall, and then bought the field behind the house.",
            "The children grew up in a warm room, which {he} had not done {himself}.",
            "People at {place} said {he} had finally had a turn of luck, and {he} agreed with them.",
            "For eleven years {he} did not count anything.",
        ]},
        {"mode": "tell", "scene": 3, "count": 2, "grow": True, "pool": "waiting", "lines": [
            "It is a strange thing to live beside and not look at.",
            "Somebody asked {him} once how much there was. {He} said {he} did not know, which was true.",
            "A rule you keep every day stops feeling like a rule and starts feeling like a habit.",
            "And a habit is a thing you can break without meaning to.",
        ]},
        {"mode": "turn", "scene": 4, "count": 1, "lines": [
            "Then a man came from the town about a tax, and wanted a figure.",
            "In {season} the question came up in a way {he} could not walk around.",
            "It was a small thing that did it, as it always is.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "pool": "dread", "lines": [
            "{Hero} stood in the store with a lamp and said it would only be a look.",
            "{He} got as far as the third row before {he} heard {his} own voice saying the numbers.",
            "{He} stopped straight away. Stopping straight away is not the same as not starting.",
            "The lamp went out. It had oil in it and no wind on it, and it went out.",
        ]},
        {"mode": "speech", "scene": 4, "count": 1, "lines": [
            "\"You counted,\" said a voice from the door, which was shut. \"I asked one thing.\"",
            "\"That is the end of it, then,\" the voice said, without any anger at all.",
        ]},
        {"mode": "tell", "scene": 4, "count": 2, "grow": True, "lines": [
            "In the morning the store was as full as it had ever been, and it never filled again.",
            "Nothing was taken back. Nothing more was given, and that turned out to be the same thing.",
            "{He} went up into {wild} every evening for a month and found nobody to talk to.",
        ]},
        {"mode": "close", "scene": 5, "count": 2, "grow": True, "pool": "aftermath", "lines": [
            "They lived on what was there, and it lasted a long time, and then it did not.",
            "{Hero} went back to the old work in the end, and was better at it than {he} had been.",
            "{He} told the story {himself}, later, which is how it is known at all.",
            "{He} said the worst of it was that {he} had not even wanted the number.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "The rule is never the difficult part. Remembering that there is one is the difficult part.",
            "A gift with a condition is a loan, and this one was called in the first time it was tested.",
            "Eleven years of keeping a promise, and it ended in the time it takes to say three numbers.",
        ]},
    ],
}


# ---------------------------------------------------------------------------
#  3. De weg na donker
# ---------------------------------------------------------------------------

NIGHT_ROAD = {
    "key": "night-road",
    "being_kinds": ["woman", "man", "monk", "traveller", "rider", "child", "giant"],
    "idea": "Iemand loopt na donker over een weg waar gewaarschuwd voor is",
    "titles": [
        "The Road After Dark",
        "The Night Road to {place}",
        "What Walks the Road at {place}",
        "{Hero} and the Late Road",
    ],
    "description": [
        "Everybody at {place} knows which road not to take after dark, and "
        "{hero} takes it anyway, for the usual reason: it is shorter. "
        "{origin_sentence} This retelling is our own."
    ],
    "tags": ["folk tale", "night road", "ghost story", "the old road"],
    "scenes": [
        {"role": "village", "time": ["dusk", "overcast"], "weather": "none",
         "caption": "{place}",
         "subjects": [("home", 0.26, 0.13, 0.80), ("signpost", 0.58, 0.07, 0.92)]},
        {"role": "wild", "time": "dusk", "weather": ["none", "mist"],
         "caption": None,
         "subjects": [("hero", 0.30, 0.11, 0.92), ("signpost", 0.66, 0.06, 0.88)]},
        {"role": "wild", "time": ["night", "moonlit"], "weather": "mist",
         "caption": None,
         "subjects": [("hero", 0.24, 0.11, 0.93), ("dead_tree", 0.70, 0.19, 0.84)]},
        {"role": "high", "time": ["night", "underworld"], "weather": "mist",
         "caption": None,
         "subjects": [("being", 0.48, "being", 0.80), ("standing_stones", 0.14, 0.12, 0.70)]},
        {"role": "wild", "time": "night", "weather": "none",
         "caption": None,
         "subjects": [("hero", 0.52, 0.12, 0.94)]},
        {"role": "village", "time": ["dawn", "day"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.34, 0.13, 0.82), ("church", 0.70, 0.16, 0.76)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "There are two ways from {place} to the market town, and everybody uses the long one.",
            "The short way runs along {water} and up over {wild}, and saves an hour and a half.",
            "Nobody at {place} would tell you it was dangerous. They would only say they went the other way.",
            "{Hero} was {a_role} there, young enough to find that funny.",
            "{He} had walked the short way in daylight a hundred times and never seen anything but sheep.",
        ]},
        {"mode": "tell", "scene": 0, "count": 3, "grow": True, "pool": "land", "lines": [
            "The old road is older than the village. You can see where it was cut into the slope.",
            "There is a stone halfway along it with nothing written on it any more.",
            "Carts stopped using it when the new road went in, and after that it went to grass.",
            "In summer it is a pleasant walk. Everybody agrees about that too.",
            "The difference between the two roads is an hour of daylight, and everybody at {place} has made that trade.",
        ]},
        {"mode": "turn", "scene": 1, "count": 1, "lines": [
            "On the evening this happened, {hero} was late leaving town, and the weather was coming.",
            "It was {season}, and the light was going faster every week, and {he} had stayed too long.",
            "{He} stood at the fork with the rain starting and chose the short way.",
        ]},
        {"mode": "tell", "scene": 1, "count": 3, "grow": True, "pool": "travel", "lines": [
            "For the first mile there was still enough light to see the ruts.",
            "{He} walked fast, the way you do when you have decided something you are not sure about.",
            "An old man at the last house called something after {him}. {He} did not hear it properly and did not go back.",
            "The wind was behind {him}, which is the only good thing that can be said about that night.",
            "By the stone, the light had gone altogether.",
        ]},
        {"mode": "turn", "scene": 2, "count": 1, "lines": [
            "Then {he} heard people coming the other way.",
            "Somewhere ahead, on a road where there was nobody, there were footsteps.",
            "It began with a light that was not a lantern, coming down the slope towards {him}.",
        ]},
        {"mode": "tell", "scene": 2, "count": 3, "grow": True, "pool": "dread", "lines": [
            "{He} stepped off the road to let them pass, which is only manners.",
            "There were a great many of them and they made almost no sound.",
            "They went by two and three at a time, and none of them looked at {him}.",
            "{He} knew one of the faces. {He} had carried that one to the churchyard the winter before.",
            "{He} did not move. {He} could not have said afterwards whether that was courage or the other thing.",
        ]},
        {"mode": "turn", "scene": 3, "count": 1, "lines": [
            "At the top of the rise, the last of them stopped in front of {him}.",
            "One turned out of the line and stood in the road, and it was {being}.",
        ]},
        {"mode": "speech", "scene": 3, "count": 1, "lines": [
            "\"You are early,\" it said. \"Nobody is expecting you.\"",
            "\"You should not be able to see us,\" it said. \"That is the trouble with this road.\"",
        ]},
        {"mode": "tell", "scene": 3, "count": 3, "grow": True, "lines": [
            "{Hero} said nothing at all, which was the best thing {he} did that night.",
            "It asked {him} where {he} was going, and {he} pointed, because {he} could not speak.",
            "It looked at {him} for what felt like a long time.",
            "Then it told {him} the way home, and the way it named was not the way {he} had come.",
            "It said {he} was to walk it without stopping and without looking behind {him}.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "pool": "travel", "lines": [
            "So {he} walked. The road went where it had never gone before, and {he} took it.",
            "Twice {he} heard {his} own name behind {him}, in a voice {he} knew, and did not turn.",
            "The third time it was the voice of somebody who had been dead eleven years.",
            "{He} kept {his} eyes on the ground in front of {his} own feet and counted nothing.",
            "The light came up while {he} was still walking, which should not have been possible.",
        ]},
        {"mode": "close", "scene": 5, "count": 3, "grow": True, "pool": "aftermath", "lines": [
            "{He} came into {place} at first light, from the wrong direction, with {his} coat soaked through.",
            "{He} had been gone one night. The village had been looking for {him} for three days.",
            "{His} hair had gone white at one side and stayed that way.",
            "{He} never used the short road again, and never told anybody not to.",
            "When people asked, {he} said only that there had been a lot of them and they were not in a hurry.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "When a whole village goes the long way round, the long way is the short one.",
            "Nobody at {place} ever forbade that road. They did not need to, afterwards.",
            "The advice in this story is the kind that is only ever given once and never taken.",
        ]},
    ],
}


# ---------------------------------------------------------------------------
#  4. Het dier dat gespaard werd
# ---------------------------------------------------------------------------

BEAST_SPARED = {
    "key": "beast-spared",
    "role_kind": "land",
    "idea": "Een dier wordt gespaard en betaalt dat jaren later terug",
    "titles": [
        "The {Beast_Title} of {place}",
        "What {hero} Did Not Do",
        "The Debt at {place}",
        "The Winter {hero} Was Repaid",
    ],
    "description": [
        "{Hero}, {a_role} at {place}, has one clear shot and does not take it, "
        "and is still being paid for it years later. {origin_sentence} "
        "Retold here in our own words."
    ],
    "tags": ["folk tale", "mercy", "animal tale", "winter"],
    "scenes": [
        {"role": "wild", "time": ["dawn", "winter"], "weather": "snow",
         "caption": None,
         "subjects": [("hero", 0.28, 0.11, 0.92), ("beast", 0.66, 0.08, 0.84)]},
        {"role": "wild", "time": ["day", "overcast"], "weather": "snow",
         "caption": None,
         "subjects": [("beast", 0.52, 0.09, 0.80), ("dead_tree", 0.16, 0.17, 0.88)]},
        {"role": "home", "time": ["dusk", "winter"], "weather": "none",
         "caption": "{place}",
         "subjects": [("home", 0.38, 0.13, 0.84), ("hero", 0.66, 0.10, 0.93)]},
        {"role": "high", "time": ["storm", "winter"], "weather": "snow",
         "caption": None,
         "subjects": [("hero", 0.46, 0.11, 0.93)]},
        {"role": "wild", "time": ["night", "moonlit"], "weather": "snow",
         "caption": None,
         "subjects": [("beast", 0.40, 0.09, 0.82), ("hero", 0.62, 0.11, 0.94)]},
        {"role": "village", "time": ["dawn", "day"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.32, 0.13, 0.82), ("oak", 0.74, 0.20, 0.90)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "{Hero} was {a_role} at {place} in a winter that everybody there still counts from.",
            "That was the year the snow came in {season} and did not go until it was nearly summer.",
            "The village had food for the winter they expected and not for the one they got.",
            "{He} went up into {wild} because that was where anything was left.",
        ]},
        {"mode": "tell", "scene": 0, "count": 3, "grow": True, "pool": "travel", "lines": [
            "{He} was out before light and back after dark, and most days brought nothing home.",
            "There is a kind of cold that does not feel like cold. That is the kind to be afraid of.",
            "The tracks in the snow were all old. Everything that could leave had left.",
            "On the fourth day {he} went further up than anybody had been that year.",
        ]},
        {"mode": "turn", "scene": 1, "count": 1, "lines": [
            "And there, in the open, was {beast}, standing still and looking straight at {him}.",
            "Then {he} came round the rock and {beast} was in front of {him}, close enough to touch.",
        ]},
        {"mode": "tell", "scene": 1, "count": 3, "grow": True, "pool": "dread", "lines": [
            "It was thin. It had been having the same winter as everybody else.",
            "It did not run. It had nothing left to run with.",
            "{Hero} had one clear shot and all the reason in the world to take it.",
            "There was a house behind {him} with people in it who had not eaten properly in a month.",
            "{He} stood there long enough for {his} hands to go numb.",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "lines": [
            "Then {he} lowered what {he} was carrying and stepped back off the path.",
            "{He} could not have told you why, then or later. It was not kindness. It was something nearer to recognition.",
            "{Beast_the} watched {him} go and did not move until {he} was out of sight.",
            "{He} came home with nothing and said nothing about it.",
        ]},
        {"mode": "tell", "scene": 2, "count": 3, "grow": True, "pool": "waiting", "lines": [
            "They got through that winter on what the village had between them, which is how villages get through winters.",
            "Two of the old people did not. That was counted against nobody.",
            "The spring came late and hard and then everything happened at once.",
            "{Hero} did not think about {wild} again for six years.",
            "{He} married in that time, and the house was fuller than it had been.",
        ]},
        {"mode": "turn", "scene": 3, "count": 1, "lines": [
            "Then, six winters on, {he} was caught out on {wild} in weather that came from nothing.",
            "It was {season} when the storm came down off {wild} with {him} still above the treeline.",
        ]},
        {"mode": "tell", "scene": 3, "count": 3, "grow": True, "pool": "dread", "lines": [
            "{He} knew that ground as well as anybody and it did not help at all.",
            "There is a point at which you stop looking for the path and start looking for shelter.",
            "{He} got into the lee of a rock and understood that it was not enough.",
            "The cold came up through {him} from the ground, which is the way it comes when it means it.",
            "{He} thought about the house and could not hold the thought.",
        ]},
        {"mode": "turn", "scene": 4, "count": 1, "lines": [
            "Some time in the night, something came and lay against {him}.",
            "{He} woke because something warm had got between {him} and the wind.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "lines": [
            "{He} did not open {his} eyes. {He} was past being able to.",
            "It stayed until the wind dropped, and then it got up and went a little way off and waited.",
            "When {he} could stand, it went ahead of {him}, and stopped when {he} stopped.",
            "It brought {him} down by a way {he} did not know, which was shorter than the way {he} did.",
            "At the last wall it stopped and would not come further.",
        ]},
        {"mode": "close", "scene": 5, "count": 3, "grow": True, "pool": "aftermath", "lines": [
            "{Hero} came into {place} at first light with all {his} fingers, which the doctor called luck.",
            "{He} went back up with food twice that spring and left it at the wall, and it was gone both times.",
            "{He} told the story exactly once, to {his} son, and the son told it afterwards.",
            "Nobody at {place} hunted that side of {wild} again while {he} was alive.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "What is not done can be repaid the same as what is.",
            "{He} always said {he} had not spared anything. {He} said it had been a bad shot and {he} had known it.",
            "Six years is a long time to carry a debt. Nothing in the story says it was in a hurry.",
        ]},
    ],
}


# ---------------------------------------------------------------------------
#  5. Eén nacht onder de heuvel
# ---------------------------------------------------------------------------

HOLLOW_HILL = {
    "key": "hollow-hill",
    "role_from": "musicians",
    "being_kinds": ["woman", "man", "monk", "traveller", "rider", "child", "giant"],
    "idea": "Iemand gaat één nacht mee naar binnen en komt honderd jaar later buiten",
    "titles": [
        "One Night Under the Hill",
        "The {Role} Who Went Inside",
        "The Hill at {place}",
        "{Hero} and the Long Night",
    ],
    "description": [
        "{Hero} goes up the hill at {place} to play one night for one fee, "
        "and comes down into a village that has had a hundred years to forget "
        "{him}. {origin_sentence} Retold here in our own words."
    ],
    "tags": ["folk tale", "fairy hill", "lost time", "music"],
    "scenes": [
        {"role": "village", "time": ["dusk", "overcast"], "weather": "none",
         "caption": "{place}",
         "subjects": [("home", 0.28, 0.13, 0.82), ("hero", 0.60, 0.10, 0.93)]},
        {"role": "high", "time": ["dusk", "moonlit"], "weather": ["none", "mist"],
         "caption": None,
         "subjects": [("hero", 0.34, 0.11, 0.92), ("standing_stones", 0.66, 0.13, 0.78)]},
        {"role": "high", "time": ["moonlit", "night"], "weather": "mist",
         "caption": None,
         "subjects": [("being", 0.44, "being", 0.82), ("gate", 0.72, 0.10, 0.74)]},
        {"role": "high", "time": "underworld", "weather": "none",
         "caption": "Inside the hill",
         "subjects": [("campfire", 0.50, 0.07, 0.88), ("being", 0.26, "being", 0.80)]},
        {"role": "high", "time": ["dawn", "day"], "weather": "mist",
         "caption": None,
         "subjects": [("hero", 0.44, 0.11, 0.93), ("standing_stones", 0.18, 0.12, 0.76)]},
        {"role": "village", "time": ["day", "overcast"], "weather": "none",
         "caption": None,
         "subjects": [("church", 0.36, 0.17, 0.78), ("ruin", 0.72, 0.12, 0.86)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "{Hero} was {a_role} at {place}, and played at every wedding between there and the coast.",
            "{He} was the one they sent for when there was dancing to be done properly.",
            "{He} had no land and no trade beyond it, and it kept {him} in boots.",
            "There was a hill above {place} that people walked round rather than over, out of habit.",
        ]},
        {"mode": "tell", "scene": 0, "count": 3, "grow": True, "pool": "work", "lines": [
            "{He} was walking home from a wedding, {hour}, with the fee in {his} pocket.",
            "It had been a long night already and {he} had been paid in drink for half of it.",
            "The way home went past the foot of the hill, as it always had.",
            "There was music coming off the hill, and it was not music from the village.",
            "{He} stopped to listen, which is what anybody would do, and that is the whole mistake.",
        ]},
        {"mode": "turn", "scene": 1, "count": 1, "lines": [
            "A man came down to meet {him} and asked if {he} was the one who played.",
            "There was a light on the hill where there was no house, and somebody standing in it.",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "pool": "dread", "lines": [
            "The stranger was dressed for a wedding, but not for any wedding {hero} had played at.",
            "He offered a night's work, and named a fee three times what anybody at {place} would pay.",
            "{Hero} asked whose wedding it was. The answer was polite and told {him} nothing.",
        ]},
        {"mode": "speech", "scene": 2, "count": 1, "lines": [
            "\"One night,\" said {the_being}. \"You will be back before they miss you.\"",
            "\"Play until we stop asking,\" it said, \"and eat nothing while you are inside.\"",
        ]},
        {"mode": "tell", "scene": 2, "count": 3, "grow": True, "lines": [
            "{Hero} said yes. {He} was young, and the fee was real, and {he} could hear the tune already.",
            "The hillside opened where there had been nothing but grass and a gate post.",
            "Inside it was warm and full of people and there was no smoke from the fire.",
            "{He} remembered the part about eating nothing, and kept to it, and that is why there is a story.",
        ]},
        {"mode": "tell", "scene": 3, "count": 4, "grow": True, "lines": [
            "So {he} played. {He} played better than {he} had ever played in {his} life.",
            "They danced the whole night and did not tire, and nobody asked for the same tune twice.",
            "Food came round, and drink, and {he} took none of it, and they did not press {him}.",
            "There was no window in that room and no way of telling how long anything took.",
            "Once {he} thought {he} recognised a face from {place}, from a long time before.",
            "When {he} put the instrument down, {his} hands were not tired, and that frightened {him} more than the rest.",
        ]},
        {"mode": "speech", "scene": 3, "count": 1, "lines": [
            "\"That will do,\" said {the_being}, and counted the fee into {his} hand.",
            "\"Go out the way you came,\" it said, \"and do not look for the door again.\"",
        ]},
        {"mode": "turn", "scene": 4, "count": 1, "lines": [
            "{He} came out onto the hillside and it was morning, and the wrong morning.",
            "The hill closed behind {him} and there was dew on the grass and no mark of any door.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "pool": "land", "lines": [
            "The wall along the track was gone. There was a new wall, in a different line.",
            "There were trees on the slope that had not been there, and they were not young trees.",
            "{He} walked down into {place} with the fee still in {his} hand.",
            "The road was where it had been, which was the only thing that was.",
        ]},
        {"mode": "tell", "scene": 5, "count": 3, "grow": True, "lines": [
            "The people in the street did not know {him}, and {he} did not know one of them.",
            "The house {he} had grown up in was a wall with grass on top of it.",
            "{He} asked after {his} own family and they had to think about the name.",
            "An old woman said her grandmother had known a {role} who went up the hill and did not come back.",
            "That had been, she said, before the church was rebuilt, and the church was not new.",
        ]},
        {"mode": "close", "scene": 5, "count": 2, "grow": True, "pool": "aftermath", "lines": [
            "{He} opened {his} hand, and what was in it was not money any more.",
            "{He} sat down on the wall and did not get up again for a long while.",
            "They were decent to {him} at {place}. There was a room, and work of a sort.",
            "{He} never played again. People asked, and {he} said {he} had forgotten how, which was not true.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "One night is one night, unless it is somebody else's night.",
            "The fee was paid in full. Nobody ever said what it was paid in.",
            "Tellers who ended this one cheerfully were not from {place}.",
        ]},
    ],
}


# ---------------------------------------------------------------------------
#  6. De klok onder het water
# ---------------------------------------------------------------------------

DROWNED_BELL = {
    "key": "drowned-bell",
    "role_kind": "water",
    "being_kinds": ["woman", "man", "monk", "traveller", "rider", "child", "giant"],
    "idea": "Een verdronken dorp onder het water, en een klok die nog luidt",
    "titles": [
        "The Bell Under {water_title}",
        "The Drowned Village of {place}",
        "What Rings Under the Water",
        "The Night the Water Came to {place}",
    ],
    "description": [
        "There was a village where {water} is now, and on certain nights you "
        "can still hear its bell. {Hero} went out to find out why. "
        "{origin_sentence} Retold here in our own words."
    ],
    "tags": ["folk tale", "drowned village", "bell", "lake legend"],
    "scenes": [
        {"role": "water", "time": ["day", "overcast"], "weather": "none",
         "caption": "{place}",
         "subjects": [("church", 0.30, 0.15, 0.78), ("rowboat", 0.68, 0.06, 0.92)]},
        {"role": "village", "time": ["day", "dusk"], "weather": "none",
         "caption": None,
         "subjects": [("home", 0.26, 0.13, 0.82), ("well", 0.58, 0.08, 0.90)]},
        {"role": "water", "time": ["storm", "night"], "weather": "rain",
         "caption": None,
         "subjects": [("church", 0.42, 0.13, 0.76)]},
        {"role": "water", "time": ["moonlit", "night"], "weather": "mist",
         "caption": None,
         "subjects": [("rowboat", 0.46, 0.07, 0.72), ("hero", 0.46, 0.05, 0.70)]},
        {"role": "water", "time": "underworld", "weather": "none",
         "caption": "Under the water",
         "subjects": [("being", 0.50, "being", 0.80), ("ruin", 0.20, 0.12, 0.86)]},
        {"role": "water", "time": ["dawn", "winter"], "weather": "mist",
         "caption": None,
         "subjects": [("rowboat", 0.52, 0.06, 0.88)]},
    ],
    "arc": [
        {"mode": "open", "scene": 0, "count": 2, "grow": True, "lines": [
            "There is a village under {water} at {place}. Everybody there will tell you so.",
            "They will point at a flat place in the middle and say the church was there.",
            "On still evenings in {season}, people at {place} say you can hear a bell out on the water.",
            "It is always somebody's grandfather who heard it, and always on a night like tonight.",
        ]},
        {"mode": "tell", "scene": 1, "count": 3, "grow": True, "pool": "land", "lines": [
            "The story is that there was a village there, and it was a rich one, and it stopped being careful.",
            "There was a spring in the middle of it that had to be covered every night, and one night it was not.",
            "The water came up through the floors before anybody was properly awake.",
            "Some got out. They went up the slope and stood there and watched their own roofs go under.",
            "By morning there was water where there had been a street, and it has been there since.",
        ]},
        {"mode": "tell", "scene": 1, "count": 2, "grow": True, "pool": "waiting", "lines": [
            "That was a long time ago and the details have been argued about ever since.",
            "The people at {place} now are descended from the ones who got up the slope, or they say they are.",
            "Nobody builds on the low ground, and nobody can tell you exactly why not.",
        ]},
        {"mode": "turn", "scene": 2, "count": 1, "lines": [
            "{Hero} was {a_role} at {place}, and did not believe a word of it.",
            "Then there was a {season} when the water dropped further than anyone living had seen.",
        ]},
        {"mode": "tell", "scene": 2, "count": 3, "grow": True, "lines": [
            "There were stones showing out in the middle that were too square to be stones.",
            "{Hero} rowed out to look at them, because somebody was going to.",
            "{He} found a wall, and a corner, and a step going down into the water.",
            "{He} came back and said nothing, and went out again the next night, alone.",
            "{He} took {token} with {him}, which {his} mother had made {him} carry since {he} was small.",
        ]},
        {"mode": "turn", "scene": 3, "count": 1, "lines": [
            "On the third night, out over the middle, {he} heard the bell.",
            "It came up through the bottom of the boat before it came through the air.",
        ]},
        {"mode": "tell", "scene": 3, "count": 3, "grow": True, "pool": "dread", "lines": [
            "It was not a sound that moved. It was underneath {him} and it stayed underneath {him}.",
            "It rang the hour, and then it rang it again, and the second time it was slower.",
            "The water was flat. There was nothing on it in any direction.",
            "{He} sat with the oars up and let it ring and did not once think of rowing.",
        ]},
        {"mode": "tell", "scene": 4, "count": 3, "grow": True, "lines": [
            "Then somebody came up beside the boat, out of the water, without any water running off them.",
            "It was {being}, and it looked at {him} the way you look at somebody who is late.",
            "It asked {him} whether the village was still up there on the hill.",
            "{Hero} said that it was. It asked whether the spring was still covered.",
            "{He} said that {he} did not know, and that was the wrong answer, and {he} knew it while {he} was saying it.",
        ]},
        {"mode": "speech", "scene": 4, "count": 1, "lines": [
            "\"Then go and look,\" it said. \"We did not know either.\"",
            "\"Tell them what it sounds like from out here,\" it said. \"They will not listen, but tell them.\"",
        ]},
        {"mode": "tell", "scene": 4, "count": 2, "grow": True, "lines": [
            "The bell stopped in the middle of a stroke, the way a bell does when a hand is put on it.",
            "{He} rowed back with the light coming up behind {him} and did not look down once.",
            "{He} was at the spring above {place} before {he} had dried off.",
        ]},
        {"mode": "close", "scene": 5, "count": 3, "grow": True, "pool": "aftermath", "lines": [
            "The cover on the spring at {place} was rotten through, and had been for years.",
            "{He} put a new one on it that week, in oak, and the village paid for it without being asked twice.",
            "It is checked every {season} now, by whoever holds the office, and there is an office for it.",
            "{Hero} went out on the water for another forty years and never heard the bell again.",
            "{He} said that was the point, and people who had not been there thought {he} was being modest.",
        ]},
        {"mode": "moral", "scene": 5, "count": 1, "lines": [
            "Most of what the old stories warn about is maintenance.",
            "A village does not drown all at once. It drowns over the years in which nobody checks.",
            "They still tell it at {place}, and they still cover the spring, and both of those are the same story.",
        ]},
    ],
}


PATTERNS = [BARGAIN, ONE_RULE, NIGHT_ROAD, BEAST_SPARED, HOLLOW_HILL, DROWNED_BELL]
