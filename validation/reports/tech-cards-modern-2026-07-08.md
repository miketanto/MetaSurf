# What cards are good against each archetype — modern — 2026-07-08

Card-level within-archetype, matchup-conditioned DiD (the §4c honest design at card granularity). 347438 directed decided non-mirror rows. A card is scored only where it appears in >= 40 decided rows vs the archetype across >= 3 player archetypes. `A-specific` = how much more the card lifts a deck's winrate vs this archetype than vs the field. Deterministic. Cards tagged `land / deck-proxy` are manabase that rides deck-type correlation, not answers — read past them.

All numbers printed by `python -m validation.tech_finder.card_report --format modern`.

## vs Aggro  (387 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Toxic Deluge | +0.1232 | +0.1082 | -0.0150 | 5 | 238 | — |
| Flame Blitz | +0.1109 | +0.0801 | -0.0308 | 3 | 189 | — |
| Darksteel Citadel | +0.1099 | +0.0938 | -0.0161 | 3 | 527 | land / deck-proxy |
| Sink into Stupor // Soporific Springs | +0.0961 | +0.0831 | -0.0130 | 8 | 498 | land / deck-proxy |
| Disruptor Flute | +0.0938 | +0.1012 | +0.0074 | 3 | 192 | — |
| Kataki, War's Wage | +0.0933 | +0.0805 | -0.0128 | 5 | 214 | — |
| Pyrite Spellbomb | +0.0919 | +0.0854 | -0.0065 | 6 | 689 | creature_removal |
| Ranger-Captain of Eos | +0.0918 | +0.0928 | +0.0010 | 3 | 126 | — |
| Demolition Field | +0.0898 | +0.1266 | +0.0368 | 3 | 366 | land_destruction |
| Tarmogoyf | +0.0875 | +0.0531 | -0.0344 | 4 | 983 | — |
| Break the Ice | +0.0866 | +0.0823 | -0.0043 | 5 | 202 | land_destruction |
| Gaddock Teeg | +0.0853 | +0.0963 | +0.0110 | 4 | 165 | — |
| Skyclave Apparition | +0.0850 | +0.0776 | -0.0074 | 10 | 624 | — |
| Grist, the Hunger Tide | +0.0809 | +0.0176 | -0.0632 | 3 | 159 | creature_removal |
| Run Afoul | +0.0805 | +0.0548 | -0.0257 | 3 | 110 | creature_removal |

## vs GenericMidrange  (276 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Anger of the Gods | +0.1542 | +0.1232 | -0.0310 | 4 | 180 | board_sweeper |
| Wrath of the Skies | +0.1132 | +0.0913 | -0.0219 | 3 | 138 | — |
| Inti, Seneschal of the Sun | +0.1129 | +0.1199 | +0.0070 | 3 | 84 | — |
| Sword of Fire and Ice | +0.0997 | +0.1071 | +0.0074 | 3 | 289 | creature_removal |
| Legion's End | +0.0820 | +0.0909 | +0.0089 | 3 | 671 | creature_removal, hand_disruption |
| Pyroclasm | +0.0814 | +0.0418 | -0.0395 | 3 | 72 | board_sweeper |
| Reclamation Sage | +0.0810 | +0.0862 | +0.0052 | 4 | 646 | artifact_enchant_removal |
| Thought Scour | +0.0799 | +0.0762 | -0.0038 | 3 | 137 | — |
| Agatha's Soul Cauldron | +0.0759 | +0.0640 | -0.0119 | 3 | 958 | graveyard_hate |
| Yorion, Sky Nomad | +0.0744 | +0.0999 | +0.0255 | 4 | 359 | — |
| Batterskull | +0.0691 | +0.1065 | +0.0374 | 3 | 136 | — |
| Tourach, Dread Cantor | +0.0672 | +0.0695 | +0.0023 | 4 | 420 | hand_disruption |
| Kozilek, Butcher of Truth | +0.0655 | +0.0643 | -0.0012 | 3 | 266 | — |
| Ice-Fang Coatl | +0.0653 | +0.0880 | +0.0227 | 4 | 342 | — |
| Abundant Growth | +0.0648 | +0.0937 | +0.0288 | 3 | 456 | — |

