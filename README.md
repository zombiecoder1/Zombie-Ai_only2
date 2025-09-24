# 🧟‍♂️ ZombieCoder - Hello Zombie AI Agent

> **যেখানে কোড ও কথা বলে** | Where Code and Conversation Meet

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-orange.svg)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Overview

**ZombieCoder** is a powerful local AI agent system that combines FastAPI backend with Ollama LLM integration, providing a complete development assistant experience. Built with industry best practices, it offers OpenAI-compatible endpoints, advanced caching, connection pooling, and comprehensive monitoring.

## ✨ Features

### 🧠 **AI Capabilities**
- **Local Ollama Integration** - No cloud dependencies
- **OpenAI-Compatible API** - Works with Cursor AI, VS Code extensions
- **Multi-Model Support** - gemma:2b, deepseek-coder, qwen2.5-coder
- **Response Caching** - 1000 entries, 1-hour TTL
- **Session Management** - Persistent conversation context

### 🚀 **Performance & Optimization**
- **Connection Pooling** - 10 max database connections
- **Automatic Cleanup** - 30-day conversation retention
- **Real-time Monitoring** - Performance metrics and health checks
- **Memory Management** - SQLite-based conversation storage

### 🛠️ **Developer Experience**
- **VSCode Extension** - TypeScript-based extension
- **Interactive Dashboard** - Real-time monitoring and control
- **Command Interface** - Easy server management
- **Meta Memory System** - Configurable agent behavior

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VSCode        │    │   FastAPI       │    │   Ollama        │
│   Extension     │◄──►│   Main Server   │◄──►│   Local AI      │
│   (TypeScript)  │    │   (Python)      │    │   (Port 11434)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite        │
                       │   Memory DB     │
                       │   (Conversations)│
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Ollama installed and running
- Node.js (for extension development)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/zombiecoder1/Zombie-Ai_only2.git
cd Zombie-Ai_only2
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Start Ollama server**
```bash
ollama serve
```

4. **Run the main server**
```bash
python main_server.py
```

5. **Access the dashboard**
Open `http://localhost:12346` in your browser

## 📁 Project Structure

```
ZombieCoder Main Server/
├── main_server.py              # FastAPI main server
├── requirements.txt            # Python dependencies
├── config/
│   └── agents/
│       └── zombiecoder_meta.json  # Agent meta memory
├── Extension/                  # VSCode extension
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   └── extension.ts
│   └── LICENSE
├── data/
│   └── memory/                 # SQLite database
├── index.html                  # Main dashboard
├── cmd.html                    # Command interface
└── README.md
```

## 🔧 Configuration

### Agent Meta Memory
The agent behavior is configured through `config/agents/zombiecoder_meta.json`:

```json
{
  "agent_name": "ZombieCoder",
  "tagline": "যেখানে কোড ও কথা বলে",
  "owner": "Sahon Srabon",
  "company": "Developer Zone",
  "core_rules": {
    "prefix": "ভাইয়া",
    "tone": "বন্ধুসুলভ, সত্যবাদী",
    "skills": ["Laravel", "Node.js", "Python", "AI Integration"]
  }
}
```

### Server Configuration
Edit `Extension/agent_config/hello_zombie.yaml` for server settings:

```yaml
infrastructure:
  ollama:
    host: "http://localhost:11434"
    model_name: "gemma:2b"
  main_server:
    url: "http://localhost:12346"
  memory:
    location: "data/memory/hello_zombie_memory.sqlite"
```

## 🌐 API Endpoints

### Core Endpoints
- `GET /health` - Server health check
- `GET /performance` - Performance metrics
- `GET /v1/models` - Available models
- `POST /v1/chat/completions` - OpenAI-compatible chat

### Example Usage

**Health Check:**
```bash
curl http://localhost:12346/health
```

**Chat Completion:**
```bash
curl -X POST http://localhost:12346/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma:2b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 🔌 Cursor AI Integration

To use ZombieCoder with Cursor AI:

1. Open Cursor AI Settings → Model Provider
2. Set Provider: `Custom`
3. Set Base URL: `http://localhost:12346/v1`
4. Set API Key: `dummy` (local server)
5. Test the connection

## 📊 Monitoring & Logs

### Dashboard Features
- **Real-time Status** - Server and Ollama health
- **Performance Metrics** - Cache hit rates, response times
- **Memory Usage** - Database size and connections
- **Command Interface** - Easy server management

### Log Files
- `main_server.log` - Server logs
- `data/memory/hello_zombie_memory.sqlite` - Conversation database

## 🛡️ Security Features

- **Local-Only Operation** - No external API calls
- **CORS Protection** - Configurable origins
- **User Permission Required** - Terminal command confirmation
- **Input Validation** - Pydantic model validation
- **Rate Limiting** - Built-in request throttling

## 🧪 Testing

### Manual Testing
```bash
# Test server health
curl http://localhost:12346/health

# Test Ollama connection
curl http://localhost:11434/api/tags

# Test chat endpoint
curl -X POST http://localhost:12346/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma:2b", "messages": [{"role": "user", "content": "Test"}]}'
```

### Automated Testing
Use the dashboard at `http://localhost:12346` for interactive testing.

## 🚀 Performance Optimization

### Caching
- **Response Cache** - 1000 entries, 1-hour TTL
- **Database Pooling** - 10 max connections
- **Auto Cleanup** - 30-day retention policy

### Monitoring
- **Real-time Metrics** - Performance dashboard
- **Health Checks** - Automated status monitoring
- **Log Analysis** - Comprehensive logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Sahon Srabon**
- Company: Developer Zone
- Contact: +880 1323-626282
- Email: infi@zombiecoder.my.id
- Website: https://zombiecoder.my.id/

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for local AI capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [VSCode](https://code.visualstudio.com/) for the extension platform

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact: +880 1323-626282
- Email: infi@zombiecoder.my.id

---

**Made with ❤️ by ZombieCoder Team**

*যেখানে কোড ও কথা বলে | Where Code and Conversation Meet*
