"""
Science synonym dictionary for the grading matching engine.

Covers chemistry, biology, physics and maths abbreviations/alternative names.
Matching is always bidirectional and case-insensitive.

Structure:  each entry is a SET of equivalent terms for the same concept.
"""

# ── Chemistry ──────────────────────────────────────────────────────────────

# Common molecular formulas ↔ IUPAC / common names
CHEMISTRY_SYNONYMS = [
    # Gases
    {"co2", "carbon dioxide", "carbon(iv) oxide"},
    {"co", "carbon monoxide", "carbon(ii) oxide"},
    {"h2o", "water", "dihydrogen monoxide", "hydrogen oxide"},
    {"o2", "oxygen", "dioxygen", "molecular oxygen"},
    {"n2", "nitrogen", "dinitrogen", "molecular nitrogen"},
    {"h2", "hydrogen", "dihydrogen", "molecular hydrogen"},
    {"nh3", "ammonia", "nitrogen trihydride"},
    {"hcl", "hydrochloric acid", "hydrogen chloride"},
    {"h2so4", "sulfuric acid", "sulphuric acid"},
    {"hno3", "nitric acid"},
    {"h3po4", "phosphoric acid"},
    {"h2co3", "carbonic acid"},
    {"naoh", "sodium hydroxide", "caustic soda", "lye"},
    {"koh", "potassium hydroxide", "caustic potash"},
    {"ca(oh)2", "calcium hydroxide", "slaked lime", "limewater", "lime water"},
    {"nacl", "sodium chloride", "table salt", "salt"},
    {"cacl2", "calcium chloride"},
    {"mgcl2", "magnesium chloride"},
    {"caco3", "calcium carbonate", "limestone", "chalk", "marble"},
    {"cao", "calcium oxide", "quicklime", "lime"},
    {"na2co3", "sodium carbonate", "washing soda", "soda ash"},
    {"nahco3", "sodium bicarbonate", "baking soda", "sodium hydrogen carbonate"},
    {"h2o2", "hydrogen peroxide"},
    {"ch4", "methane", "natural gas"},
    {"c2h6", "ethane"},
    {"c2h4", "ethene", "ethylene"},
    {"c2h2", "ethyne", "acetylene"},
    {"c6h12o6", "glucose", "dextrose"},
    {"c12h22o11", "sucrose", "cane sugar", "table sugar"},
    {"ch3oh", "methanol", "methyl alcohol", "wood alcohol"},
    {"c2h5oh", "ethanol", "ethyl alcohol", "alcohol"},
    {"ch3cooh", "acetic acid", "ethanoic acid", "vinegar"},
    {"so2", "sulfur dioxide", "sulphur dioxide"},
    {"so3", "sulfur trioxide", "sulphur trioxide"},
    {"no2", "nitrogen dioxide"},
    {"no", "nitric oxide", "nitrogen monoxide"},
    {"cl2", "chlorine", "dichlorine"},
    {"br2", "bromine"},
    {"i2", "iodine"},
    {"f2", "fluorine"},
    {"fe2o3", "iron(iii) oxide", "iron oxide", "rust", "haematite", "hematite"},
    {"feo", "iron(ii) oxide"},
    {"fe3o4", "iron(ii,iii) oxide", "magnetite"},
    {"al2o3", "aluminium oxide", "aluminum oxide", "alumina"},
    {"sio2", "silicon dioxide", "silica", "silicon(iv) oxide"},
    {"mgo", "magnesium oxide"},
    {"cuo", "copper(ii) oxide", "cupric oxide"},
    {"zno", "zinc oxide"},
    {"k2so4", "potassium sulfate", "potassium sulphate"},
    {"na2so4", "sodium sulfate", "sodium sulphate"},
    {"feso4", "iron(ii) sulfate", "ferrous sulfate", "iron(ii) sulphate"},
    {"fecl3", "iron(iii) chloride", "ferric chloride"},
    {"cucl2", "copper(ii) chloride", "cupric chloride"},
    {"agno3", "silver nitrate"},
    {"pbso4", "lead(ii) sulfate", "lead sulphate"},
    {"baso4", "barium sulfate", "barium sulphate"},
]

