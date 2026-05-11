#!/usr/bin/env python3
"""
Section 2: KRO Resource Validation Script
Validates UK8SCluster KRO resources according to certification checklist
"""

import json
import subprocess
import sys
from typing import Dict, List


def run_kubectl(args: List[str]) -> str:
    """Run kubectl command and return output."""
    cmd = ["kubectl"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running kubectl: {e.stderr}", file=sys.stderr)
        return ""


def check_rgd_exists(rgd_name: str) -> bool:
    """Check if ResourceGraphDefinition exists and is active."""
    print(f"Checking ResourceGraphDefinition: {rgd_name}")

    # Check if RGD exists
    output = run_kubectl([
        "get", "resourcegraphdefinition", rgd_name,
        "-o", "jsonpath={.status.state}"
    ])

    if output == "Active":
        print(f"  ✓ {rgd_name} exists and is Active")
        return True
    else:
        print(f"  ✗ {rgd_name} not found or not Active (state: {output})")
        return False


def check_uk8s_instance(instance_name: str, namespace: str) -> Dict:
    """Check UK8SCluster instance status and conditions."""
    print(f"\nChecking UK8SCluster instance: {instance_name}")

    results = {
        "exists": False,
        "state": None,
        "conditions": {}
    }

    # Check if instance exists
    output = run_kubectl([
        "get", "uk8scluster", instance_name,
        "-n", namespace,
        "-o", "json"
    ])

    if not output:
        print(f"  ✗ Instance {instance_name} not found")
        return results

    try:
        instance_data = json.loads(output)
        results["exists"] = True

        # Check state
        state = instance_data.get("status", {}).get("state")
        results["state"] = state
        if state == "ACTIVE":
            print(f"  ✓ Instance state is ACTIVE")
        else:
            print(f"  ✗ Instance state is {state} (expected ACTIVE)")

        # Check conditions
        conditions = instance_data.get("status", {}).get("conditions", [])
        for condition in conditions:
            cond_type = condition.get("type")
            cond_status = condition.get("status")
            results["conditions"][cond_type] = cond_status

            if cond_status == "True":
                print(f"  ✓ Condition {cond_type}: True")
            else:
                print(f"  ✗ Condition {cond_type}: {cond_status}")

        # Check finalizers
        finalizers = instance_data.get("metadata", {}).get("finalizers", [])
        if "kro.run/finalizer" in finalizers:
            print(f"  ✓ Finalizer present")
        else:
            print(f"  ⚠ Finalizer not found")

        # Check labels
        labels = instance_data.get("metadata", {}).get("labels", {})
        if labels.get("kro.run/owned") == "true":
            print(f"  ✓ Label kro.run/owned: true")
        else:
            print(f"  ⚠ Label kro.run/owned not found")

    except json.JSONDecodeError as e:
        print(f"  ✗ Error parsing instance JSON: {e}", file=sys.stderr)

    return results


def check_nested_resources(namespace: str) -> Dict:
    """Check nested KRO resources (UK8Sjobs, UK8SFluxGitOps)."""
    print(f"\nChecking nested KRO resources in namespace {namespace}")

    results = {
        "uk8sjobs": {"exists": False, "ready": False},
        "uk8sfluxgitops": {"exists": False, "ready": False}
    }

    # Check UK8Sjobs
    print("Checking UK8Sjobs instances...")
    output = run_kubectl([
        "get", "uk8sjobs",
        "-n", namespace,
        "-o", "jsonpath={.items[*].metadata.name}"
    ])

    if output:
        job_names = output.split()
        print(f"  Found {len(job_names)} UK8Sjobs instance(s): {', '.join(job_names)}")
        results["uk8sjobs"]["exists"] = True

        # Check first instance status
        if job_names:
            job_status = run_kubectl([
                "get", "uk8sjobs", job_names[0],
                "-n", namespace,
                "-o", "jsonpath={.status.state}"
            ])
            if job_status == "ACTIVE":
                print(f"  ✓ UK8Sjobs state is ACTIVE")
                results["uk8sjobs"]["ready"] = True
            else:
                print(f"  ✗ UK8Sjobs state is {job_status}")
    else:
        print(f"  ⚠ No UK8Sjobs instances found")

    # Check UK8SFluxGitOps
    print("Checking UK8SFluxGitOps instances...")
    output = run_kubectl([
        "get", "uk8sfluxgitops",
        "-n", namespace,
        "-o", "jsonpath={.items[*].metadata.name}"
    ])

    if output:
        flux_names = output.split()
        print(f"  Found {len(flux_names)} UK8SFluxGitOps instance(s): {', '.join(flux_names)}")
        results["uk8sfluxgitops"]["exists"] = True

        # Check first instance status
        if flux_names:
            flux_status = run_kubectl([
                "get", "uk8sfluxgitops", flux_names[0],
                "-n", namespace,
                "-o", "jsonpath={.status.state}"
            ])
            if flux_status == "ACTIVE":
                print(f"  ✓ UK8SFluxGitOps state is ACTIVE")
                results["uk8sfluxgitops"]["ready"] = True
            else:
                print(f"  ✗ UK8SFluxGitOps state is {flux_status}")
    else:
        print(f"  ⚠ No UK8SFluxGitOps instances found")

    return results


def main():
    """Main validation logic for Section 2."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate KRO resources for UK8S cluster certification"
    )
    parser.add_argument("--instance-name", required=True, help="UK8SCluster instance name")
    parser.add_argument("--namespace", required=True, help="Kubernetes namespace")

    args = parser.parse_args()

    print("=" * 60)
    print("Section 2: KRO Resource Validation")
    print("=" * 60)

    passed = 0
    failed = 0

    # 2.1 Check ResourceGraphDefinitions
    print("\n2.1 ResourceGraphDefinition Status")
    print("-" * 60)

    rgds_to_check = [
        "uk8scluster.kro.run",
        "uk8sjobs.kro.run",
        "uk8sfluxgitops.kro.run"
    ]

    for rgd in rgds_to_check:
        if check_rgd_exists(rgd):
            passed += 1
        else:
            failed += 1

    # 2.2 Check UK8SCluster Instance
    print("\n2.2 UK8SCluster Instance")
    print("-" * 60)

    instance_results = check_uk8s_instance(args.instance_name, args.namespace)

    if instance_results["exists"]:
        passed += 1

        # Check state
        if instance_results["state"] == "ACTIVE":
            passed += 1
        else:
            failed += 1

        # Check conditions
        required_conditions = ["InstanceManaged", "GraphResolved", "ResourcesReady", "Ready"]
        for cond in required_conditions:
            if instance_results["conditions"].get(cond) == "True":
                passed += 1
            else:
                failed += 1
    else:
        failed += 5  # Instance not found, all checks fail

    # 2.3 Check Nested Resources
    print("\n2.3 Nested KRO Resources")
    print("-" * 60)

    nested_results = check_nested_resources(args.namespace)

    # UK8Sjobs
    if nested_results["uk8sjobs"]["exists"]:
        passed += 1
        if nested_results["uk8sjobs"]["ready"]:
            passed += 1
        else:
            failed += 1
    else:
        # Not a failure if not configured
        print("  Note: UK8Sjobs may not be configured")

    # UK8SFluxGitOps
    if nested_results["uk8sfluxgitops"]["exists"]:
        passed += 1
        if nested_results["uk8sfluxgitops"]["ready"]:
            passed += 1
        else:
            failed += 1
    else:
        # Not a failure if not configured
        print("  Note: UK8SFluxGitOps may not be configured")

    # Generate summary
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed out of {total} checks")
    print("=" * 60)

    # Save results
    results = {
        "section": "KRO Resources",
        "passed": passed,
        "failed": failed,
        "total": total,
        "instance": instance_results,
        "nested": nested_results
    }

    with open('/tmp/validation-result.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Exit with error if any critical checks failed
    if failed > 0:
        print(f"\n❌ Section 2 validation failed with {failed} failures")
        sys.exit(1)
    else:
        print(f"\n✅ Section 2 validation passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
