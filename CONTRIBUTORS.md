# Kairo Phantom - Contributors & Community

Welcome to Kairo Phantom! We are thrilled to have you here. This project aims to be the category-defining open-source document intelligence layer, and we can only achieve that with a strong community.

## 🤝 Getting Involved

Whether you're fixing a typo, writing documentation, reporting a bug, or implementing a new feature, your contributions are welcome and valued.

### Beta Testers
*v0.4.0-beta.1 Testers*
(Add your name here when you test our beta releases!)
- @tester1
- @tester2

### 🎯 Good First Issues (Pick one up in under an hour!)

We have curated a few introductory tasks to help you get familiar with the codebase. Look for the `good first issue` label on our GitHub Issues. 

Here are some current examples you can claim:
1. **[Docs] Add a troubleshooting guide for Linux X11 clipboards** 
   - *Goal*: Document the `xclip` or `xsel` requirement for users on X11 if they hit a clipboard error.
2. **[Tests] Write an edge-case test for the UIA window parser**
   - *Goal*: Add a `proptest` or unit test in `phantom-core/tests/` to verify behavior when a window title contains obscure unicode characters.
3. **[Core] Add a `--version` flag to the CLI**
   - *Goal*: Make `kairo-phantom --version` output the current build version.

## 🛠️ How to Contribute

1. **Fork the repo** and clone it locally.
2. **Create a branch** for your feature or bugfix (`git checkout -b feature/my-cool-feature`).
3. **Run the tests** (`cargo test --workspace`) before making changes.
4. **Commit your changes** using conventional commits.
5. **Push to your fork** and open a Pull Request.

## 💬 Community Channels

- **GitHub Discussions**: Use the "Show and Tell", "Help", and "Plugin Ideas" categories.
- **Discord**: Join our Discord server (link coming soon) to chat with the maintainers. Channels include `#general`, `#plugins`, `#bug-reports`, and `#enterprise`.

## 🐛 Reporting Bugs

When reporting a bug, please include:
- OS version (Windows 11, macOS Sonoma, Ubuntu 24.04, etc.)
- The application you were using (Word, VS Code, Chrome, etc.)
- What you expected to happen vs what actually happened.
- Any errors in the Kairo overlay or logs.