# Element symbols ↔ names
ELEMENT_SYNONYMS = [
    {"h", "hydrogen"},
    {"he", "helium"},
    {"li", "lithium"},
    {"be", "beryllium"},
    {"b", "boron"},
    {"c", "carbon"},
    {"n", "nitrogen"},
    {"o", "oxygen"},
    {"f", "fluorine"},
    {"ne", "neon"},
    {"na", "sodium", "natrium"},
    {"mg", "magnesium"},
    {"al", "aluminium", "aluminum"},
    {"si", "silicon"},
    {"p", "phosphorus"},
    {"s", "sulfur", "sulphur"},
    {"cl", "chlorine"},
    {"ar", "argon"},
    {"k", "potassium", "kalium"},
    {"ca", "calcium"},
    {"sc", "scandium"},
    {"ti", "titanium"},
    {"v", "vanadium"},
    {"cr", "chromium"},
    {"mn", "manganese"},
    {"fe", "iron", "ferrum"},
    {"co", "cobalt"},
    {"ni", "nickel"},
    {"cu", "copper", "cuprum"},
    {"zn", "zinc"},
    {"br", "bromine"},
    {"ag", "silver", "argentum"},
    {"sn", "tin", "stannum"},
    {"i", "iodine"},
    {"ba", "barium"},
    {"au", "gold", "aurum"},
    {"hg", "mercury", "hydrargyrum"},
    {"pb", "lead", "plumbum"},
    {"pt", "platinum"},
    {"u", "uranium"},
    {"ra", "radium"},
]

# ── Biology ────────────────────────────────────────────────────────────────

BIOLOGY_SYNONYMS = [
    # Molecules
    {"atp", "adenosine triphosphate"},
    {"adp", "adenosine diphosphate"},
    {"amp", "adenosine monophosphate"},
    {"nadh", "nicotinamide adenine dinucleotide"},
    {"nad+", "nad", "nicotinamide adenine dinucleotide"},
    {"nadph", "nicotinamide adenine dinucleotide phosphate"},
    {"dna", "deoxyribonucleic acid"},
    {"rna", "ribonucleic acid"},
    {"mrna", "messenger rna", "messenger ribonucleic acid"},
    {"trna", "transfer rna", "transfer ribonucleic acid"},
    {"rrna", "ribosomal rna", "ribosomal ribonucleic acid"},
    {"atp synthase", "f1fo atpase", "complex v"},
    # Processes
    {"cellular respiration", "aerobic respiration", "aerobic cellular respiration"},
    {"anaerobic respiration", "anaerobic cellular respiration", "fermentation"},
    {"photosynthesis", "light-dependent reactions and calvin cycle"},
    {"glycolysis", "embden-meyerhof-parnas pathway", "emp pathway"},
    {"krebs cycle", "citric acid cycle", "tca cycle", "tricarboxylic acid cycle"},
    {"electron transport chain", "etc", "oxidative phosphorylation", "respiratory chain"},
    {"light reactions", "light-dependent reactions", "photophosphorylation"},
    {"calvin cycle", "dark reactions", "light-independent reactions", "carbon fixation"},
    {"mitosis", "somatic cell division"},
    {"meiosis", "reduction division", "germ cell division"},
    {"transcription", "dna transcription", "gene transcription"},
    {"translation", "protein synthesis", "mrna translation"},
    {"dna replication", "semi-conservative replication"},
    {"osmosis", "diffusion of water"},
    {"active transport", "active uptake"},
    {"passive transport", "passive diffusion", "facilitated diffusion"},
    # Structures
    {"mitochondria", "mitochondrion", "powerhouse of the cell"},
    {"chloroplast", "site of photosynthesis"},
    {"ribosome", "site of protein synthesis"},
    {"endoplasmic reticulum", "er"},
    {"rough er", "rough endoplasmic reticulum"},
    {"smooth er", "smooth endoplasmic reticulum"},
    {"golgi apparatus", "golgi body", "golgi complex"},
    {"cell membrane", "plasma membrane", "phospholipid bilayer"},
    {"cell wall", "plant cell wall"},
    {"nucleus", "nuclear membrane", "nuclear envelope"},
    {"chromosome", "condensed chromatin"},
    {"allele", "gene variant", "gene form"},
    {"homologous chromosomes", "homologues", "homologs"},
    # Genetics
    {"dominant", "dominant allele", "dominant trait"},
    {"recessive", "recessive allele", "recessive trait"},
    {"genotype", "genetic makeup", "allele combination"},
    {"phenotype", "observable trait", "physical trait"},
    {"homozygous", "homozygote", "pure breeding"},
    {"heterozygous", "heterozygote", "hybrid"},
    {"mutation", "gene mutation", "genetic change"},
]

