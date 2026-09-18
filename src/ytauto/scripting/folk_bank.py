"""De grondstof voor de gratis verteller: tradities, namen en beelden.

Hier staat geen verhaal in. Hier staat waar een verhaal uit gemaakt wordt:
uit welke streek het komt, hoe de mensen daar heten, welke wezens er in de
verhalen van die streek voorkomen en hoe het landschap eruitziet.

De opbouw van een verhaal staat in `folk_patterns.py`; het aan elkaar zetten
gebeurt in `local_writer.py`.

Twee dingen zijn met opzet zo gedaan:

  * Elk wezen heeft een `draw` die bestaat als silhouet. De renderer kan
    dus nooit gevraagd worden iets te tekenen wat er niet is.
  * De tradities zijn allemaal breed gepubliceerde, eeuwenoude verhaal-
    stof. Verhalen met een levende heilige of ceremoniële betekenis staan
    hier bewust niet in; dat is geen materiaal voor een kanaal.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
#  Tradities
# ---------------------------------------------------------------------------
#
#  settings  : welke landschappen bij deze streek passen (uit story_scene)
#  beings    : het wezen dat het verhaal in beweging zet. `draw` is het
#              silhouet, `short` de naam zoals hij verderop in de tekst
#              terugkomt.
#  source    : de bronvermelding aan het eind van de video.

TRADITIONS = [
    {
        "key": "norse",
        "musicians": ["fiddler", "horn blower"],
        "origin": "Norway",
        "adjective": "Norwegian",
        "label": "A tale from the Norwegian fjords",
        "source": (
            "This story belongs to the farms and fishing stations of western "
            "Norway, where versions of it were collected in the eighteen "
            "hundreds. It has been retold here in our own words."
        ),
        "settings": ["mountains", "coast", "valley", "lake", "cliffs"],
        "wild": ["the pine woods", "the high pasture", "the birch scrub",
                 "the stone fields above the farm"],
        "water": ["the fjord", "the black lake", "the cold river", "the sound"],
        "places": ["Sunndal", "Hovden", "Rjukan", "Vassenden", "Undredal",
                   "Storfjord", "Bergsdal", "Aurland"],
        "men": ["Eirik", "Halvor", "Sigurd", "Olav", "Tarald", "Gunnar", "Anders"],
        "women": ["Sigrid", "Ingeborg", "Ragnhild", "Astrid", "Marit", "Solveig"],
        "roles": ["ferryman", "charcoal burner", "boat builder", "herder",
                  "net mender", "smith"],
        "homes": ["a turf-roofed cottage", "a low house of grey timber",
                  "a cabin at the water's edge"],
        "beings": [
            {"name": "a troll", "short": "the troll", "draw": "giant",
             "lives": "under the bridge", "scale": 0.24},
            {"name": "a grey shape no taller than a child", "short": "the grey shape",
             "draw": "child", "lives": "in the scree", "scale": 0.10},
            {"name": "something in the water", "short": "the thing in the water",
             "draw": "rowboat", "lives": "in the sound", "scale": 0.08},
        ],
        "beasts": ["a grey wolf", "a white reindeer", "a raven with one eye"],
    },
    {
        "key": "irish",
        "musicians": ["fiddler", "piper"],
        "origin": "Ireland",
        "adjective": "Irish",
        "label": "A tale from the west of Ireland",
        "source": (
            "This story comes from the west of Ireland, where it was gathered "
            "from tellers who had it from their own grandparents. The words "
            "here are ours; the tale is theirs."
        ),
        "settings": ["moor", "hills", "coast", "lake", "village"],
        "wild": ["the bog", "the whitethorn field", "the low hills",
                 "the rushes behind the house"],
        "water": ["the lough", "the grey sea", "the stream below the road"],
        "places": ["Ballyvaughan", "Kilfenora", "Dooagh", "Glencolumb",
                   "Carrowmore", "Inisheer", "Lisdoon"],
        "men": ["Seamus", "Fergal", "Donal", "Padraig", "Cormac", "Brendan"],
        "women": ["Nuala", "Aoife", "Maire", "Brigid", "Sorcha", "Eithne"],
        "roles": ["fiddler", "turf cutter", "weaver", "cowherd", "thatcher",
                  "boatman"],
        "homes": ["a whitewashed cottage", "a house of two rooms and a half door",
                  "a cabin with the thatch going green"],
        "beings": [
            {"name": "a woman in a green cloak", "short": "the woman in green",
             "draw": "woman", "lives": "beyond the whitethorn", "scale": 0.13},
            {"name": "a rider on a white horse", "short": "the rider",
             "draw": "rider", "lives": "on the old road", "scale": 0.14},
            {"name": "a hare that would not run", "short": "the hare",
             "draw": "fox", "lives": "in the far field", "scale": 0.07},
        ],
        "beasts": ["a red fox", "a heron", "a black dog"],
    },
    {
        "key": "german",
        "musicians": ["fiddler", "organ blower"],
        "origin": "Germany",
        "adjective": "German",
        "label": "A tale from the German forests",
        "source": (
            "Versions of this story were written down in Germany in the early "
            "eighteen hundreds, when collectors began taking down what people "
            "still told at the fireside. This retelling is our own."
        ),
        "settings": ["forest", "village", "hills", "valley", "mountains"],
        "wild": ["the spruce forest", "the charcoal clearing", "the deer paths",
                 "the wood above the mill"],
        "water": ["the mill stream", "the green river", "the forest pond"],
        "places": ["Dornstadt", "Waldheim", "Brunnenbach", "Steinau",
                   "Ilsenburg", "Hohenroda"],
        "men": ["Konrad", "Wilhelm", "Matthias", "Hans", "Gerhard", "Lorenz"],
        "women": ["Katrin", "Elsbeth", "Margarethe", "Johanna", "Liesel"],
        "roles": ["miller", "woodcutter", "carter", "glassblower",
                  "forester", "cooper"],
        "homes": ["a mill house", "a timbered cottage", "a house at the forest edge"],
        "beings": [
            {"name": "an old man with a green hat", "short": "the old man",
             "draw": "monk", "lives": "in the deep wood", "scale": 0.13},
            {"name": "a wolf that walked like a person", "short": "the wolf",
             "draw": "wolf", "lives": "beyond the ridge", "scale": 0.09},
            {"name": "a girl at the well who cast no shadow", "short": "the girl at the well",
             "draw": "child", "lives": "by the well", "scale": 0.10},
        ],
        "beasts": ["a wild boar", "a white stag", "a raven"],
    },
    {
        "key": "slavic",
        "musicians": ["piper", "fiddler"],
        "origin": "the Carpathians",
        "adjective": "Carpathian",
        "label": "A tale from the Carpathian villages",
        "source": (
            "This story was told in the villages of the Carpathian mountains, "
            "where the same tale is found under a dozen different names. We "
            "have retold it in our own words."
        ),
        "settings": ["forest", "mountains", "village", "plain", "valley"],
        "wild": ["the birch forest", "the long meadow", "the fir slopes",
                 "the rye fields"],
        "water": ["the river", "the mill pond", "the spring under the rock"],
        "places": ["Verkhovyna", "Zvolen", "Rakhiv", "Bystra", "Kolochava",
                   "Podhale"],
        "men": ["Jurko", "Milan", "Stefan", "Vasyl", "Tomasz", "Bogdan"],
        "women": ["Zofia", "Halyna", "Marika", "Ludmila", "Katarzyna"],
        "roles": ["shepherd", "wheelwright", "beekeeper", "raftsman",
                  "herb gatherer", "ploughman"],
        "homes": ["a low house with a thatched roof", "a shepherd's hut",
                  "a cottage behind a fence of split logs"],
        "beings": [
            {"name": "a woman with wet hair", "short": "the woman",
             "draw": "woman", "lives": "by the river", "scale": 0.12},
            {"name": "an old man of the forest", "short": "the forest man",
             "draw": "giant", "lives": "in the deep fir", "scale": 0.20},
            {"name": "a grey wolf that spoke", "short": "the wolf",
             "draw": "wolf", "lives": "on the ridge", "scale": 0.09},
        ],
        "beasts": ["a brown bear", "a stork", "a grey wolf"],
    },
    {
        "key": "japanese",
        "musicians": ["flute player", "drum keeper"],
        "origin": "Japan",
        "adjective": "Japanese",
        "label": "A tale from the Japanese countryside",
        "source": (
            "This story comes from the Japanese countryside, from the kind of "
            "tale told to explain a bend in a road or a shrine on a hill. The "
            "retelling here is our own."
        ),
        "settings": ["mountains", "forest", "village", "coast", "valley"],
        "wild": ["the cedar slope", "the bamboo grove", "the terraced fields",
                 "the pass above the village"],
        "water": ["the river", "the grey sea", "the still pool"],
        "places": ["Kurokawa", "Tanigawa", "Hoshino", "Akeno", "Shirakami",
                   "Nagase"],
        "men": ["Tarou", "Kenji", "Shiro", "Hideo", "Masaru", "Ryou"],
        "women": ["Yuki", "Sachi", "Hana", "Tomoe", "Kiyo", "Mitsu"],
        "roles": ["charcoal maker", "papermaker", "fisherman", "woodcutter",
                  "innkeeper", "bell ringer"],
        "homes": ["a house of wood and paper", "a farmhouse under a thatched roof",
                  "a small house at the foot of the pass"],
        "beings": [
            {"name": "a woman in white", "short": "the woman in white",
             "draw": "woman", "lives": "in the snow country", "scale": 0.12},
            {"name": "a fox with too many tails", "short": "the fox",
             "draw": "fox", "lives": "by the shrine", "scale": 0.07},
            {"name": "a traveller with a wide hat", "short": "the traveller",
             "draw": "traveller", "lives": "on the mountain road", "scale": 0.12},
        ],
        "beasts": ["a crane", "a wild boar", "a red fox"],
    },
    {
        "key": "greek",
        "musicians": ["lyre player", "fiddler"],
        "origin": "Greece",
        "adjective": "Greek",
        "label": "A tale from the Greek islands",
        "source": (
            "This story was told on the Greek islands, where older gods and "
            "newer saints share the same coastline. It has been retold here "
            "in our own words."
        ),
        "settings": ["coast", "cliffs", "hills", "village", "plain"],
        "wild": ["the olive terraces", "the dry hills", "the thyme slopes",
                 "the stone walls above the bay"],
        "water": ["the sea", "the harbour", "the spring below the chapel"],
        "places": ["Kalamos", "Vathy", "Ikaria", "Skopelos", "Molyvos", "Naxos"],
        "men": ["Stavros", "Nikos", "Andreas", "Petros", "Manolis", "Yannis"],
        "women": ["Eleni", "Maria", "Sofia", "Chrysa", "Athina", "Despina"],
        "roles": ["sponge diver", "goatherd", "sailmaker", "olive grower",
                  "boatman", "lamplighter"],
        "homes": ["a house of whitewashed stone", "a cottage above the harbour",
                  "a two-room house with a flat roof"],
        "beings": [
            {"name": "a woman who came up out of the sea", "short": "the woman from the sea",
             "draw": "woman", "lives": "past the harbour mouth", "scale": 0.12},
            {"name": "an old man nobody in the village knew", "short": "the old man",
             "draw": "monk", "lives": "on the headland", "scale": 0.12},
            {"name": "a ship with no crew", "short": "the ship",
             "draw": "ship", "lives": "out past the point", "scale": 0.11},
        ],
        "beasts": ["a sea eagle", "a white goat", "a grey heron"],
    },
    {
        "key": "finnish",
        "musicians": ["kantele player", "fiddler"],
        "origin": "Finland",
        "adjective": "Finnish",
        "label": "A tale from the Finnish lakes",
        "source": (
            "This story comes from the lake country of Finland, from the long "
            "winter evenings when there was nothing to do but tell. The words "
            "here are ours."
        ),
        "settings": ["lake", "forest", "hills", "plain", "village"],
        "wild": ["the spruce forest", "the frozen marsh", "the burnt clearing",
                 "the island pines"],
        "water": ["the lake", "the narrow water", "the rapids"],
        "places": ["Nurmes", "Sotkamo", "Kuhmo", "Ilomantsi", "Rautavaara"],
        "men": ["Väinö", "Toivo", "Aarne", "Eero", "Kalle", "Onni"],
        "women": ["Aino", "Helmi", "Sirkka", "Kerttu", "Liisa"],
        "roles": ["log driver", "net fisher", "tar burner", "trapper",
                  "boat builder", "smith"],
        "homes": ["a log house", "a cabin with a stove of stacked stone",
                  "a house at the end of the lake road"],
        "beings": [
            {"name": "an old woman at the edge of the ice", "short": "the old woman",
             "draw": "woman", "lives": "out on the ice", "scale": 0.11},
            {"name": "a bear that would not be driven off", "short": "the bear",
             "draw": "bear", "lives": "in the burnt clearing", "scale": 0.11},
            {"name": "a man of the water", "short": "the man of the water",
             "draw": "man", "lives": "under the rapids", "scale": 0.11},
        ],
        "beasts": ["a lynx", "a black grouse", "an elk"],
    },
    {
        "key": "welsh",
        "musicians": ["harper", "fiddler"],
        "origin": "Wales",
        "adjective": "Welsh",
        "label": "A tale from the Welsh hills",
        "source": (
            "This story belongs to the hill farms of Wales, where it was still "
            "being told within living memory. This retelling is our own."
        ),
        "settings": ["hills", "valley", "moor", "lake", "village"],
        "wild": ["the sheep walk", "the bracken slope", "the old quarry road",
                 "the hawthorn hedge"],
        "water": ["the llyn", "the brook", "the reservoir"],
        "places": ["Nantyffin", "Cwmystwyth", "Bethesda", "Llanfair",
                   "Pontarfynach", "Trefriw"],
        "men": ["Gwilym", "Rhys", "Ieuan", "Owain", "Dafydd", "Emrys"],
        "women": ["Ceridwen", "Nesta", "Angharad", "Gwen", "Eluned"],
        "roles": ["shepherd", "slate quarrier", "drover", "boatman",
                  "carter", "blacksmith"],
        "homes": ["a long stone house", "a farmhouse with slate on three sides",
                  "a cottage set into the hillside"],
        "beings": [
            {"name": "a girl standing in the middle of the lake", "short": "the girl in the lake",
             "draw": "woman", "lives": "in the llyn", "scale": 0.11},
            {"name": "a black dog with pale eyes", "short": "the dog",
             "draw": "wolf", "lives": "on the quarry road", "scale": 0.09},
            {"name": "a harper nobody had hired", "short": "the harper",
             "draw": "traveller", "lives": "on the pass", "scale": 0.12},
        ],
        "beasts": ["a red kite", "a mountain pony", "a badger"],
    },
]


# ---------------------------------------------------------------------------
#  Voorwerpen en jaargetijden
# ---------------------------------------------------------------------------

TOKENS = [
    "a ring of grey iron", "a knife with a horn handle", "a silver coin",
    "a comb of white bone", "a length of red thread", "a key with no lock",
    "a stone with a hole worn through it", "a cup of dark wood",
    "a bell the size of a thumb", "a strip of woven hair",
]

SEASONS = [
    "that autumn", "the spring after", "the middle of winter",
    "the end of the summer", "the last week of the harvest",
    "the first of the cold weather",
]

HOURS = [
    "before it was properly light", "while the light was going",
    "in the last of the daylight", "after the lamps were lit",
    "at the hour when the wind turns", "before the first bell",
]


# ---------------------------------------------------------------------------
#  Gedeelde losse zinnen
# ---------------------------------------------------------------------------
#
#  Deze regels horen bij geen enkel verhaal in het bijzonder. Ze worden
#  gebruikt om een verhaal op lengte te brengen als de eigen regels van het
#  patroon op zijn. Elke categorie past bij één soort moment.

TEXTURE = {
    "land": [
        "Everything at {place} is built out of what was already lying there.",
        "The walls run straight up the slope instead of across it, which tells you who made them and when.",
        "There is more sky than land in that part of the country.",
        "{water} freezes at the edges first and in the middle last, and the middle never quite.",
        "The ground there rises in long steps, and every step has a wall on it that somebody carried up stone by stone.",
        "In that country the weather comes from one direction and everybody builds with their back to it.",
        "The road went up and did not come down again for an hour.",
        "There were three houses at {place} and a fourth that nobody had lived in since before anyone could remember.",
        "From the top you could see {water} lying flat and grey, and nothing moving on it.",
        "The path to {wild} was worn to bare rock in the middle and grass at the edges.",
        "Nothing grew tall there. What grew, grew sideways.",
        "There was one tree on that slope and it leaned away from the wind like a person walking into it.",
    ],
    "work": [
        "Nobody at {place} did one thing only. There was not the work for it.",
        "The season decided what {he} did, and {he} did not argue with the season.",
        "It is skilled work that looks like no work at all, which is why it was badly paid.",
        "{He} was known for it as far as the next valley, in the small way people are known.",
        "{Hero} was up before the house and back after dark, and that was every day and not only the good ones.",
        "The work was the same on a fine morning as on a bad one, which is why nobody at {place} talked much about the weather.",
        "There is a way of doing that work that looks slow and is not, and {hero} had it.",
        "People came from the far side of {water} because the work was done properly and the price did not change.",
        "It was not a living that made anybody rich. It was a living that kept the roof on.",
        "In the good months there was more than could be finished. In the bad ones there was the mending.",
        "{Hero} kept the tools better than the house.",
    ],
    "waiting": [
        "Two winters went by in the ordinary way.",
        "Things that are not spoken about stop being true in the daytime.",
        "The story could have ended there, and for a long while it looked as though it had.",
        "{He} was busy, and being busy is the best forgetting there is.",
        "Nothing happened for a long while, and that is the part of the story people leave out.",
        "A week went by. Then another.",
        "The days closed over it the way water closes over a stone.",
        "{Hero} thought about it in the evenings and not at all during the day.",
        "For a time it seemed that it had been nothing after all.",
        "The season turned. The work changed with it, as work does.",
    ],
    "dread": [
        "The fire in the grate leaned away from nothing at all.",
        "There is a quiet that comes before weather and a quiet that does not, and this was the other one.",
        "{His} own footsteps sounded as though somebody else were making them.",
        "Afterwards {he} could not say how long it had lasted. It had been either a moment or most of the night.",
        "The dogs at {place} would not settle that night, and nobody could say why.",
        "There was a stillness on {water} that does not belong to any weather.",
        "The birds went quiet before it, the way they do before a change.",
        "It was not fear exactly. It was the feeling of standing in a room somebody has just left.",
        "The cold that came off it was not the cold of the season.",
        "Afterwards {hero} could not say what had been wrong with the light, only that something had been.",
    ],
    "travel": [
        "There is no shelter on that stretch and everybody who uses it knows the fact by heart.",
        "The wind came straight down {water} with nothing in the way of it.",
        "{He} had done the walk a hundred times and never once at that hour.",
        "It is uphill in both directions, which is a joke at {place} and also true.",
        "The way ran along {water} for a mile and then turned up into {wild}.",
        "It is four hours on foot and there is no shelter in the middle of it.",
        "{Hero} walked with the light behind and the hills coming up slowly ahead.",
        "There is one place on that road where you can see where you are going and where you have been at the same time.",
        "The last of the daylight went while there was still an hour to walk.",
        "Nobody was on the road. At that hour nobody ever was.",
    ],
    "aftermath": [
        "The priest at {place} did not like the story and could not make it stop.",
        "Two versions were still being told in that valley within living memory.",
        "Somebody wrote it down eventually, which is how it comes to be here.",
        "{Hero} lived a long time after, and worked, and was not strange about it.",
        "People at {place} told it afterwards in different ways, and every way had the same end.",
        "The story got out, as stories do, and came back changed.",
        "For years after, nobody at {place} would go that way alone after dark.",
        "The house is gone now. The wall of it is still there, up to about knee height.",
        "They still point out the place. It is not marked, but everybody knows it.",
        "What is certain is that {hero} never spoke of it again, and never had to.",
    ],
}


def texture(category: str) -> list[str]:
    return list(TEXTURE.get(category, []))


# ---------------------------------------------------------------------------
#  Welk landschap hoort bij welke plek in het verhaal
# ---------------------------------------------------------------------------
#
#  Een patroon zegt "dit speelt bij het water"; per traditie is dat een
#  ander landschap. Zo speelt hetzelfde verhaal in Noorwegen aan een fjord
#  en in Ierland op de hoogvlakte, zonder dat het patroon dat hoeft te weten.

SCENERY = {
    "norse":    {"home": "coast",   "water": "lake",   "wild": "mountains",
                 "village": "village", "high": "cliffs"},
    "irish":    {"home": "village", "water": "lake",   "wild": "moor",
                 "village": "village", "high": "coast"},
    "german":   {"home": "village", "water": "lake",   "wild": "forest",
                 "village": "village", "high": "hills"},
    "slavic":   {"home": "village", "water": "lake",   "wild": "forest",
                 "village": "village", "high": "mountains"},
    "japanese": {"home": "village", "water": "coast",  "wild": "forest",
                 "village": "village", "high": "mountains"},
    "greek":    {"home": "village", "water": "coast",  "wild": "hills",
                 "village": "village", "high": "cliffs"},
    "finnish":  {"home": "village", "water": "lake",   "wild": "forest",
                 "village": "village", "high": "hills"},
    "welsh":    {"home": "village", "water": "lake",   "wild": "moor",
                 "village": "village", "high": "hills"},
}


# ---------------------------------------------------------------------------
#  Welk beroep past bij welk soort verhaal
# ---------------------------------------------------------------------------
#
#  Een herder die zijn netten ophaalt klopt niet. Een patroon zegt daarom of
#  het bij het water speelt of in het veld; hieronder staat waar dat op slaat.

ROLE_KINDS = {
    "water": ["ferry", "boat", "net", "fisher", "raft", "sponge", "sail",
              "diver", "miller", "log driver"],
    "land": ["herd", "charcoal", "turf", "forester", "woodcutter", "trapper",
             "tar burner", "herb", "grower", "drover", "quarrier", "weaver"],
}
