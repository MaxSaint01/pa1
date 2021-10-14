#!/usr/bin/python3

import argparse
import configparser
import json
import sys
import os.path

def print_empty_gradescope():
    gradescope_json = {}
    gradescope_json["score"] = 0.0
    gradescope_json["output"] = "We were unable to run the tests due to an error in your code."
    gradescope_json["visibility"] = "visible"
    gradescope_json["stdout_visibility"] = "visible"
    print(json.dumps(gradescope_json, indent=2))

parser = argparse.ArgumentParser()
parser.add_argument("--json-file", default="tests.json")
parser.add_argument("--rubric-file", default="pytest.ini")
parser.add_argument("--csv", action="store_true")
parser.add_argument("--gradescope", action="store_true")
parser.add_argument("--gradescope-visibility", default="after_published")

args = parser.parse_args()

assert args.gradescope_visibility in ("hidden", "after_due_date", "after_published", "visible")

if not os.path.exists(args.json_file):
    print("No such file: {}".format(args.json_file), file=sys.stderr)
    print("Make sure you run py.test before running the grader!", file=sys.stderr)

    if args.gradescope:
        print_empty_gradescope()
    else:
        sys.exit(1)

with open(args.json_file) as f:
    results = json.load(f)

if not os.path.exists(args.rubric_file):
    print("No such file: {}".format(args.rubric_file), file=sys.stderr)
    sys.exit(1)

config = configparser.ConfigParser(delimiters=('='))
config.optionxform = lambda option: option
config.read(args.rubric_file)

if "test-points" not in config:
    print("Error: {} does not have a [test-points] section.".format(args.rubric_file), file=sys.stderr)
    sys.exit(1)

categories = [[name] + value.split(",") for name, value in config["test-points"].items()]
category_names = [name for name, _, _ in categories]
cid2name = {cid: name for name, cid, _ in categories}
total_points = {name: float(points) for name, _, points in categories}

tests = {cname:{} for cname in category_names}

for test in results["included"]:
    if test.get("type") == "test":
        test_id = test["attributes"]["name"]
        outcome = test["attributes"]["outcome"]

        # Check that the test only matches a single category
        cid_matches = [cid for cid in cid2name if cid in test_id]
        if len(cid_matches) == 0:
            print("Error: Test {} does not match any category in the rubric.".format(test_id))
            sys.exit(1)
        elif len(cid_matches) > 1:
            print("Error: Test {} matches more than one category in the rubric: {}".format(test_id, ", ".join(cid_matches)))
            sys.exit(1)

        cid = cid_matches[0]
        cname = cid2name[cid]

        if outcome == "passed":
            tests[cname][test_id] = 1
        else:
            tests[cname][test_id] = 0

empty_categories = [cname for cname in category_names if len(tests[cname]) == 0]

if args.gradescope:
    gradescope_json = {}
    gradescope_json["tests"] = []

if len(empty_categories) > 0:
    print("WARNING: The following categories had no test results:", ", ".join(empty_categories), file=sys.stderr)
    print("         Make sure you run py.test without '-k' before you run the grader\n", file=sys.stderr)

    if args.gradescope:
        gradescope_json["output"] = "We were unable to run some or all of the tests due to an error in your code."

scores = {}
for cname in category_names:
    scores[cname] = {}
    num_total = len(tests[cname])
    num_success = sum(tests[cname].values())
    num_failed = num_total - num_success
    scores[cname] = (num_success, num_failed, num_total)

pscores = []
pscore = 0.0

if not args.csv and not args.gradescope:
    print("%-62s %-6s / %-10s  %-6s / %-10s" % ("Category", "Passed", "Total", "Score", "Points"))
    print("-" * 100)

for cname in category_names:
    (num_success, num_failed, num_total) = scores[cname]

    cpoints = total_points[cname]

    if num_total == 0:
        cscore = 0.0
    else:
        cscore = (float(num_success) / num_total) * cpoints

    pscore += cscore

    if not args.csv and not args.gradescope:
        print("%-62s %-6i / %-10i  %-6.2f / %-10.2f" % (cname, num_success, num_total, cscore, cpoints))
    elif args.gradescope:
        gs_test = {}
        gs_test["score"] = cscore
        gs_test["max_score"] = cpoints
        gs_test["name"] = cname

        gradescope_json["tests"].append(gs_test)

if not args.csv and not args.gradescope:
    print("-" * 100)
    print("%81s = %-6.2f / %-10i" % ("TOTAL", pscore, sum(total_points.values())))
    print("=" * 100)
    print()
pscores.append(pscore)

if args.csv:
    print(",".join([str(s) for s in pscores]))
elif args.gradescope:
    gradescope_json["score"] = pscore
    gradescope_json["visibility"] = args.gradescope_visibility
    gradescope_json["stdout_visibility"] = args.gradescope_visibility

    print(json.dumps(gradescope_json, indent=2))
