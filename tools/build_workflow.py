"""Build an importable n8n workflow JSON or Make scenario blueprint from a simple spec.

Claude writes a short spec (nodes/modules + connections); this script validates it,
assigns ids and a readable left-to-right layout, and emits the platform's import format.
Free. Only --push makes an external call (creates the workflow in your account, inactive).

Usage:
    .venv/bin/python tools/build_workflow.py --platform n8n  --spec spec.json --out n8n-workflow.json [--push]
    .venv/bin/python tools/build_workflow.py --platform make --spec spec.json --out make-blueprint.json [--push]

n8n spec:
{
  "name": "Lead intake agent",
  "nodes": [
    {"name": "New Form Submission", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "parameters": {}},
    {"name": "AI Agent", "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 1.7,
     "notes": "Qualifies the lead"},
    {"name": "Chat Model", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi", "typeVersion": 1}
  ],
  "connections": [
    {"from": "New Form Submission", "to": "AI Agent"},
    {"from": "Chat Model", "to": "AI Agent", "type": "ai_languageModel"},
    {"from": "Is Qualified?", "to": "Slack", "output": 0}          # IF true branch; output 1 = false
  ],
  "stickies": [{"content": "## Human approval\\nSales manager approves in Slack"}]
}
Connection types other than "main" (ai_languageModel, ai_tool, ai_memory, ai_vectorStore,
ai_embedding, ai_document, ai_textSplitter, ai_outputParser) attach sub-nodes; they are drawn under their parent.

Make spec:
{
  "name": "Invoice processing",
  "instant": true,
  "flow": [
    {"module": "gateway:CustomWebHook", "version": 1, "label": "Invoice received"},
    {"module": "builtin:BasicFeeder", "version": 1, "label": "Each line item", "mapper": {"array": "{{1.items}}"}},
    {"module": "builtin:BasicAggregator", "version": 1, "label": "Collect lines", "feeder": "Each line item"},
    {"module": "builtin:BasicRouter", "version": 1, "label": "Route",
     "routes": [
        {"filter": {"name": "Over $5k"}, "flow": [{"module": "slack:CreateMessage", "version": 4, "label": "Ask approval"}]},
        {"flow": [{"module": "google-sheets:addRow", "version": 2, "label": "Log invoice"}]}
     ]}
  ]
A router must be the last module in its flow (Make continues only inside its routes).
}
Optional "scenario_settings" overrides the scenario metadata, e.g. {"dlq": true} to store incomplete
executions (required for builtin:Break retry handlers).
Any module may carry "filter" (applies to the link into it) and "onerror" (a list of handler modules,
e.g. {"module": "builtin:Break"}). "feeder" is resolved from a label to the iterator's module id.
"""

import argparse
import json
import os
import sys
import uuid
from collections import defaultdict, deque
from pathlib import Path

import requests
from dotenv import load_dotenv

X_STEP, Y_STEP, SUB_Y = 280, 200, 220


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- n8n

