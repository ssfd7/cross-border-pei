"""Shared paths and connection settings for the prototype."""
import os
from pathlib import Path

from rdflib import Namespace

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model" / "xb-pei-model.ttl"
GOVERNANCE = ROOT / "model" / "xb-pei-governance.ttl"
BUNDLE = ROOT / "solution" / "bundle"
MAPPINGS = BUNDLE / "references" / "mappings"
GRAPH_MAPPING = MAPPINGS / "graph" / "ladybug.yaml"
DOCUMENTS = ROOT / "solution" / "documents"
SHAPES = ROOT / "solution" / "shapes"
GRAPH_DB = ROOT / "solution" / ".data" / "graph.lbug"

XBPEI = Namespace("https://w3id.org/xb-pei/ontology#")
DSN = os.environ.get("XBPEI_DSN", "postgresql://xbpei_agent:xbpei_agent@localhost:54329/xbpei")
ADMIN_DSN = os.environ.get("XBPEI_ADMIN_DSN", "postgresql://xbpei_admin:xbpei_admin@localhost:54329/xbpei")
CONTROL_DSN = os.environ.get("XBPEI_CONTROL_DSN", "postgresql://xbpei_control:xbpei_control@localhost:54329/xbpei")
GOLD = ROOT / "solution" / "gold" / "answer-key.yaml"
BUSINESS = ROOT / "business"
REVIEWER_DSN = os.environ.get("XBPEI_REVIEWER_DSN", "postgresql://xbpei_reviewer:xbpei_reviewer@localhost:54329/xbpei")
