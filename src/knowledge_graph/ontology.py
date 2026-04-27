from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD

BATT = Namespace("http://battery-ontology.org/schema#")
INST = Namespace("http://battery-ontology.org/instance#")
UNIT = Namespace("http://battery-ontology.org/unit#")


def create_ontology() -> Graph:
    g = Graph()

    g.bind("batt", BATT)
    g.bind("inst", INST)
    g.bind("unit", UNIT)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    ontology_uri = URIRef("http://battery-ontology.org/schema")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("Battery Specification Ontology")))
    g.add((ontology_uri, RDFS.comment, Literal(
        "An ontology for representing battery datasheet specifications, "
        "including electrical, physical, and thermal properties."
    )))

    g.add((BATT.Battery, RDF.type, OWL.Class))
    g.add((BATT.Battery, RDFS.label, Literal("Battery")))
    g.add((BATT.Battery, RDFS.comment, Literal("A battery cell or pack described by a datasheet.")))

    g.add((BATT.Specification, RDF.type, OWL.Class))
    g.add((BATT.Specification, RDFS.label, Literal("Specification")))
    g.add((BATT.Specification, RDFS.comment, Literal("A technical specification of a battery.")))

    g.add((BATT.ElectricalSpecification, RDF.type, OWL.Class))
    g.add((BATT.ElectricalSpecification, RDFS.subClassOf, BATT.Specification))
    g.add((BATT.ElectricalSpecification, RDFS.label, Literal("Electrical Specification")))

    g.add((BATT.PhysicalSpecification, RDF.type, OWL.Class))
    g.add((BATT.PhysicalSpecification, RDFS.subClassOf, BATT.Specification))
    g.add((BATT.PhysicalSpecification, RDFS.label, Literal("Physical Specification")))

    g.add((BATT.ThermalSpecification, RDF.type, OWL.Class))
    g.add((BATT.ThermalSpecification, RDFS.subClassOf, BATT.Specification))
    g.add((BATT.ThermalSpecification, RDFS.label, Literal("Thermal Specification")))

    g.add((BATT.LifecycleSpecification, RDF.type, OWL.Class))
    g.add((BATT.LifecycleSpecification, RDFS.subClassOf, BATT.Specification))
    g.add((BATT.LifecycleSpecification, RDFS.label, Literal("Lifecycle Specification")))

    g.add((BATT.Unit, RDF.type, OWL.Class))
    g.add((BATT.Unit, RDFS.label, Literal("Unit of Measurement")))

    g.add((BATT.Manufacturer, RDF.type, OWL.Class))
    g.add((BATT.Manufacturer, RDFS.label, Literal("Manufacturer")))

    g.add((BATT.Chemistry, RDF.type, OWL.Class))
    g.add((BATT.Chemistry, RDFS.label, Literal("Battery Chemistry")))

    g.add((BATT.hasSpecification, RDF.type, OWL.ObjectProperty))
    g.add((BATT.hasSpecification, RDFS.domain, BATT.Battery))
    g.add((BATT.hasSpecification, RDFS.range, BATT.Specification))

    g.add((BATT.hasManufacturer, RDF.type, OWL.ObjectProperty))
    g.add((BATT.hasManufacturer, RDFS.domain, BATT.Battery))
    g.add((BATT.hasManufacturer, RDFS.range, BATT.Manufacturer))

    g.add((BATT.hasChemistry, RDF.type, OWL.ObjectProperty))
    g.add((BATT.hasChemistry, RDFS.domain, BATT.Battery))
    g.add((BATT.hasChemistry, RDFS.range, BATT.Chemistry))

    g.add((BATT.hasUnit, RDF.type, OWL.ObjectProperty))
    g.add((BATT.hasUnit, RDFS.domain, BATT.Specification))
    g.add((BATT.hasUnit, RDFS.range, BATT.Unit))

    _add_datatype_property(g, BATT.batteryModel, BATT.Battery, XSD.string,
                           "Battery Model", "Model name/number of the battery")
    _add_datatype_property(g, BATT.hasValue, BATT.Specification, XSD.float,
                           "Value", "Numeric value of a specification")
    _add_datatype_property(g, BATT.specName, BATT.Specification, XSD.string,
                           "Specification Name", "Name/label of the specification")
    _add_datatype_property(g, BATT.manufacturerName, BATT.Manufacturer, XSD.string,
                           "Manufacturer Name", "Name of the manufacturer company")
    _add_datatype_property(g, BATT.chemistryType, BATT.Chemistry, XSD.string,
                           "Chemistry Type", "Battery chemistry type identifier")
    _add_datatype_property(g, BATT.unitSymbol, BATT.Unit, XSD.string,
                           "Unit Symbol", "Symbol of the unit (e.g., V, mAh, C)")
    _add_datatype_property(g, BATT.unitName, BATT.Unit, XSD.string,
                           "Unit Name", "Full name of the unit")

    units = {
        "Volt": ("V", "Volt"),
        "Milliampere_Hour": ("mAh", "Milliampere-hour"),
        "Milliohm": ("mOhm", "Milliohm"),
        "Ampere": ("A", "Ampere"),
        "Celsius": ("C", "Degree Celsius"),
        "Gram": ("g", "Gram"),
        "Watt_Hour": ("Wh", "Watt-hour"),
        "Cycle": ("cycles", "Charge/Discharge Cycle"),
        "Percent_Per_Month": ("%/month", "Percent per Month"),
    }

    for unit_id, (symbol, name) in units.items():
        unit_uri = UNIT[unit_id]
        g.add((unit_uri, RDF.type, BATT.Unit))
        g.add((unit_uri, BATT.unitSymbol, Literal(symbol)))
        g.add((unit_uri, BATT.unitName, Literal(name)))

    chemistries = ["Li-ion", "LiFePO4", "Li-Polymer", "LiCoO2", "NMC", "LTO"]

    for chem in chemistries:
        chem_uri = INST[chem.replace("-", "_")]
        g.add((chem_uri, RDF.type, BATT.Chemistry))
        g.add((chem_uri, BATT.chemistryType, Literal(chem)))

    return g