def build_n8n(spec: dict) -> dict:
    nodes = spec.get("nodes") or fail("spec.nodes is empty")
    names = [n.get("name") or fail(f"node without a name: {n}") for n in nodes]
    dupes = {x for x in names if names.count(x) > 1}
    if dupes:
        fail(f"duplicate node names: {sorted(dupes)}")
    for n in nodes:
        if not n.get("type"):
            fail(f"node '{n['name']}' has no type")

    main_out = defaultdict(list)  # from -> [to]
    sub_parent = {}               # sub-node -> parent
    connections: dict = {}
    has_main_in = set()
    for c in spec.get("connections", []):
        src, dst = c.get("from"), c.get("to")
        for end in (src, dst):
            if end not in names:
                fail(f"connection references unknown node '{end}'")
        ctype = c.get("type", "main")
        out_idx = int(c.get("output", 0))
        slots = connections.setdefault(src, {}).setdefault(ctype, [])
        while len(slots) <= out_idx:
            slots.append([])
        slots[out_idx].append({"node": dst, "type": ctype, "index": int(c.get("input", 0))})
        if ctype == "main":
            main_out[src].append(dst)
            has_main_in.add(dst)
        else:
            sub_parent[src] = dst

    main_nodes = [n for n in names if n not in sub_parent]
    roots = [n for n in main_nodes if n not in has_main_in]
    if not roots:
        fail("no entry node: every main node has an incoming connection (need a trigger)")
    triggers = [n for n in nodes if n["name"] in roots]
    warnings = []
    for t in triggers:
        low = t["type"].lower()
        if not any(k in low for k in ("trigger", "webhook", "schedule", "cron", "form")):
            warnings.append(f"entry node '{t['name']}' ({t['type']}) does not look like a trigger")

    # BFS depth from roots; back-edges (loops such as splitInBatches) are ignored for layout.
    depth = {}
    q = deque()
    for r in roots:
        depth[r] = 0
        q.append(r)
    while q:
        cur = q.popleft()
        for nxt in main_out[cur]:
            if nxt not in depth:
                depth[nxt] = depth[cur] + 1
                q.append(nxt)
    orphans = [n for n in main_nodes if n not in depth]
    if orphans:
        fail(f"nodes not reachable from any trigger: {orphans}")

    columns = defaultdict(list)
    for n in main_nodes:
        columns[depth[n]].append(n)
    pos = {}
    for d, col in columns.items():
        for i, n in enumerate(col):
            pos[n] = [d * X_STEP, int((i - (len(col) - 1) / 2) * Y_STEP)]
    kids = defaultdict(list)
    for child, parent in sub_parent.items():
        kids[parent].append(child)
    for parent, children in kids.items():
        px, py = pos.get(parent) or fail(f"sub-node parent '{parent}' is itself a sub-node; attach to a main node")
        for i, child in enumerate(children):
            pos[child] = [int(px + (i - (len(children) - 1) / 2) * 160), py + SUB_Y]

    out_nodes = []
    for n in nodes:
        node = {
            "id": str(uuid.uuid4()),
            "name": n["name"],
            "type": n["type"],
            "typeVersion": n.get("typeVersion", 1),
            "position": pos[n["name"]],
            "parameters": n.get("parameters", {}),
        }
        if n.get("notes"):
            node["notes"] = n["notes"]
            node["notesInFlow"] = True
        if n.get("credentials"):
            node["credentials"] = n["credentials"]
        if n.get("onError"):
            node["onError"] = n["onError"]  # continueRegularOutput | continueErrorOutput | stopWorkflow
        if n.get("retryOnFail"):
            node["retryOnFail"] = True
            node["maxTries"] = n.get("maxTries", 3)
        out_nodes.append(node)

    top = min(p[1] for p in pos.values()) - 360
    for i, s in enumerate(spec.get("stickies", [])):
        out_nodes.append({
            "id": str(uuid.uuid4()),
            "name": f"Sticky Note{'' if i == 0 else ' ' + str(i + 1)}",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [i * 380, top],
            "parameters": {"content": s["content"], "width": s.get("width", 340), "height": s.get("height", 240)},
        })

    wf = {
        "name": spec.get("name", "Generated workflow"),
        "nodes": out_nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1", **spec.get("settings", {})},
    }
    return wf, warnings


def push_n8n(wf: dict) -> None:
    base, key = os.getenv("N8N_BASE_URL"), os.getenv("N8N_API_KEY")
    if not base or not key:
        fail("N8N_BASE_URL and N8N_API_KEY must be set in .env to push")
    r = requests.post(f"{base.rstrip('/')}/api/v1/workflows", headers={"X-N8N-API-KEY": key},
                      json={k: wf[k] for k in ("name", "nodes", "connections", "settings")}, timeout=60)
    if r.status_code >= 300:
        fail(f"n8n rejected the workflow ({r.status_code}): {r.text[:500]}")
    print(f"Pushed to n8n (inactive): id={r.json().get('id')}")


# ---------------------------------------------------------------- Make

