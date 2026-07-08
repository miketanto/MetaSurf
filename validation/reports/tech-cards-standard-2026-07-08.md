# What cards are good against each archetype — standard — 2026-07-08

Card-level within-archetype, matchup-conditioned DiD (the §4c honest design at card granularity). 62458 directed decided non-mirror rows. A card is scored only where it appears in >= 40 decided rows vs the archetype across >= 3 player archetypes. `A-specific` = how much more the card lifts a deck's winrate vs this archetype than vs the field. Deterministic. Cards tagged `land / deck-proxy` are manabase that rides deck-type correlation, not answers — read past them.

All numbers printed by `python -m validation.tech_finder.card_report --format standard`.

## vs Midrange  (159 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Melira, the Living Cure | +0.1689 | +0.1044 | -0.0646 | 3 | 76 | — |
| Tocasia's Welcome | +0.1174 | +0.0941 | -0.0233 | 3 | 120 | — |
| Leyline Binding | +0.1067 | +0.0497 | -0.0570 | 3 | 103 | artifact_enchant_removal, creature_removal |
| Analyze the Pollen | +0.1014 | +0.0593 | -0.0420 | 3 | 137 | — |
| Spara's Headquarters | +0.0999 | +0.0512 | -0.0487 | 5 | 1068 | land / deck-proxy |
| Jetmir's Garden | +0.0960 | +0.0531 | -0.0429 | 3 | 1016 | land / deck-proxy |
| Lazav, Wearer of Faces | +0.0929 | +0.0740 | -0.0189 | 3 | 96 | graveyard_hate |
| Malcolm, Alluring Scoundrel | +0.0904 | -0.0103 | -0.1007 | 4 | 114 | — |
| Assimilation Aegis | +0.0835 | +0.0622 | -0.0213 | 3 | 158 | — |
| Ill-Timed Explosion | +0.0811 | +0.0152 | -0.0658 | 4 | 182 | — |
| Sanguine Evangelist | +0.0792 | +0.0902 | +0.0111 | 3 | 1040 | — |
| Glistening Deluge | +0.0754 | +0.0796 | +0.0043 | 3 | 528 | — |
| Up the Beanstalk | +0.0751 | +0.0288 | -0.0464 | 5 | 1399 | — |
| Ziatora's Proving Ground | +0.0711 | +0.0490 | -0.0221 | 5 | 1513 | land / deck-proxy |
| Steel Seraph | +0.0690 | +0.0894 | +0.0204 | 3 | 105 | — |

## vs Control  (84 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Yavimaya Coast | +0.0941 | +0.1250 | +0.0308 | 3 | 340 | land / deck-proxy |
| Go for the Throat | +0.0897 | +0.1074 | +0.0177 | 4 | 1525 | creature_removal |
| Spell Pierce | +0.0853 | +0.1072 | +0.0219 | 4 | 641 | counter_spell |
| Restless Reef | +0.0846 | +0.1130 | +0.0284 | 3 | 426 | land / deck-proxy |
| Rockfall Vale | +0.0750 | +0.0468 | -0.0282 | 4 | 174 | land / deck-proxy |
| Mirrex | +0.0744 | +0.0720 | -0.0024 | 5 | 1457 | land / deck-proxy |
| Battlefield Forge | +0.0738 | +0.0783 | +0.0045 | 3 | 975 | land / deck-proxy |
| Topiary Stomper | +0.0728 | +0.0687 | -0.0041 | 3 | 706 | — |
| Tyrranax Rex | +0.0719 | +0.0573 | -0.0146 | 3 | 217 | — |
| Spyglass Siren | +0.0704 | +0.1030 | +0.0326 | 4 | 340 | — |
| Tishana's Tidebinder | +0.0523 | +0.0554 | +0.0031 | 7 | 1754 | counter_ability |
| Cryptic Coat | +0.0509 | +0.0624 | +0.0115 | 3 | 200 | — |
| Eiganjo, Seat of the Empire | +0.0499 | +0.0431 | -0.0068 | 7 | 2233 | land / deck-proxy |
| Make Disappear | +0.0498 | +0.0695 | +0.0197 | 3 | 374 | counter_spell |
| Kaito Shizuki | +0.0479 | +0.0584 | +0.0105 | 3 | 253 | — |

