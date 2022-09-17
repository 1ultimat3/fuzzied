# Fuzzied - Continuous Fuzzing for Smart Contracts
This project is heavily inspired by [oss-fuzz](https://github.com/google/oss-fuzz).

[Fuzz testing](https://en.wikipedia.org/wiki/Fuzzing) is a well-known technique for uncovering programming errors in software. Many of these detectable errors, like reentrancy issues, can have serious security implications.

Fuzzied provides a scalable and distributed infrastructure for continuous fuzzing. This apporach makes fuzzing very attractive for developers and security auditors, who can focus on writing testcases. At the same time chances of finding vulnerabilities  are orders of mangitudes better compared to current fuzzing activities in the blockchain space, which mostly rely on very short runs on single machines.

Fuzzied and its workflow are completely open source. Developers needs to create pull requests against the official repository, which is used as the baseline of the continuous fuzzing infrastructure and all fuzzing activities. Relevant stakeholders are informed once a vulnerabiliy is identified during fuzzing. Although [echidna](https://github.com/crytic/echidna) is currently the only integrated fuzzer,  the platform is not limited to it, and as such, other fuzzing engines can be integrated in the future.


## Overview
![fuzzied process digram](docs/process.png)

## Workflow for Harness Developers
Continuously fuzzed targets can be found in the projects folder.
In order to add your project to the distributed fuzzing procedures, you need to
 1.  fork this repo
 2.  copy/add a project (replace the contracts with yours and add test cases to be validated)
 3.  test locally
 4.  create a pull requests
 5.  once merged, you will be notified if your harness has identified a vulnerability
