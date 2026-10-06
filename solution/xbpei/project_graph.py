"""Rebuild the read-only graph from the legacy schemas, following the mapping files.

The graph is shaped for path questions, not after the ontology: an Ownership Interest, a
Jurisdiction Fact and a Payment Event are each an edge. Property names are the ontology's.
Every edge names the row it came from (sourceRef) and whether that row is the system of record.
One Party node stands for the same party in every system; systems are matched on LEI, then on
registration number, never on name.

    python -m xbpei.project_graph
"""
import shutil
from datetime import date

import psycopg
import real_ladybug as lb

from . import DSN, GRAPH_DB

SCHEMA = [
    """CREATE NODE TABLE Party(id STRING PRIMARY KEY, name STRING, kind STRING, isFundVehicle BOOLEAN,
        isSPV BOOLEAN, isPortfolioCompany BOOLEAN, leiCode STRING, legalForm STRING, sourceRefs STRING[])""",
    "CREATE NODE TABLE Jurisdiction(id STRING PRIMARY KEY, countryCode STRING, subdivisionCode STRING)",
    """CREATE REL TABLE HOLDS(FROM Party TO Party, identifier STRING, economicPercentage DOUBLE,
        votingPercentage DOUBLE, shareClass STRING, holdingCapacity STRING, heldThrough STRING,
        validFrom DATE, validTo DATE, sourceRef STRING, systemOfRecord BOOLEAN)""",
    """CREATE REL TABLE JURISDICTION_FACT(FROM Party TO Jurisdiction, factType STRING, validFrom DATE,
        validTo DATE, recordedOn DATE, sourceRef STRING, systemOfRecord BOOLEAN)""",
    """CREATE REL TABLE PAYMENT(FROM Party TO Party, identifier STRING, paymentType STRING, amount DOUBLE,
        currencyCode STRING, occurredOn DATE, sourceRef STRING)""",
]
# Party sources, system of record first: its identifier and name become the node's.
PARTY_SOURCES = [
    ("entity_mgmt.legal_entity", """SELECT entity_id, legal_name, lei, reg_no, legal_form, 'LegalEntity',
        is_fund = 'Y', is_spv = 'Y', is_portco = 'Y' FROM entity_mgmt.legal_entity ORDER BY 1"""),
    ("investor_register.investor", """SELECT inv_no, display_name, lei, reg_no, legal_form,
        CASE inv_type WHEN 'IND' THEN 'NaturalPerson' ELSE 'LegalEntity' END, false, false, false
        FROM investor_register.investor ORDER BY 1"""),
    ("investor_register.fund", "SELECT fund_code, fund_name, lei, NULL, NULL, 'LegalEntity', true, false, false FROM investor_register.fund ORDER BY 1"),
    ("treasury.counterparty", "SELECT cp_id, cp_name, lei, reg_no, NULL, 'LegalEntity', false, false, false FROM treasury.counterparty ORDER BY 1"),
]
FACT_TYPES = {"INC": "Incorporation", "TAXRES": "TaxResidence", "OPS": "OperatingLocation"}
PAYMENT_TYPES = {"CAPCALL": "CapitalContribution", "MGMTFEE": "ManagementFee", "DIV": "Dividend", "DIST": "Distribution"}


def resolve_parties(pg) -> tuple[dict, dict]:
    """Party nodes by id, and the node id for each (source table, key)."""
    parties, node_of, by_identifier = {}, {}, {}
    for table, sql in PARTY_SOURCES:
        for key, name, lei, reg_no, legal_form, kind, is_fund, is_spv, is_portco in pg.execute(sql):
            node_id = by_identifier.get(("lei", lei)) or by_identifier.get(("reg_no", reg_no))
            if node_id is None:
                node_id = key
                parties[node_id] = {"id": key, "name": name, "kind": kind, "isFundVehicle": False, "isSPV": False,
                                    "isPortfolioCompany": False, "leiCode": lei, "legalForm": legal_form, "sourceRefs": []}
            party = parties[node_id]
            party["isFundVehicle"] |= is_fund
            party["isSPV"] |= is_spv
            party["isPortfolioCompany"] |= is_portco
            party["leiCode"] = party["leiCode"] or lei
            party["legalForm"] = party["legalForm"] or legal_form
            party["sourceRefs"].append(f"{table}:{key}")
            node_of[table, key] = node_id
            for scheme, value in (("lei", lei), ("reg_no", reg_no)):
                if value:
                    by_identifier.setdefault((scheme, value), node_id)
    return parties, node_of


