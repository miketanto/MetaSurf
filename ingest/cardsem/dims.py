"""Names of the 68 feature dimensions, in table column order.

Derived from CardGuru's `rl/e2_extract.py` at the pinned commit (see
PROVENANCE.md) by reading its `ANSWER_QUERIES`, `EFFECT_APIS`, `KEYWORDS`, and
structural-feature lists — not transcribed by hand. `test_cardsem.py` asserts
the count matches the shipped table's declared dimensionality, so a pin bump
that changes the feature space fails the suite instead of silently shifting
every column's meaning.

These names are what makes the features *explainable* downstream: an emerging
cluster can be described by the dimensions on which its centroid differs from
its nearest neighbour, which is the difference between "new cluster, 12 lists"
and "new cluster running graveyard exile and ETB triggers".
"""

from __future__ import annotations

# 9 answer classes (cardguru.answers.ANSWER_QUERIES, sorted)
ANSWER_DIMS: tuple[str, ...] = (
    "ans_bounce_target",
    "ans_counter_spell",
    "ans_damage_target",
    "ans_destroy_all",
    "ans_destroy_target",
    "ans_edict_sacrifice",
    "ans_edict_sacrifice_mass",
    "ans_exile_target",
    "ans_minus_toughness",
)

# 20 Forge effect APIs
API_DIMS: tuple[str, ...] = (
    "api_DealDamage",
    "api_Counter",
    "api_Destroy",
    "api_ChangeZone",
    "api_Pump",
    "api_Draw",
    "api_Discard",
    "api_Token",
    "api_PutCounter",
    "api_GainLife",
    "api_LoseLife",
    "api_Sacrifice",
    "api_Mill",
    "api_Scry",
    "api_Mana",
    "api_DestroyAll",
    "api_DamageAll",
    "api_PumpAll",
    "api_Animate",
    "api_Dig",
)

# 18 keywords
KEYWORD_DIMS: tuple[str, ...] = (
    "kw_flying",
    "kw_haste",
    "kw_deathtouch",
    "kw_lifelink",
    "kw_first_strike",
    "kw_double_strike",
    "kw_trample",
    "kw_vigilance",
    "kw_flash",
    "kw_menace",
    "kw_reach",
    "kw_defender",
    "kw_ward",
    "kw_hexproof",
    "kw_shroud",
    "kw_protection",
    "kw_prowess",
    "kw_ninjutsu",
)

# 21 structural dims. `num_dmg` is the only non-binary feature in the table:
# min(NumDmg, 6) / 6, or 0.5 for X/SVar-driven damage.
STRUCTURAL_DIMS: tuple[str, ...] = (
    "trig_etb",
    "trig_death",
    "trig_attacks",
    "trig_spellcast",
    "trig_damage",
    "trig_phase",
    "has_static",
    "has_replacement",
    "has_activated",
    "tgt_creature",
    "tgt_player_or_any",
    "tgt_spell",
    "num_dmg",
    "pump_att_pos",
    "pump_def_neg",
    "type_land",
    "type_planeswalker",
    "type_enchantment",
    "type_artifact",
    "recursive",
    "multi_face",
)

FEATURE_NAMES: tuple[str, ...] = ANSWER_DIMS + API_DIMS + KEYWORD_DIMS + STRUCTURAL_DIMS

DIM = len(FEATURE_NAMES)

# Mechanics that name or define Modern archetypes in
# archetypes/definitions/modern/ but have no dimension in the feature space.
# Probed empirically in the coverage report: cards whose only ability is one of
# these come back as all-zero vectors, which the vectorizer must mask rather
# than read as "this card does nothing". Extending CardGuru's KEYWORDS list is
# the fix; until then this is a documented blind spot, not a surprise.
UNREPRESENTED_MECHANICS: tuple[str, ...] = (
    "infect",
    "cycling",
    "delve",
    "cascade",
    "storm",
    "dredge",
    "evoke",
    "affinity",
    "convoke",
    "madness",
)
