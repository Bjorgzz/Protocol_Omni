# Golden Dataset Directory

This directory contains golden evaluation datasets for GEPA (Genetic Evolution of Prompt Agents).

## Structure

```
golden/
├── accuracy/           # Accuracy benchmark tests
│   └── *.jsonl        # Test cases in JSONL format
├── tool_use/          # Tool orchestration tests
│   └── *.jsonl
└── reasoning/         # Complex reasoning tests
    └── *.jsonl
```

## Format

Each test case is a JSON object with:
- `input`: The user prompt/query
- `expected`: Expected output or behavior
- `metadata`: Optional test metadata

## Adding Tests

Add new JSONL files to the appropriate category directory.
Tests are automatically discovered by GEPA during evaluation.