# ── Physics ────────────────────────────────────────────────────────────────

PHYSICS_SYNONYMS = [
    # Units
    {"n", "newton", "newtons"},
    {"j", "joule", "joules"},
    {"w", "watt", "watts"},
    {"pa", "pascal", "pascals"},
    {"hz", "hertz"},
    {"v", "volt", "volts"},
    {"a", "ampere", "amperes", "amp", "amps"},
    {"c", "coulomb", "coulombs"},
    {"ω", "ohm", "ohms"},
    {"f", "farad", "farads"},
    {"h", "henry", "henries"},
    {"t", "tesla", "teslas"},
    {"wb", "weber", "webers"},
    {"ev", "electron volt", "electronvolt"},
    {"kev", "kilo electron volt", "kiloelectronvolt"},
    {"mev", "mega electron volt", "megaelectronvolt"},
    {"kwh", "kilowatt hour", "kilowatt-hour"},
    # Quantities / concepts
    {"emf", "electromotive force", "e.m.f."},
    {"pd", "potential difference", "voltage", "p.d."},
    {"ke", "kinetic energy", "k.e."},
    {"pe", "potential energy", "p.e."},
    {"gpe", "gravitational potential energy"},
    {"ke = ½mv²", "kinetic energy = half mass times velocity squared"},
    {"f = ma", "force equals mass times acceleration", "newton's second law"},
    {"v = ir", "ohm's law", "voltage equals current times resistance"},
    {"e = mc²", "mass energy equivalence", "einstein's equation"},
    {"p = iv", "power equals current times voltage"},
    {"speed", "velocity"},           # often used interchangeably in basic physics
    {"acceleration due to gravity", "gravitational acceleration", "g = 9.8", "g = 9.81", "g ≈ 10"},
    {"electromagnetic radiation", "em radiation", "em waves"},
    {"total internal reflection", "tir", "t.i.r."},
    {"critical angle", "angle of total internal reflection"},
    {"refractive index", "index of refraction", "n"},
    {"wavelength", "lambda", "λ"},
    {"frequency", "f", "nu", "ν"},
]

# ── Maths ──────────────────────────────────────────────────────────────────

MATHS_SYNONYMS = [
    {"gradient", "slope", "rate of change", "m"},
    {"y-intercept", "c", "constant term"},
    {"quadratic formula", "x = (-b ± √(b²-4ac)) / 2a", "x = (-b ± √(b²-4ac)) / (2a)"},
    {"pythagoras theorem", "pythagorean theorem", "a² + b² = c²", "a^2 + b^2 = c^2"},
    {"differentiation", "derivative", "finding the derivative"},
    {"integration", "antiderivative", "finding the integral"},
    {"perpendicular", "at right angles", "normal"},
    {"parallel", "same gradient", "same slope"},
    {"arithmetic mean", "mean", "average"},
    {"standard deviation", "sd", "σ"},
    {"variance", "σ²", "standard deviation squared"},
    {"probability", "p", "likelihood", "chance"},
    {"permutation", "arrangement"},
    {"combination", "selection"},
    {"pi", "π", "3.14159", "3.14"},
    {"infinity", "∞"},
    {"absolute value", "modulus", "|x|"},
]

# ── Build lookup structures ────────────────────────────────────────────────