## vs Aggro  (123 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Spell Pierce | +0.0863 | +0.1014 | +0.0151 | 4 | 357 | counter_spell |
| Abrade | +0.0815 | +0.0703 | -0.0112 | 3 | 282 | artifact_enchant_removal, creature_removal |
| Ziatora's Proving Ground | +0.0788 | +0.0493 | -0.0296 | 4 | 682 | land / deck-proxy |
| Knockout Blow | +0.0767 | +0.0853 | +0.0087 | 7 | 920 | — |
| Brotherhood's End | +0.0683 | +0.0159 | -0.0524 | 4 | 249 | board_sweeper |
| Deathcap Glade | +0.0667 | +0.0672 | +0.0004 | 3 | 554 | land / deck-proxy |
| Concealed Courtyard | +0.0658 | +0.0275 | -0.0383 | 3 | 485 | land / deck-proxy |
| Tyrranax Rex | +0.0613 | +0.0534 | -0.0079 | 3 | 110 | — |
| Sokenzan, Crucible of Defiance | +0.0568 | +0.0241 | -0.0327 | 4 | 739 | land / deck-proxy |
| Raffine's Tower | +0.0536 | +0.0098 | -0.0438 | 3 | 764 | land / deck-proxy |
| Boseiju, Who Endures | +0.0505 | +0.0413 | -0.0092 | 6 | 996 | artifact_enchant_removal, land_destruction |
| Virtue of Persistence // Locthwain Scorn | +0.0498 | +0.0263 | -0.0235 | 5 | 530 | — |
| Preacher of the Schism | +0.0493 | +0.0260 | -0.0233 | 5 | 1130 | — |
| Deserted Beach | +0.0492 | +0.0685 | +0.0193 | 3 | 927 | land / deck-proxy |
| Takenuma, Abandoned Mire | +0.0469 | +0.0338 | -0.0131 | 4 | 1405 | land / deck-proxy |

## vs Esper Midrange  (79 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Ziatora's Proving Ground | +0.1412 | +0.0853 | -0.0558 | 3 | 490 | land / deck-proxy |
| Ill-Timed Explosion | +0.0938 | +0.0496 | -0.0442 | 3 | 639 | — |
| Path of Peril | +0.0551 | +0.0486 | -0.0065 | 5 | 1385 | board_sweeper |
| Deathcap Glade | +0.0545 | +0.0516 | -0.0028 | 3 | 827 | land / deck-proxy |
| Swamp | +0.0540 | +0.0259 | -0.0281 | 6 | 1949 | land / deck-proxy |
| Boseiju, Who Endures | +0.0539 | +0.0432 | -0.0107 | 7 | 1100 | artifact_enchant_removal, land_destruction |
| Forest | +0.0507 | +0.0323 | -0.0184 | 5 | 748 | land / deck-proxy |
| Raffine's Tower | +0.0505 | -0.0119 | -0.0624 | 3 | 504 | land / deck-proxy |
| Liliana of the Veil | +0.0505 | +0.0392 | -0.0112 | 3 | 1207 | creature_removal |
| The Stone Brain | +0.0488 | -0.0091 | -0.0579 | 5 | 167 | graveyard_hate |
| Cavern of Souls | +0.0457 | +0.0260 | -0.0197 | 4 | 1876 | land / deck-proxy |
| Rockfall Vale | +0.0446 | +0.0110 | -0.0337 | 3 | 113 | land / deck-proxy |
| Soul-Guide Lantern | +0.0434 | +0.0329 | -0.0105 | 3 | 125 | graveyard_hate |
| Long Goodbye | +0.0346 | +0.0031 | -0.0315 | 6 | 1349 | creature_removal |
| Duress | +0.0339 | +0.0252 | -0.0088 | 6 | 1859 | hand_disruption |