## vs Footfalls  (214 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Demolition Field | +0.1635 | +0.1534 | -0.0101 | 3 | 282 | land_destruction |
| Undercity Sewers | +0.1169 | +0.1342 | +0.0173 | 3 | 233 | land / deck-proxy |
| Aether Spellbomb | +0.1041 | +0.1246 | +0.0205 | 3 | 339 | — |
| Temporary Lockdown | +0.1000 | +0.1210 | +0.0210 | 3 | 98 | board_sweeper |
| Hedge Maze | +0.0928 | +0.1050 | +0.0123 | 4 | 473 | land / deck-proxy |
| Meticulous Archive | +0.0925 | +0.1114 | +0.0189 | 4 | 380 | land / deck-proxy |
| Kaheera, the Orphanguard | +0.0843 | +0.1073 | +0.0230 | 3 | 666 | — |
| Pendelhaven | +0.0802 | +0.0936 | +0.0134 | 3 | 1756 | land / deck-proxy |
| Explore | +0.0744 | +0.0670 | -0.0074 | 3 | 734 | — |
| Aether Gust | +0.0741 | +0.1094 | +0.0353 | 5 | 388 | — |
| Agatha's Soul Cauldron | +0.0732 | +0.0668 | -0.0064 | 3 | 1706 | graveyard_hate |
| Drannith Magistrate | +0.0697 | +0.0706 | +0.0009 | 6 | 1035 | — |
| Jetmir's Garden | +0.0641 | +0.0505 | -0.0136 | 4 | 549 | land / deck-proxy |
| Minamo, School at Water's Edge | +0.0624 | +0.0814 | +0.0190 | 6 | 700 | land / deck-proxy |
| Commercial District | +0.0600 | +0.0594 | -0.0006 | 5 | 220 | land / deck-proxy |

## vs Titan  (262 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Harbinger of the Seas | +0.1978 | +0.1852 | -0.0126 | 3 | 563 | mana_denial |
| Spirebluff Canal | +0.1940 | +0.2027 | +0.0087 | 6 | 1811 | land / deck-proxy |
| Counterspell | +0.1888 | +0.1921 | +0.0033 | 8 | 2740 | counter_spell |
| Dragon's Rage Channeler | +0.1757 | +0.1850 | +0.0093 | 5 | 1832 | — |
| Mishra's Bauble | +0.1745 | +0.1845 | +0.0100 | 9 | 2184 | — |
| Ledger Shredder | +0.1620 | +0.1711 | +0.0091 | 4 | 1035 | — |
| Murktide Regent | +0.1555 | +0.1530 | -0.0026 | 6 | 2586 | — |
| Blood Moon | +0.1529 | +0.1618 | +0.0089 | 12 | 3955 | mana_denial |
| Expressive Iteration | +0.1526 | +0.1688 | +0.0162 | 9 | 2290 | — |
| Unholy Heat | +0.1484 | +0.1623 | +0.0139 | 9 | 2725 | creature_removal |
| Subtlety | +0.1466 | +0.1607 | +0.0141 | 13 | 3590 | — |
| Ragavan, Nimble Pilferer | +0.1341 | +0.1488 | +0.0146 | 10 | 4611 | — |
| Dress Down | +0.1337 | +0.1496 | +0.0159 | 10 | 2029 | — |
| Consider | +0.1299 | +0.1385 | +0.0086 | 4 | 1258 | — |
| Steam Vents | +0.1276 | +0.1367 | +0.0091 | 14 | 4901 | land / deck-proxy |

## vs Yawgmoth  (208 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Malevolent Rumble | +0.1539 | +0.1680 | +0.0141 | 3 | 297 | — |
| Utopia Sprawl | +0.1051 | +0.1051 | +0.0000 | 3 | 212 | — |
| Karn, the Great Creator | +0.0996 | +0.0805 | -0.0190 | 3 | 181 | — |
| Pyroclasm | +0.0962 | +0.0762 | -0.0199 | 3 | 120 | board_sweeper |
| Phlage, Titan of Fire's Fury | +0.0939 | +0.0855 | -0.0084 | 4 | 166 | creature_removal |
| Galvanic Discharge | +0.0902 | +0.0945 | +0.0043 | 3 | 441 | — |
| Consign to Memory | +0.0844 | +0.0969 | +0.0126 | 9 | 478 | counter_ability, counter_spell |
| Cityscape Leveler | +0.0821 | +0.0793 | -0.0028 | 3 | 777 | — |
| Remand | +0.0806 | +0.0915 | +0.0110 | 3 | 79 | counter_spell |
| Unmoored Ego | +0.0788 | +0.0568 | -0.0220 | 3 | 98 | graveyard_hate |
| The Stone Brain | +0.0784 | +0.0789 | +0.0005 | 6 | 978 | graveyard_hate |
| Tourach, Dread Cantor | +0.0758 | +0.0972 | +0.0214 | 3 | 577 | hand_disruption |
| Walking Ballista | +0.0756 | +0.0459 | -0.0297 | 5 | 893 | creature_removal |
| Portable Hole | +0.0713 | +0.0944 | +0.0231 | 3 | 112 | artifact_enchant_removal, creature_removal |
| Liquimetal Coating | +0.0691 | +0.0566 | -0.0126 | 5 | 1003 | — |

