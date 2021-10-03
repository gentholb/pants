# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import textwrap

import pytest

from pants.backend.go.target_types import GoModTarget, GoPackage
from pants.backend.go.util_rules import go_mod, go_pkg, sdk
from pants.backend.go.util_rules.go_pkg import ResolvedGoPackage, ResolveGoPackageRequest
from pants.build_graph.address import Address
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *go_mod.rules(),
            *go_pkg.rules(),
            *sdk.rules(),
            QueryRule(ResolvedGoPackage, [ResolveGoPackageRequest]),
        ],
        target_types=[GoPackage, GoModTarget],
    )
    rule_runner.set_options([], env_inherit={"PATH"})
    return rule_runner


def test_resolve_go_package(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "foo/BUILD": "go_mod()\n",
            "foo/go.mod": textwrap.dedent(
                """\
                module go.example.com/foo
                go 1.17
                """
            ),
            "foo/pkg/BUILD": "go_package()\n",
            "foo/pkg/foo.go": textwrap.dedent(
                """\
                package pkg
                func Grok() string {
                    return "Hello World"
                }
                """
            ),
            "foo/cmd/BUILD": "go_package()\n",
            "foo/cmd/main.go": textwrap.dedent(
                """\
                package main
                import (
                    "fmt"
                    "go.example.com/foo/pkg"
                )
                func main() {
                    fmt.Printf("%s\n", pkg.Grok())
                }
                """
            ),
            "foo/cmd/bar_test.go": textwrap.dedent(
                """\
                package main
                import "testing"
                func TestBar(t *testing.T) {}
                """
            ),
        }
    )
    resolved_go_package = rule_runner.request(
        ResolvedGoPackage, [ResolveGoPackageRequest(Address("foo/cmd"))]
    )

    # Compare field-by-field rather than with a `ResolvedGoPackage` instance because
    # `dependency_import_paths` is so verbose.
    assert resolved_go_package.address == Address("foo/cmd")
    assert resolved_go_package.import_path == "go.example.com/foo/cmd"
    assert resolved_go_package.module_address == Address("foo")
    assert resolved_go_package.package_name == "main"
    assert resolved_go_package.imports == ("fmt", "go.example.com/foo/pkg")
    assert resolved_go_package.test_imports == ("testing",)
    assert resolved_go_package.go_files == ("main.go",)
    assert not resolved_go_package.cgo_files
    assert not resolved_go_package.ignored_go_files
    assert not resolved_go_package.ignored_other_files
    assert resolved_go_package.test_go_files == ("bar_test.go",)
    assert not resolved_go_package.xtest_go_files