## vs Boros Convoke  (80 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Analyze the Pollen | +0.2020 | +0.1779 | -0.0241 | 3 | 91 | — |
| Sunfall | +0.1562 | +0.1656 | +0.0094 | 4 | 1424 | board_sweeper |
| No More Lies | +0.1264 | +0.1261 | -0.0003 | 3 | 1610 | counter_spell |
| Depopulate | +0.1223 | +0.1339 | +0.0117 | 3 | 1009 | board_sweeper |
| The Stone Brain | +0.1097 | +0.0638 | -0.0459 | 4 | 143 | graveyard_hate |
| Dennick, Pious Apprentice // Dennick, Pious Apparition | +0.0994 | +0.1177 | +0.0183 | 3 | 1005 | — |
| Deserted Beach | +0.0876 | +0.0921 | +0.0045 | 3 | 1394 | land / deck-proxy |
| Temporary Lockdown | +0.0871 | +0.1080 | +0.0209 | 4 | 1715 | board_sweeper |
| Rest in Peace | +0.0787 | +0.0418 | -0.0369 | 6 | 1335 | graveyard_hate |
| Plains | +0.0787 | +0.0737 | -0.0050 | 6 | 2051 | land / deck-proxy |
| The Wandering Emperor | +0.0716 | +0.0806 | +0.0090 | 4 | 1858 | creature_removal |
| Lightning Helix | +0.0686 | +0.0311 | -0.0375 | 3 | 76 | creature_removal |
| Get Lost | +0.0516 | +0.0564 | +0.0048 | 7 | 1142 | artifact_enchant_removal, creature_removal |
| Eiganjo, Seat of the Empire | +0.0432 | +0.0452 | +0.0020 | 7 | 2068 | land / deck-proxy |
| Sulfurous Springs | +0.0385 | +0.0083 | -0.0302 | 3 | 292 | land / deck-proxy |

## vs Domain  (86 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Atraxa, Grand Unifier | +0.1434 | +0.1621 | +0.0187 | 3 | 128 | — |
| Undercity Sewers | +0.1268 | +0.1569 | +0.0301 | 3 | 138 | land / deck-proxy |
| Three Steps Ahead | +0.0957 | +0.0966 | +0.0009 | 5 | 717 | counter_spell |
| Jace, the Perfected Mind | +0.0825 | +0.0792 | -0.0032 | 3 | 704 | — |
| Island | +0.0812 | +0.0881 | +0.0069 | 8 | 1146 | land / deck-proxy |
| Elesh Norn, Mother of Machines | +0.0729 | +0.0849 | +0.0121 | 3 | 330 | — |
| Yavimaya Coast | +0.0668 | +0.1026 | +0.0358 | 3 | 194 | land / deck-proxy |
| Pick Your Poison | +0.0628 | +0.0619 | -0.0009 | 3 | 478 | creature_removal |
| Torch the Tower | +0.0572 | +0.0729 | +0.0157 | 3 | 192 | creature_removal |
| Cut Down | +0.0558 | +0.0564 | +0.0006 | 4 | 1390 | creature_removal |
| Tishana's Tidebinder | +0.0533 | +0.0783 | +0.0250 | 4 | 1522 | counter_ability |
| Obliterating Bolt | +0.0517 | +0.0814 | +0.0297 | 3 | 353 | creature_removal |
| Negate | +0.0465 | +0.0675 | +0.0210 | 9 | 2117 | counter_spell |
| Darkslick Shores | +0.0464 | +0.0655 | +0.0192 | 3 | 554 | land / deck-proxy |
| Otawara, Soaring City | +0.0456 | +0.0722 | +0.0265 | 4 | 1093 | land / deck-proxy |