## vs GenericTron  (267 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Sunbaked Canyon | +0.1358 | +0.1143 | -0.0215 | 3 | 799 | land / deck-proxy |
| Ignoble Hierarch | +0.1051 | +0.1004 | -0.0048 | 3 | 610 | — |
| Collector Ouphe | +0.0974 | +0.0505 | -0.0469 | 3 | 151 | — |
| Spreading Seas | +0.0925 | +0.0955 | +0.0030 | 4 | 318 | — |
| Sanctifier en-Vec | +0.0925 | +0.0686 | -0.0239 | 6 | 1050 | — |
| The Stone Brain | +0.0877 | +0.0751 | -0.0126 | 4 | 333 | graveyard_hate |
| Void Mirror | +0.0860 | +0.0898 | +0.0039 | 5 | 251 | — |
| Ensnaring Bridge | +0.0856 | +0.0696 | -0.0160 | 5 | 459 | — |
| Torpor Orb | +0.0791 | +0.0437 | -0.0354 | 4 | 117 | — |
| Arena of Glory | +0.0779 | +0.0739 | -0.0040 | 3 | 637 | land / deck-proxy |
| Sheoldred's Edict | +0.0726 | +0.0768 | +0.0041 | 6 | 363 | creature_removal |
| Obsidian Charmaw | +0.0698 | +0.0578 | -0.0121 | 10 | 856 | land_destruction |
| Thought Scour | +0.0624 | +0.0513 | -0.0111 | 3 | 157 | — |
| Molten Collapse | +0.0618 | +0.0608 | -0.0010 | 3 | 304 | creature_removal |
| Sacred Foundry | +0.0594 | +0.0397 | -0.0197 | 14 | 2700 | land / deck-proxy |

## vs Energy  (178 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Persist | +0.1525 | +0.1007 | -0.0519 | 3 | 109 | — |
| Kozilek's Return | +0.1417 | +0.1216 | -0.0202 | 4 | 1700 | board_sweeper |
| Meltdown | +0.1296 | +0.0975 | -0.0322 | 6 | 266 | — |
| Ketramose, the New Dawn | +0.0910 | +0.0385 | -0.0526 | 3 | 523 | — |
| Snow-Covered Island | +0.0872 | +0.0909 | +0.0037 | 3 | 84 | land / deck-proxy |
| Tarfire | +0.0860 | +0.0984 | +0.0124 | 3 | 155 | creature_removal |
| Galvanic Discharge | +0.0825 | +0.0621 | -0.0203 | 3 | 476 | — |
| Wrath of the Skies | +0.0810 | +0.0722 | -0.0087 | 6 | 1867 | — |
| Temple Garden | +0.0724 | +0.0196 | -0.0528 | 3 | 216 | land / deck-proxy |
| Ghost Quarter | +0.0714 | +0.0603 | -0.0111 | 3 | 742 | land_destruction |
| Commandeer | +0.0703 | +0.1100 | +0.0397 | 3 | 273 | — |
| Molten Collapse | +0.0681 | +0.0723 | +0.0042 | 3 | 105 | creature_removal |
| Green Sun's Zenith | +0.0681 | +0.0417 | -0.0264 | 4 | 827 | — |
| Arid Mesa | +0.0679 | +0.0636 | -0.0043 | 12 | 2429 | land / deck-proxy |
| Graveyard Trespasser // Graveyard Glutton | +0.0635 | +0.0588 | -0.0047 | 3 | 541 | — |