def holdings(pg, node_of: dict) -> list[dict]:
    """HOLDS edges from the four places an Ownership Interest lives."""
    investor, entity, fund = "investor_register.investor", "entity_mgmt.legal_entity", "investor_register.fund"
    nominees = {r[0] for r in pg.execute("SELECT DISTINCT owned_inv_no FROM onboarding.declared_owner WHERE alloc_basis = 'NOMINEE_ALLOC'")}
    edges, commitments = [], []
    for cid, inv, code, econ, vote, cls, start, end in pg.execute(
            "SELECT commit_id, inv_no, fund_code, unit_pct, vote_pct, unit_class, from_dt, to_dt FROM investor_register.commitment ORDER BY 1"):
        commitments.append((cid, inv, code, econ, vote, start, end))
        edges.append({"from": node_of[investor, inv], "to": node_of[fund, code], "identifier": cid, "econ": econ, "vote": vote,
                      "shareClass": cls, "capacity": "nominee" if inv in nominees else "beneficial", "heldThrough": None,
                      "start": start, "end": end, "sourceRef": f"investor_register.commitment:{cid}", "systemOfRecord": True})
    registered = {(e["from"], e["to"]) for e in edges}
    for hid, owner, owned, econ, vote, cls, start, end in pg.execute(
            "SELECT holding_id, owner_entity_id, owned_entity_id, pct_econ, pct_vote, share_class, eff_from, eff_to FROM entity_mgmt.shareholding ORDER BY 1"):
        pair = node_of[entity, owner], node_of[entity, owned]
        edges.append({"from": pair[0], "to": pair[1], "identifier": hid, "econ": econ, "vote": vote, "shareClass": cls,
                      "capacity": "beneficial", "heldThrough": None, "start": start, "end": end,
                      "sourceRef": f"entity_mgmt.shareholding:{hid}", "systemOfRecord": pair not in registered})
    for did, owned, owner, econ, vote, basis, start, end in pg.execute(
            "SELECT decl_id, owned_inv_no, owner_inv_no, pct_econ, pct_vote, alloc_basis, from_dt, to_dt FROM onboarding.declared_owner ORDER BY 1"):
        base = {"from": node_of[investor, owner], "shareClass": None, "capacity": "beneficial",
                "sourceRef": f"onboarding.declared_owner:{did}", "systemOfRecord": True}
        if basis == "OWNERSHIP":
            edges.append(dict(base, to=node_of[investor, owned], identifier=did, econ=econ, vote=vote, heldThrough=None, start=start, end=end))
            continue
        # A nominee allocation is a beneficial interest in whatever the nominee holds of record.
        for cid, inv, code, c_econ, c_vote, c_start, c_end in commitments:
            overlap_start, overlap_end = max(start, c_start), min(end or date.max, c_end or date.max)
            if inv == owned and overlap_start <= overlap_end:
                edges.append(dict(base, to=node_of[fund, code], identifier=f"{did}/{cid}", econ=econ * c_econ / 100,
                                  vote=vote * c_vote / 100, heldThrough=cid, start=overlap_start,
                                  end=None if overlap_end == date.max else overlap_end))
    return edges


def jurisdiction_facts(pg, node_of: dict) -> list[dict]:
    facts = []
    for eid, country, sub, cap, start, end, recorded in pg.execute(
            "SELECT entity_id, country, subdivision, capacity_cd, from_dt, to_dt, recorded_dt FROM entity_mgmt.entity_jurisdiction ORDER BY 1, 4, 2"):
        facts.append({"party": node_of["entity_mgmt.legal_entity", eid], "country": country, "subdivision": sub,
                      "factType": FACT_TYPES[cap], "start": start, "end": end, "recordedOn": recorded,
                      "sourceRef": f"entity_mgmt.entity_jurisdiction:{eid}/{cap}/{country}/{start}", "systemOfRecord": True})
    for inv, country, start, end, recorded in pg.execute(
            "SELECT inv_no, country, from_dt, to_dt, recorded_dt FROM onboarding.residence_record ORDER BY 1, 3"):
        facts.append({"party": node_of["investor_register.investor", inv], "country": country, "subdivision": None,
                      "factType": "TaxResidence", "start": start, "end": end, "recordedOn": recorded,
                      "sourceRef": f"onboarding.residence_record:{inv}/{country}/{start}", "systemOfRecord": True})
    for inv, inc, res in pg.execute("SELECT inv_no, country_inc, country_res FROM investor_register.investor ORDER BY 1"):
        for country, fact_type, of_record in ((inc, "Incorporation", True), (res, "TaxResidence", False)):
            if country:
                facts.append({"party": node_of["investor_register.investor", inv], "country": country, "subdivision": None,
                              "factType": fact_type, "start": None, "end": None, "recordedOn": None,
                              "sourceRef": f"investor_register.investor:{inv}", "systemOfRecord": of_record})
    return facts


