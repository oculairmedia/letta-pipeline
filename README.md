# Letta Pipeline for Open WebUI

A pipeline integration for Open WebUI that connects to the Letta AI API, providing streaming responses with event emitters and development tools.

## Features

- Streaming responses with event emitters
- Development mode with detailed logging
- Support for reasoning steps and usage statistics
- Tool integration with Open WebUI
- Configurable settings through valves
- Comprehensive test suite

## Installation

1. Clone this repository:
```bash
git clone https://github.com/oculairmedia/letta-pipeline.git
cd letta-pipeline
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export LETTA_BASE_URL="https://letta2.oculair.ca"
export LETTA_AGENT_ID="your-agent-id"
export LETTA_PASSWORD="your-password"
```

## Usage

1. Import and initialize the pipeline:
```python
from letta import Pipe

pipe = Pipe()
```

2. Use the pipeline in Open WebUI:
```python
# The pipeline will be automatically registered with Open WebUI
# and will appear in the model selection dropdown
```

## Development

1. Enable development mode:
```python
pipe.valves.DEV_MODE = True
pipe.valves.LOG_RAW_CHUNKS = True
pipe.valves.LOG_PARSED_CHUNKS = True
pipe.valves.LOG_EVENTS = True
pipe.valves.SAVE_RESPONSES = True
```

2. Run tests:
```bash
python test_letta_dev.py
```

## License

MIT License