## vs HammerTime  (207 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Thrun, the Last Troll | +0.1283 | +0.1197 | -0.0086 | 3 | 92 | — |
| Unmoored Ego | +0.0846 | +0.0852 | +0.0005 | 5 | 208 | graveyard_hate |
| Elesh Norn, Mother of Machines | +0.0778 | +0.0413 | -0.0365 | 6 | 508 | — |
| Leyline Binding | +0.0739 | +0.0562 | -0.0177 | 7 | 1554 | artifact_enchant_removal, creature_removal |
| Prismatic Vista | +0.0734 | +0.0783 | +0.0049 | 3 | 84 | land / deck-proxy |
| Anger of the Gods | +0.0730 | +0.0699 | -0.0030 | 3 | 85 | board_sweeper |
| Crumble to Dust | +0.0691 | +0.0375 | -0.0316 | 3 | 110 | — |
| Yavimaya, Cradle of Growth | +0.0686 | +0.0468 | -0.0218 | 3 | 347 | land / deck-proxy |
| Stern Scolding | +0.0666 | +0.0716 | +0.0050 | 8 | 530 | counter_spell |
| Lavinia, Azorius Renegade | +0.0648 | +0.0489 | -0.0159 | 3 | 135 | — |
| Waterlogged Grove | +0.0647 | +0.0783 | +0.0136 | 3 | 223 | land / deck-proxy |
| Aether Spellbomb | +0.0634 | +0.0816 | +0.0183 | 3 | 368 | — |
| Field of Ruin | +0.0619 | +0.0375 | -0.0244 | 3 | 94 | land_destruction |
| Dovin's Veto | +0.0594 | +0.0580 | -0.0014 | 3 | 729 | counter_spell |
| Seachrome Coast | +0.0591 | +0.1251 | +0.0661 | 3 | 90 | land / deck-proxy |

## vs Azorius Control  (219 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Aether Gust | +0.1348 | +0.1640 | +0.0292 | 4 | 172 | — |
| Ensnaring Bridge | +0.1131 | +0.1071 | -0.0060 | 5 | 773 | — |
| Phyrexian Crusader | +0.1094 | +0.1117 | +0.0023 | 3 | 77 | — |
| Abundant Growth | +0.1031 | +0.1331 | +0.0300 | 3 | 334 | — |
| Wrath of the Skies | +0.0998 | +0.0748 | -0.0250 | 4 | 291 | — |
| Karn, the Great Creator | +0.0970 | +0.0827 | -0.0143 | 4 | 753 | — |
| Bonecrusher Giant // Stomp | +0.0824 | +0.0917 | +0.0093 | 7 | 592 | — |
| Snow-Covered Forest | +0.0804 | +0.0970 | +0.0166 | 6 | 424 | land / deck-proxy |
| Drown in the Loch | +0.0765 | +0.0638 | -0.0127 | 3 | 324 | counter_spell, creature_removal |
| Tormod's Crypt | +0.0764 | +0.0718 | -0.0046 | 10 | 1188 | graveyard_hate |
| Snow-Covered Plains | +0.0725 | +0.0909 | +0.0185 | 3 | 405 | land / deck-proxy |
| Sheoldred, the Apocalypse | +0.0674 | +0.0832 | +0.0158 | 6 | 698 | — |
| Torpor Orb | +0.0666 | +0.0458 | -0.0208 | 4 | 312 | — |
| Utopia Sprawl | +0.0665 | +0.0714 | +0.0049 | 3 | 253 | — |
| Wurmcoil Engine | +0.0655 | +0.0563 | -0.0092 | 3 | 493 | — |

## vs GrindingBreach  (172 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Tishana's Tidebinder | +0.1987 | +0.2045 | +0.0058 | 3 | 114 | counter_ability |
| Snow-Covered Mountain | +0.1261 | +0.1250 | -0.0011 | 3 | 113 | land / deck-proxy |
| Go for the Throat | +0.1207 | +0.1359 | +0.0152 | 3 | 69 | creature_removal |
| Sheoldred, the Apocalypse | +0.1187 | +0.1371 | +0.0184 | 3 | 192 | — |
| Pest Control | +0.0978 | +0.0740 | -0.0237 | 5 | 525 | — |
| Hidetsugu Consumes All // Vessel of the All-Consuming | +0.0968 | +0.1093 | +0.0126 | 3 | 221 | — |
| Orim's Chant | +0.0905 | +0.0754 | -0.0151 | 8 | 1915 | — |
| Tune the Narrative | +0.0887 | +0.0728 | -0.0160 | 3 | 188 | — |
| Kaheera, the Orphanguard | +0.0860 | +0.1178 | +0.0318 | 3 | 235 | — |
| Dauthi Voidwalker | +0.0852 | +0.0764 | -0.0088 | 5 | 552 | graveyard_hate |
| Shadowspear | +0.0832 | +0.0823 | -0.0010 | 3 | 134 | — |
| Aether Gust | +0.0806 | +0.1187 | +0.0381 | 3 | 95 | — |
| Lórien Revealed | +0.0764 | +0.0777 | +0.0014 | 3 | 240 | — |
| Path to Exile | +0.0759 | +0.0546 | -0.0213 | 5 | 442 | creature_removal |
| Celestial Purge | +0.0732 | +0.0715 | -0.0017 | 8 | 688 | — |