def build() -> dict:
    with psycopg.connect(DSN) as pg:
        parties, node_of = resolve_parties(pg)
        edges, facts = holdings(pg, node_of), jurisdiction_facts(pg, node_of)
        payments = pg.execute("SELECT pay_id, payer_cp, payee_cp, pay_type_cd, amt, ccy, value_dt FROM treasury.payment ORDER BY 1").fetchall()

    if GRAPH_DB.exists():
        shutil.rmtree(GRAPH_DB) if GRAPH_DB.is_dir() else GRAPH_DB.unlink()
    GRAPH_DB.parent.mkdir(exist_ok=True)
    graph = lb.Connection(lb.Database(str(GRAPH_DB)))
    for statement in SCHEMA:
        graph.execute(statement)

    for party in parties.values():
        graph.execute("""CREATE (:Party {id: $id, name: $name, kind: $kind, isFundVehicle: $isFundVehicle, isSPV: $isSPV,
            isPortfolioCompany: $isPortfolioCompany, leiCode: $leiCode, legalForm: $legalForm, sourceRefs: $sourceRefs})""", party)
    places = {(f["subdivision"] or f["country"], f["country"], f["subdivision"]) for f in facts}
    for place_id, country, subdivision in sorted(places, key=lambda p: p[0]):
        graph.execute("CREATE (:Jurisdiction {id: $id, countryCode: $c, subdivisionCode: $s})", {"id": place_id, "c": country, "s": subdivision})
    # Parameter names avoid Cypher keywords such as end, from and to.
    for e in edges:
        graph.execute("""MATCH (a:Party {id: $holder}), (b:Party {id: $held}) CREATE (a)-[:HOLDS {identifier: $identifier,
            economicPercentage: $econ, votingPercentage: $vote, shareClass: $shareClass, holdingCapacity: $capacity,
            heldThrough: $heldThrough, validFrom: $validFrom, validTo: $validTo, sourceRef: $sourceRef, systemOfRecord: $systemOfRecord}]->(b)""",
                      {"holder": e["from"], "held": e["to"], "identifier": e["identifier"], "econ": float(e["econ"]), "vote": float(e["vote"]),
                       "shareClass": e["shareClass"], "capacity": e["capacity"], "heldThrough": e["heldThrough"], "validFrom": e["start"],
                       "validTo": e["end"], "sourceRef": e["sourceRef"], "systemOfRecord": e["systemOfRecord"]})
    for f in facts:
        graph.execute("""MATCH (a:Party {id: $party}), (j:Jurisdiction {id: $place}) CREATE (a)-[:JURISDICTION_FACT {factType: $factType,
            validFrom: $validFrom, validTo: $validTo, recordedOn: $recordedOn, sourceRef: $sourceRef, systemOfRecord: $systemOfRecord}]->(j)""",
                      {"party": f["party"], "place": f["subdivision"] or f["country"], "factType": f["factType"], "validFrom": f["start"],
                       "validTo": f["end"], "recordedOn": f["recordedOn"], "sourceRef": f["sourceRef"], "systemOfRecord": f["systemOfRecord"]})
    for pay_id, payer, payee, type_cd, amount, currency, value_date in payments:
        graph.execute("""MATCH (a:Party {id: $payer}), (b:Party {id: $payee}) CREATE (a)-[:PAYMENT {identifier: $id, paymentType: $type,
            amount: $amount, currencyCode: $currency, occurredOn: $occurredOn, sourceRef: $ref}]->(b)""",
                      {"payer": node_of["treasury.counterparty", payer], "payee": node_of["treasury.counterparty", payee], "id": pay_id,
                       "type": PAYMENT_TYPES[type_cd], "amount": float(amount), "currency": currency, "occurredOn": value_date,
                       "ref": f"treasury.payment:{pay_id}"})
    return {"Party": len(parties), "Jurisdiction": len(places), "HOLDS": len(edges), "JURISDICTION_FACT": len(facts), "PAYMENT": len(payments)}


if __name__ == "__main__":
    print("Graph rebuilt:", ", ".join(f"{count} {name}" for name, count in build().items()))
