# o0_o.core

Cross-platform command execution primitives for Ansible.

## Overview

This collection provides foundational base classes and utilities for
cross-platform command execution in Ansible. It abstracts platform
differences (POSIX, Windows) and provides unified interfaces for running
commands, parsing results, and managing templates.

## Documentation

Full documentation is available at:
https://o0-o.github.io/ansible-collection-core/

## Installation

```bash
ansible-galaxy collection install o0_o.core
```

> **Note:** This collection provides the core base classes used by
> `o0_o.posix` and `o0_o.windows`. Install platform-specific collections
> as needed for your target systems.

## Dependencies

- `o0_o.utils` >= 2.0.0

## Contributing

See the [AGENTS guide](https://github.com/o0-o/ansible-collections/blob/main/AGENTS.md)
for contributor standards.

## License

Licensed under the
[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.txt)
or later (GPLv3+)