## vs LivingEnd  (180 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Urza's Saga | +0.1017 | +0.0982 | -0.0034 | 3 | 385 | land / deck-proxy |
| Karn, the Great Creator | +0.1016 | +0.0825 | -0.0190 | 3 | 87 | — |
| The Stone Brain | +0.0901 | +0.0846 | -0.0054 | 5 | 566 | graveyard_hate |
| Shifting Woodland | +0.0817 | +0.1112 | +0.0295 | 3 | 95 | land / deck-proxy |
| Seasoned Pyromancer | +0.0775 | +0.0993 | +0.0218 | 4 | 655 | — |
| Urborg, Tomb of Yawgmoth | +0.0665 | +0.0500 | -0.0165 | 3 | 244 | land / deck-proxy |
| Kaheera, the Orphanguard | +0.0628 | +0.0924 | +0.0296 | 3 | 353 | — |
| Liquimetal Coating | +0.0588 | +0.0522 | -0.0067 | 5 | 685 | — |
| Minamo, School at Water's Edge | +0.0574 | +0.0786 | +0.0212 | 4 | 325 | land / deck-proxy |
| Preordain | +0.0560 | +0.0618 | +0.0058 | 8 | 660 | — |
| Inti, Seneschal of the Sun | +0.0551 | +0.0679 | +0.0128 | 3 | 74 | — |
| Meticulous Archive | +0.0541 | +0.0674 | +0.0133 | 4 | 293 | land / deck-proxy |
| Endurance | +0.0536 | +0.0430 | -0.0106 | 8 | 2852 | graveyard_hate |
| Ensnaring Bridge | +0.0515 | +0.0450 | -0.0065 | 4 | 714 | — |
| Necromentia | +0.0514 | +0.0584 | +0.0070 | 3 | 356 | graveyard_hate |

## vs OmnathControl  (182 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Phyrexian Metamorph | +0.1476 | +0.1453 | -0.0023 | 4 | 236 | — |
| Sunbaked Canyon | +0.1401 | +0.1227 | -0.0175 | 4 | 703 | land / deck-proxy |
| Sacred Foundry | +0.1171 | +0.0933 | -0.0238 | 10 | 1366 | land / deck-proxy |
| Lurrus of the Dream-Den | +0.1000 | +0.1278 | +0.0279 | 4 | 272 | — |
| Arid Mesa | +0.0956 | +0.0739 | -0.0217 | 10 | 1681 | land / deck-proxy |
| Flame Slash | +0.0929 | +0.0910 | -0.0018 | 4 | 95 | creature_removal |
| Wear // Tear | +0.0815 | +0.0663 | -0.0152 | 8 | 861 | — |
| Sanctifier en-Vec | +0.0815 | +0.0598 | -0.0217 | 5 | 944 | — |
| Minamo, School at Water's Edge | +0.0814 | +0.1070 | +0.0256 | 3 | 219 | land / deck-proxy |
| Leyline Binding | +0.0736 | +0.0657 | -0.0079 | 6 | 696 | artifact_enchant_removal, creature_removal |
| The One Ring | +0.0690 | +0.0781 | +0.0091 | 13 | 1158 | — |
| Nettlecyst | +0.0679 | +0.0740 | +0.0061 | 3 | 351 | — |
| The Stone Brain | +0.0668 | +0.0646 | -0.0022 | 4 | 485 | graveyard_hate |
| Lórien Revealed | +0.0658 | +0.0613 | -0.0045 | 4 | 761 | — |
| Lightning Bolt | +0.0578 | +0.0808 | +0.0230 | 10 | 1870 | creature_removal |