## vs Analyst  (39 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Three Steps Ahead | +0.1482 | +0.1440 | -0.0042 | 3 | 712 | counter_spell |
| Tishana's Tidebinder | +0.0585 | +0.0749 | +0.0164 | 5 | 1542 | counter_ability |
| Shipwreck Marsh | +0.0543 | +0.0409 | -0.0134 | 3 | 474 | land / deck-proxy |
| Island | +0.0516 | +0.0533 | +0.0017 | 4 | 692 | land / deck-proxy |
| Unlicensed Hearse | +0.0494 | +0.0550 | +0.0057 | 5 | 1061 | graveyard_hate |
| Elesh Norn, Mother of Machines | +0.0486 | +0.0486 | +0.0000 | 5 | 723 | — |
| Deadly Cover-Up | +0.0419 | +0.0061 | -0.0358 | 3 | 248 | board_sweeper, graveyard_hate |
| Thran Portal | +0.0398 | +0.0508 | +0.0111 | 3 | 270 | land / deck-proxy |
| Loran of the Third Path | +0.0363 | +0.0395 | +0.0031 | 3 | 434 | — |
| Aclazotz, Deepest Betrayal // Temple of the Dead | +0.0359 | +0.0364 | +0.0006 | 4 | 1375 | land / deck-proxy |
| Takenuma, Abandoned Mire | +0.0355 | +0.0131 | -0.0224 | 3 | 1225 | land / deck-proxy |
| Path of Peril | +0.0214 | +0.0176 | -0.0038 | 4 | 925 | board_sweeper |
| Rest in Peace | +0.0183 | +0.0062 | -0.0121 | 6 | 1365 | graveyard_hate |
| Raffine's Tower | +0.0181 | +0.0006 | -0.0175 | 5 | 870 | land / deck-proxy |
| Disdainful Stroke | +0.0161 | +0.0492 | +0.0331 | 3 | 730 | counter_spell |

## vs Poison  (49 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Pick Your Poison | +0.1381 | +0.1310 | -0.0070 | 3 | 358 | creature_removal |
| Boseiju, Who Endures | +0.0919 | +0.0891 | -0.0029 | 3 | 507 | artifact_enchant_removal, land_destruction |
| Dennick, Pious Apprentice // Dennick, Pious Apparition | +0.0911 | +0.1143 | +0.0232 | 3 | 411 | — |
| Get Lost | +0.0811 | +0.0915 | +0.0103 | 5 | 799 | artifact_enchant_removal, creature_removal |
| Eiganjo, Seat of the Empire | +0.0806 | +0.1018 | +0.0213 | 3 | 826 | land / deck-proxy |
| Liliana of the Veil | +0.0736 | +0.0645 | -0.0091 | 3 | 567 | creature_removal |
| Plains | +0.0647 | +0.0744 | +0.0097 | 3 | 808 | land / deck-proxy |
| Cavern of Souls | +0.0607 | +0.0431 | -0.0176 | 4 | 869 | land / deck-proxy |
| Sokenzan, Crucible of Defiance | +0.0552 | +0.0294 | -0.0258 | 5 | 736 | land / deck-proxy |
| Forest | +0.0475 | +0.0438 | -0.0036 | 3 | 352 | land / deck-proxy |
| No More Lies | +0.0469 | +0.0606 | +0.0137 | 3 | 732 | counter_spell |
| The Wandering Emperor | +0.0440 | +0.0629 | +0.0189 | 4 | 840 | creature_removal |
| Kutzil's Flanker | +0.0408 | +0.0592 | +0.0184 | 4 | 416 | graveyard_hate |
| Temporary Lockdown | +0.0342 | +0.0662 | +0.0320 | 3 | 524 | board_sweeper |
| Mountain | +0.0303 | +0.0083 | -0.0221 | 3 | 314 | land / deck-proxy |