def _add_datatype_property(g, prop_uri, domain, range_type, label, comment):
    g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
    g.add((prop_uri, RDFS.domain, domain))
    g.add((prop_uri, RDFS.range, range_type))
    g.add((prop_uri, RDFS.label, Literal(label)))
    g.add((prop_uri, RDFS.comment, Literal(comment)))


FIELD_TO_SPEC = {
    "nominal_voltage_V": {
        "name": "Nominal Voltage",
        "class": "ElectricalSpecification",
        "unit": "Volt",
    },
    "nominal_capacity_mAh": {
        "name": "Nominal Capacity",
        "class": "ElectricalSpecification",
        "unit": "Milliampere_Hour",
    },
    "min_capacity_mAh": {
        "name": "Minimum Capacity",
        "class": "ElectricalSpecification",
        "unit": "Milliampere_Hour",
    },
    "internal_resistance_mOhm": {
        "name": "Internal Resistance",
        "class": "ElectricalSpecification",
        "unit": "Milliohm",
    },
    "charge_voltage_V": {
        "name": "Charge Voltage",
        "class": "ElectricalSpecification",
        "unit": "Volt",
    },
    "discharge_cutoff_voltage_V": {
        "name": "Discharge Cutoff Voltage",
        "class": "ElectricalSpecification",
        "unit": "Volt",
    },
    "max_charge_current_A": {
        "name": "Maximum Charge Current",
        "class": "ElectricalSpecification",
        "unit": "Ampere",
    },
    "max_discharge_current_A": {
        "name": "Maximum Discharge Current",
        "class": "ElectricalSpecification",
        "unit": "Ampere",
    },
    "standard_charge_current_A": {
        "name": "Standard Charge Current",
        "class": "ElectricalSpecification",
        "unit": "Ampere",
    },
    "standard_discharge_current_A": {
        "name": "Standard Discharge Current",
        "class": "ElectricalSpecification",
        "unit": "Ampere",
    },
    "operating_temp_min_C": {
        "name": "Minimum Operating Temperature",
        "class": "ThermalSpecification",
        "unit": "Celsius",
    },
    "operating_temp_max_C": {
        "name": "Maximum Operating Temperature",
        "class": "ThermalSpecification",
        "unit": "Celsius",
    },
    "storage_temp_min_C": {
        "name": "Minimum Storage Temperature",
        "class": "ThermalSpecification",
        "unit": "Celsius",
    },
    "storage_temp_max_C": {
        "name": "Maximum Storage Temperature",
        "class": "ThermalSpecification",
        "unit": "Celsius",
    },
    "weight_g": {
        "name": "Weight",
        "class": "PhysicalSpecification",
        "unit": "Gram",
    },
    "energy_Wh": {
        "name": "Energy",
        "class": "ElectricalSpecification",
        "unit": "Watt_Hour",
    },
    "cycle_life": {
        "name": "Cycle Life",
        "class": "LifecycleSpecification",
        "unit": "Cycle",
    },
    "self_discharge_rate_percent_per_month": {
        "name": "Self-Discharge Rate",
        "class": "LifecycleSpecification",
        "unit": "Percent_Per_Month",
    },
}
