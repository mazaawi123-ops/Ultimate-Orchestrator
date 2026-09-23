"""Create the three small fixture repos the evals run against.

Usage (from the repo root):  python evals/make_fixtures.py
Writes evals/fixtures/<name>/ and makes each one a git repo with a single commit,
so the orchestrator has a clean BASE to branch from. Existing fixture folders are
left alone; delete one to recreate it.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = {
    "todo-cli": {
        ".gitignore": "__pycache__/\n*.json\n.orchestrator/\n",
        "README.md": "# todo-cli\nTiny stdlib-only todo CLI. Run tests with `python -m pytest -q`.\nUsage: `python -m todo.cli add \"title\"`, `python -m todo.cli list [--all]`, `python -m todo.cli done <id>`.\n",
        "tests/test_store.py": "from todo.store import Store\n\n\ndef test_add_and_list(tmp_path):\n    s = Store(tmp_path / \"db.json\")\n    s.add(\"buy milk\")\n    s.add(\"write report\")\n    assert [i[\"title\"] for i in s.list()] == [\"buy milk\", \"write report\"]\n\n\ndef test_complete_hides_from_default_list(tmp_path):\n    s = Store(tmp_path / \"db.json\")\n    item = s.add(\"x\")\n    s.complete(item[\"id\"])\n    assert s.list() == []\n    assert len(s.list(include_done=True)) == 1\n\n\ndef test_persists(tmp_path):\n    p = tmp_path / \"db.json\"\n    Store(p).add(\"a\")\n    assert Store(p).list()[0][\"title\"] == \"a\"\n",
        "todo/__init__.py": "",
        "todo/cli.py": "import argparse\nimport os\nfrom .store import Store\n\n\ndef main(argv=None):\n    p = argparse.ArgumentParser(prog=\"todo\")\n    p.add_argument(\"--db\", default=os.environ.get(\"TODO_DB\", \"todo.json\"))\n    sub = p.add_subparsers(dest=\"cmd\", required=True)\n    a = sub.add_parser(\"add\"); a.add_argument(\"title\")\n    d = sub.add_parser(\"done\"); d.add_argument(\"id\", type=int)\n    l = sub.add_parser(\"list\"); l.add_argument(\"--all\", action=\"store_true\")\n    args = p.parse_args(argv)\n    store = Store(args.db)\n    if args.cmd == \"add\":\n        item = store.add(args.title)\n        print(f\"added #{item['id']}: {item['title']}\")\n    elif args.cmd == \"done\":\n        item = store.complete(args.id)\n        print(f\"done #{item['id']}\")\n    elif args.cmd == \"list\":\n        for i in store.list(include_done=args.all):\n            mark = \"x\" if i[\"done\"] else \" \"\n            print(f\"[{mark}] #{i['id']} {i['title']}\")\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "todo/store.py": "import json\nfrom pathlib import Path\n\n\nclass Store:\n    \"\"\"JSON-backed todo storage. Each item: {\"id\": int, \"title\": str, \"done\": bool}.\"\"\"\n\n    def __init__(self, path):\n        self.path = Path(path)\n        self.items = []\n        if self.path.exists():\n            self.items = json.loads(self.path.read_text())\n\n    def save(self):\n        self.path.write_text(json.dumps(self.items, indent=2))\n\n    def add(self, title):\n        new_id = max((i[\"id\"] for i in self.items), default=0) + 1\n        item = {\"id\": new_id, \"title\": title, \"done\": False}\n        self.items.append(item)\n        self.save()\n        return item\n\n    def complete(self, item_id):\n        for i in self.items:\n            if i[\"id\"] == item_id:\n                i[\"done\"] = True\n                self.save()\n                return i\n        raise KeyError(item_id)\n\n    def list(self, include_done=False):\n        return [i for i in self.items if include_done or not i[\"done\"]]\n"
    },
    "inventory": {
        ".gitignore": "__pycache__/\n.orchestrator/\n",
        "README.md": "# inventory\nTiny stdlib-only inventory module. Tests: `python -m pytest -q`.\n",
        "inventory/__init__.py": "",
        "inventory/stock.py": "class InsufficientStock(Exception):\n    pass\n\n\nclass Inventory:\n    \"\"\"In-memory stock levels keyed by SKU.\"\"\"\n\n    def __init__(self):\n        self._levels = {}\n\n    def receive(self, sku, qty):\n        if qty <= 0:\n            raise ValueError(\"qty must be positive\")\n        self._levels[sku] = self._levels.get(sku, 0) + qty\n\n    def ship(self, sku, qty):\n        if qty <= 0:\n            raise ValueError(\"qty must be positive\")\n        current = self._levels.get(sku, 0)\n        # BUG: allows shipping more than we have, driving stock negative\n        self._levels[sku] = current - qty\n\n    def level(self, sku):\n        return self._levels.get(sku, 0)\n\n    def low_stock(self, threshold=5):\n        return sorted(s for s, q in self._levels.items() if q < threshold)\n",
        "tests/test_stock.py": "import pytest\nfrom inventory.stock import Inventory\n\n\ndef test_receive_and_level():\n    inv = Inventory()\n    inv.receive(\"A\", 10)\n    assert inv.level(\"A\") == 10\n\n\ndef test_ship_reduces():\n    inv = Inventory()\n    inv.receive(\"A\", 10)\n    inv.ship(\"A\", 4)\n    assert inv.level(\"A\") == 6\n\n\ndef test_low_stock():\n    inv = Inventory()\n    inv.receive(\"A\", 2)\n    inv.receive(\"B\", 20)\n    assert inv.low_stock() == [\"A\"]\n\n\ndef test_rejects_nonpositive():\n    inv = Inventory()\n    with pytest.raises(ValueError):\n        inv.receive(\"A\", 0)\n"
    },
    "textkit": {
        ".gitignore": "node_modules/\n.orchestrator/\n",
        "README.md": "# textkit\nZero-dependency string helpers (ESM). Tests: `npm test` (Node built-in runner).\n",
        "package.json": "{\n  \"name\": \"textkit\",\n  \"version\": \"0.1.0\",\n  \"type\": \"module\",\n  \"scripts\": { \"test\": \"node --test test/*.test.js\" }\n}\n",
        "src/index.js": "export { slugify } from \"./slug.js\";\nexport { wrap } from \"./wrap.js\";\n",
        "src/slug.js": "export function slugify(input) {\n  return String(input)\n    .toLowerCase()\n    .trim()\n    .replace(/[^a-z0-9]+/g, \"-\")\n    .replace(/^-+|-+$/g, \"\");\n}\n",
        "src/wrap.js": "// Hard-wrap text at `width` columns, breaking on spaces.\nexport function wrap(text, width = 80) {\n  const words = String(text).split(/\\s+/).filter(Boolean);\n  const lines = [];\n  let line = \"\";\n  for (const w of words) {\n    if ((line + \" \" + w).trim().length > width && line) {\n      lines.push(line);\n      line = w;\n    } else {\n      line = (line + \" \" + w).trim();\n    }\n  }\n  if (line) lines.push(line);\n  return lines.join(\"\\n\");\n}\n",
        "test/slug.test.js": "import { test } from \"node:test\";\nimport assert from \"node:assert/strict\";\nimport { slugify } from \"../src/slug.js\";\n\ntest(\"basic\", () => assert.equal(slugify(\"Hello World\"), \"hello-world\"));\ntest(\"strips punctuation\", () => assert.equal(slugify(\"  A/B & C!  \"), \"a-b-c\"));\n",
        "test/wrap.test.js": "import { test } from \"node:test\";\nimport assert from \"node:assert/strict\";\nimport { wrap } from \"../src/wrap.js\";\n\ntest(\"wraps at width\", () => {\n  assert.equal(wrap(\"aaa bbb ccc ddd\", 7), \"aaa bbb\\nccc ddd\");\n});\n"
    }
}


def main():
    root = os.path.join(HERE, "fixtures")
    for name, files in FIXTURES.items():
        repo = os.path.join(root, name)
        if os.path.exists(repo):
            print("exists, skipped:", repo)
            continue
        for rel, text in files.items():
            path = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", newline="") as f:
                f.write(text)
        git = ["git", "-C", repo, "-c", "user.name=fixture", "-c", "user.email=fixture@example.com"]
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
        print("created:", repo)


if __name__ == "__main__":
    main()