## vs Legends  (35 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Swamp | +0.0767 | +0.0461 | -0.0306 | 3 | 672 | land / deck-proxy |
| Takenuma, Abandoned Mire | +0.0705 | +0.0486 | -0.0220 | 3 | 918 | land / deck-proxy |
| Sheoldred, the Apocalypse | +0.0669 | +0.0403 | -0.0267 | 3 | 580 | — |
| Aclazotz, Deepest Betrayal // Temple of the Dead | +0.0536 | +0.0517 | -0.0020 | 3 | 854 | land / deck-proxy |
| Path of Peril | +0.0532 | +0.0397 | -0.0135 | 3 | 514 | board_sweeper |
| Long Goodbye | +0.0371 | +0.0134 | -0.0237 | 4 | 713 | creature_removal |
| Duress | +0.0310 | +0.0053 | -0.0257 | 3 | 717 | hand_disruption |
| Unlicensed Hearse | +0.0111 | +0.0160 | +0.0049 | 4 | 671 | graveyard_hate |
| Pick Your Poison | +0.0108 | +0.0149 | +0.0041 | 3 | 432 | creature_removal |
| Destroy Evil | +0.0082 | +0.0119 | +0.0037 | 5 | 749 | artifact_enchant_removal, creature_removal |
| Tranquil Frillback | +0.0004 | +0.0003 | -0.0001 | 3 | 582 | artifact_enchant_removal, graveyard_hate |
| Wedding Announcement // Wedding Festivity | -0.0073 | +0.0159 | +0.0232 | 3 | 316 | — |
| Shipwreck Marsh | -0.0095 | -0.0187 | -0.0093 | 3 | 330 | land / deck-proxy |
| Knockout Blow | -0.0116 | +0.0010 | +0.0125 | 6 | 427 | — |
| Elesh Norn, Mother of Machines | -0.0128 | +0.0002 | +0.0130 | 3 | 390 | — |

## vs Reanimator  (26 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Otawara, Soaring City | +0.1289 | +0.1535 | +0.0246 | 3 | 251 | land / deck-proxy |
| Shipwreck Marsh | +0.1282 | +0.1230 | -0.0052 | 3 | 133 | land / deck-proxy |
| Negate | +0.1143 | +0.1413 | +0.0270 | 3 | 223 | counter_spell |
| Deserted Beach | +0.0931 | +0.1119 | +0.0188 | 3 | 177 | land / deck-proxy |
| Mirrex | +0.0817 | +0.0883 | +0.0066 | 3 | 327 | land / deck-proxy |
| Disdainful Stroke | +0.0815 | +0.0979 | +0.0164 | 3 | 168 | counter_spell |
| Adarkar Wastes | +0.0676 | +0.0759 | +0.0084 | 3 | 151 | land / deck-proxy |
| Rest in Peace | +0.0555 | +0.0207 | -0.0348 | 3 | 74 | graveyard_hate |
| Tishana's Tidebinder | +0.0550 | +0.0811 | +0.0261 | 3 | 231 | counter_ability |
| Get Lost | +0.0477 | +0.0591 | +0.0114 | 5 | 290 | artifact_enchant_removal, creature_removal |
| Long Goodbye | +0.0442 | +0.0167 | -0.0275 | 4 | 159 | creature_removal |
| Eiganjo, Seat of the Empire | +0.0345 | +0.0437 | +0.0092 | 3 | 184 | land / deck-proxy |
| No More Lies | +0.0214 | +0.0329 | +0.0115 | 3 | 210 | counter_spell |
| The Wandering Emperor | +0.0010 | +0.0137 | +0.0127 | 3 | 175 | creature_removal |
| Aclazotz, Deepest Betrayal // Temple of the Dead | -0.0110 | -0.0006 | +0.0104 | 3 | 314 | land / deck-proxy |

## vs Convoke  (2 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Beza, the Bounding Spring | +0.2287 | +0.1943 | -0.0344 | 3 | 103 | — |
| Tishana's Tidebinder | +0.0155 | +0.0426 | +0.0270 | 3 | 159 | counter_ability |

## vs Artifact Aggro  (2 scored cards)

| card | A-specific | vsA | field | strata | support | role / kind |
|---|---|---|---|---|---|---|
| Long Goodbye | +0.1136 | +0.0836 | -0.0300 | 3 | 85 | creature_removal |
| Rest in Peace | -0.0535 | -0.0813 | -0.0278 | 4 | 99 | graveyard_hate |