def _build_lookup(synonym_groups):
    """
    Build a dict: normalised_term -> frozenset of all synonyms in its group.
    """
    lookup = {}
    for group in synonym_groups:
        frozen = frozenset(s.lower() for s in group)
        for term in frozen:
            lookup[term] = frozen
    return lookup


ALL_SYNONYM_GROUPS = (
    CHEMISTRY_SYNONYMS
    + ELEMENT_SYNONYMS
    + BIOLOGY_SYNONYMS
    + PHYSICS_SYNONYMS
    + MATHS_SYNONYMS
)

# Full lookup — used for whole-answer are_synonyms() checks.
SYNONYM_LOOKUP: dict = _build_lookup(ALL_SYNONYM_GROUPS)

# Substitution lookup — intentionally excludes element-symbol groups
# (e.g. {"c","carbon"}, {"n","nitrogen"}) because short element names
# would corrupt compound phrases like "carbon dioxide" when substituted
# character-by-character.  Chemical formulas (co2, h2o, …) remain
# because they are distinctive enough not to cause false matches.
_SUBSTITUTION_GROUPS = (
    CHEMISTRY_SYNONYMS
    + BIOLOGY_SYNONYMS
    + PHYSICS_SYNONYMS
    + MATHS_SYNONYMS
)
_SUBSTITUTION_LOOKUP: dict = _build_lookup(_SUBSTITUTION_GROUPS)


def are_synonyms(term_a: str, term_b: str) -> bool:
    """Return True if term_a and term_b are in the same synonym group."""
    a = term_a.strip().lower()
    b = term_b.strip().lower()
    if a == b:
        return True
    group = SYNONYM_LOOKUP.get(a)
    return group is not None and b in group


def normalise_with_synonyms(text: str) -> str:
    """
    Replace every known synonym in `text` with a canonical form so two texts
    that differ only in scientific notation compare as equal.

    The canonical form chosen is the first (alphabetically sorted) member of
    the synonym group — this is stable and deterministic.
    """
    import re as _re
    text_lower = text.lower()

    # Sort terms longest-first so "carbon dioxide" is replaced before "co2"
    sorted_terms = sorted(_SUBSTITUTION_LOOKUP.keys(), key=len, reverse=True)

    for term in sorted_terms:
        if term in text_lower:
            group = _SUBSTITUTION_LOOKUP[term]
            canonical = sorted(group)[0]   # stable canonical form
            # Replace whole-word occurrences only
            pattern = r'(?<![a-z0-9])' + _re.escape(term) + r'(?![a-z0-9])'
            text_lower = _re.sub(pattern, canonical, text_lower)

    return text_lower


def synonym_match_score(student: str, gold: str) -> float:
    """
    Compare student and gold text after replacing all synonyms with canonical
    forms.  Returns 1.0 if they match after normalisation, 0.0 otherwise.

    Also returns 1.0 when the entire student answer IS a known synonym for the
    entire gold answer (e.g. "CO2" vs "Carbon dioxide").
    """
    import re as _re

    s = student.strip().lower()
    g = gold.strip().lower()

    # Direct synonym check (whole-answer synonyms)
    if are_synonyms(s, g):
        return 1.0

    # After substituting synonyms to canonical forms, do the texts match?
    s_norm = normalise_with_synonyms(s)
    g_norm = normalise_with_synonyms(g)

    if s_norm == g_norm:
        return 1.0

    # Partial: how many canonical tokens overlap?
    s_tokens = set(_re.findall(r'[a-z0-9]+', s_norm))
    g_tokens = set(_re.findall(r'[a-z0-9]+', g_norm))
    # Exclude trivial stop-words from token overlap
    _stop = {'the', 'a', 'an', 'is', 'are', 'of', 'in', 'to', 'and', 'or', 'it'}
    s_tokens -= _stop
    g_tokens -= _stop
    if s_tokens and g_tokens:
        overlap = len(s_tokens & g_tokens) / max(len(s_tokens), len(g_tokens))
        if overlap >= 0.85:
            return overlap   # high partial — caller can decide threshold

    return 0.0
