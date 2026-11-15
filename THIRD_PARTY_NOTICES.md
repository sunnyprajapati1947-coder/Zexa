# Third-party references and notices

The following projects were cloned locally for study and architectural reference. Their source trees live under the local `sources/` directory and are not copied into Zexa's implementation by default.

- **Open-Jarvis** — https://github.com/tokenarc/open-jarvis — MIT License.
- **Leon AI** — https://github.com/leon-ai/leon — MIT License.
- **OpenHands** — https://github.com/OpenHands/OpenHands — MIT License.
- **Open Interpreter** — https://github.com/openinterpreter/openinterpreter — Apache License 2.0.

Zexa currently uses architectural ideas only (modular skills, tool routing, coding workflows, permission boundaries, and Android integration concepts). No source files from the first four reference projects are intentionally redistributed in this implementation.

If code is later adapted or copied from any upstream project, review the exact source file's license and preserve required copyright, license, NOTICE, and modification notices before distribution. This document is not a substitute for that file-by-file review.

## Build-time native dependency

- **llama.cpp** — https://github.com/ggml-org/llama.cpp — MIT License.
  - Pinned source revision: `e574a17b062be51b98e239ccd3d3743e3d902333`.
  - Fetched at Android CMake configure/build time; it is not copied into the repository.
  - Used by the Android arm64 JNI runtime for local GGUF model inference.
  - Copyright (c) 2023-2026 The ggml authors.

MIT License

Copyright (c) 2023-2026 The ggml authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