def build_make(spec: dict) -> dict:
    flow = spec.get("flow") or fail("spec.flow is empty")
    counter = [0]
    labels = {}
    pending_feeders = []

    def convert(mods: list, x0: int, y: int) -> list:
        out = []
        x = x0
        for m in mods:
            if not m.get("module"):
                fail(f"module without 'module' id: {m}")
            counter[0] += 1
            mid = counter[0]
            label = m.get("label")
            if label:
                if label in labels:
                    fail(f"duplicate module label '{label}'")
                labels[label] = mid
            mod = {
                "id": mid,
                "module": m["module"],
                "version": m.get("version", 1),
                "parameters": m.get("parameters", {}),
                "mapper": m.get("mapper", {}),
                "metadata": {"designer": {"x": x, "y": y, **({"name": label} if label else {})}},
            }
            if m.get("filter"):
                mod["filter"] = {"name": m["filter"].get("name", ""), "conditions": m["filter"].get("conditions", [])}
            if m.get("feeder"):
                pending_feeders.append((mod, m["feeder"]))
            if m.get("onerror"):
                mod["onerror"] = convert(m["onerror"], x + 150, y + 180)
            if m.get("routes"):
                if m is not mods[-1]:
                    fail(f"router '{label}' must be the last module in its flow; put later steps inside its routes")
                mod["routes"] = []
                for i, route in enumerate(m["routes"]):
                    rflow = route.get("flow") or fail(f"router '{label}' route {i} has an empty flow")
                    if route.get("filter"):
                        rflow = [{**rflow[0], "filter": route["filter"]}] + rflow[1:]
                    mod["routes"].append({"flow": convert(rflow, x + 300, y + i * 300)})
            out.append(mod)
            x += 300
        return out

    blueprint_flow = convert(flow, 0, 0)
    for mod, feeder_label in pending_feeders:
        if feeder_label not in labels:
            fail(f"aggregator feeder '{feeder_label}' does not match any module label")
        mod["parameters"] = {**mod["parameters"], "feeder": labels[feeder_label]}

    warnings = []
    first = flow[0]["module"]
    if not any(k in first.lower() for k in ("webhook", "watch", "trigger", "gateway", "schedule")):
        warnings.append(f"first module '{first}' does not look like a trigger")

    bp = {
        "name": spec.get("name", "Generated scenario"),
        "flow": blueprint_flow,
        "metadata": {
            "instant": bool(spec.get("instant", False)),
            "version": 1,
            "scenario": {
                "roundtrips": 1, "maxErrors": 3, "autoCommit": True, "autoCommitTriggerLast": True,
                "sequential": False, "confidential": False, "dataloss": False, "dlq": False,
                "freshVariables": False,
                # e.g. {"dlq": true} so Break (retry) handlers can store incomplete executions
                **spec.get("scenario_settings", {}),
            },
            "designer": {"orphans": []},
        },
    }
    return bp, warnings


def push_make(bp: dict, scheduling: dict) -> None:
    zone, token, team = os.getenv("MAKE_ZONE"), os.getenv("MAKE_API_TOKEN"), os.getenv("MAKE_TEAM_ID")
    if not zone or not token or not team:
        fail("MAKE_ZONE (e.g. eu1.make.com), MAKE_API_TOKEN and MAKE_TEAM_ID must be set in .env to push")
    # Accept "us2", "us2.make.com" or "https://us2.make.com/".
    zone = zone.strip().removeprefix("https://").removeprefix("http://").strip("/")
    if "." not in zone:
        zone = f"{zone}.make.com"
    # A common mix-up: the organization id is pasted instead of the team id, which makes Make answer 403.
    org_check = requests.get(f"https://{zone}/api/v2/organizations/{team}",
                             headers={"Authorization": f"Token {token}"}, timeout=30)
    if org_check.ok:
        fail(f"MAKE_TEAM_ID={team} is an organization id, not a team id. Find the team id under Team in Make.")
    r = requests.post(
        f"https://{zone}/api/v2/scenarios", params={"confirmed": "true"},
        headers={"Authorization": f"Token {token}"},
        json={"blueprint": json.dumps(bp), "teamId": int(team), "scheduling": json.dumps(scheduling)},
        timeout=60,
    )
    if r.status_code >= 300:
        fail(f"Make rejected the blueprint ({r.status_code}): {r.text[:500]}")
    print(f"Pushed to Make (inactive): scenario id={r.json().get('scenario', {}).get('id')}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--platform", required=True, choices=["n8n", "make"])
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--push", action="store_true", help="Create it in your account via API (needs .env keys)")
    args = p.parse_args()

    spec = json.loads(args.spec.read_text())
    if args.platform == "n8n":
        result, warnings = build_n8n(spec)
        count = len([n for n in result["nodes"] if n["type"] != "n8n-nodes-base.stickyNote"])
    else:
        result, warnings = build_make(spec)
        count = sum(1 for _ in json.dumps(result).split('"module":')) - 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    print(f"Built {args.platform} workflow '{result['name']}' with {count} nodes/modules -> {args.out}")
    for w in warnings:
        print(f"WARNING: {w}")

    if args.push:
        load_dotenv()
        if args.platform == "n8n":
            push_n8n(result)
        else:
            push_make(result, spec.get("scheduling", {"type": "on-demand"}))


if __name__ == "__main__":
    main()
