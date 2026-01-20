#include "kernel/kernel.hpp"
#include <spdlog/spdlog.h>
#include <sys/epoll.h>
#include <sys/wait.h>
#include <csignal>
#include <fstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace agentos::kernel {

// Global kernel pointer for signal handling
static Kernel* g_kernel = nullptr;

static void signal_handler(int signum) {
    spdlog::info("Received signal {}, shutting down...", signum);
    if (g_kernel) {
        g_kernel->shutdown();
    }
}

Kernel::Kernel()
    : Kernel(Config{}) {}

Kernel::Kernel(const Config& config)
    : config_(config)
    , reactor_(std::make_unique<Reactor>())
    , socket_server_(std::make_unique<ipc::SocketServer>(config.socket_path))
    , agent_manager_(std::make_unique<runtime::AgentManager>(config.socket_path))
{
    // Initialize LLM client
    LLMConfig llm_config;
    llm_config.api_key = config.gemini_api_key;
    llm_config.model = config.llm_model;
    llm_client_ = std::make_unique<LLMClient>(llm_config);
}

Kernel::~Kernel() {
    if (g_kernel == this) {
        g_kernel = nullptr;
    }
}

bool Kernel::init() {
    spdlog::info("Initializing AgentOS Kernel...");

    // Initialize reactor
    if (!reactor_->init()) {
        spdlog::error("Failed to initialize reactor");
        return false;
    }

    // Set up message handler
    socket_server_->set_handler([this](const ipc::Message& msg) {
        return handle_message(msg);
    });

    // Initialize socket server
    if (!socket_server_->init()) {
        spdlog::error("Failed to initialize socket server");
        return false;
    }

    // Add server socket to reactor
    int server_fd = socket_server_->get_server_fd();
    reactor_->add(server_fd, EPOLLIN, [this](int fd, uint32_t events) {
        on_server_event(fd, events);
    });

    // Set up signal handlers
    g_kernel = this;
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    spdlog::info("Kernel initialized successfully");
    spdlog::info("Sandboxing: {}", config_.enable_sandboxing ? "enabled" : "disabled");
    spdlog::info("LLM: {} ({})",
        llm_client_->is_configured() ? "configured" : "not configured",
        llm_client_->config().model);
    return true;
}

void Kernel::run() {
    running_ = true;
    spdlog::info("AgentOS Kernel v0.1.0 running");
    spdlog::info("Listening on: {}", config_.socket_path);
    spdlog::info("Press Ctrl+C to exit");

    while (running_) {
        int n = reactor_->poll(100);
        if (n < 0) {
            spdlog::error("Reactor error, exiting");
            break;
        }

        // Reap dead agents periodically
        agent_manager_->reap_agents();
    }

    spdlog::info("Kernel shutting down...");
    agent_manager_->stop_all();
    socket_server_->stop();
    spdlog::info("Kernel stopped");
}

void Kernel::shutdown() {
    running_ = false;
}

std::string Kernel::get_llm_model() const {
    if (llm_client_) {
        return llm_client_->config().model;
    }
    return config_.llm_model;
}

void Kernel::on_server_event(int fd, uint32_t events) {
    if (events & EPOLLIN) {
        // Accept new connections
        while (true) {
            int client_fd = socket_server_->accept_connection();
            if (client_fd < 0) {
                break;
            }

            // Add client to reactor
            reactor_->add(client_fd, EPOLLIN | EPOLLHUP | EPOLLERR,
                [this](int cfd, uint32_t ev) {
                    on_client_event(cfd, ev);
                });
        }
    }
}

void Kernel::on_client_event(int fd, uint32_t events) {
    // Handle errors and hangups
    if (events & (EPOLLHUP | EPOLLERR)) {
        reactor_->remove(fd);
        socket_server_->remove_client(fd);
        return;
    }

    // Handle readable
    if (events & EPOLLIN) {
        if (!socket_server_->handle_client(fd)) {
            reactor_->remove(fd);
            socket_server_->remove_client(fd);
            return;
        }
    }

    // Handle writable
    if (events & EPOLLOUT) {
        if (!socket_server_->flush_client(fd)) {
            reactor_->remove(fd);
            socket_server_->remove_client(fd);
            return;
        }
    }

    // Update events based on write buffer
    update_client_events(fd);
}

void Kernel::update_client_events(int fd) {
    uint32_t events = EPOLLIN | EPOLLHUP | EPOLLERR;
    if (socket_server_->client_wants_write(fd)) {
        events |= EPOLLOUT;
    }
    reactor_->modify(fd, events);
}

ipc::Message Kernel::handle_message(const ipc::Message& msg) {
    switch (msg.opcode) {
        case ipc::SyscallOp::SYS_NOOP:
            // Echo the payload back
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_NOOP, msg.payload);

        case ipc::SyscallOp::SYS_EXIT:
            spdlog::info("Agent {} requested exit", msg.agent_id);
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXIT, "goodbye");

        case ipc::SyscallOp::SYS_THINK:
            return handle_think(msg);

        case ipc::SyscallOp::SYS_SPAWN:
            return handle_spawn(msg);

        case ipc::SyscallOp::SYS_KILL:
            return handle_kill(msg);

        case ipc::SyscallOp::SYS_LIST:
            return handle_list(msg);

        case ipc::SyscallOp::SYS_EXEC:
            return handle_exec(msg);

        case ipc::SyscallOp::SYS_READ:
            return handle_read(msg);

        case ipc::SyscallOp::SYS_WRITE:
            return handle_write(msg);

        // IPC syscalls
        case ipc::SyscallOp::SYS_SEND:
            return handle_send(msg);

        case ipc::SyscallOp::SYS_RECV:
            return handle_recv(msg);

        case ipc::SyscallOp::SYS_BROADCAST:
            return handle_broadcast(msg);

        case ipc::SyscallOp::SYS_REGISTER:
            return handle_register(msg);

        // Permission syscalls
        case ipc::SyscallOp::SYS_GET_PERMS:
            return handle_get_perms(msg);

        case ipc::SyscallOp::SYS_SET_PERMS:
            return handle_set_perms(msg);

        // Network syscalls
        case ipc::SyscallOp::SYS_HTTP:
            return handle_http(msg);

        default:
            spdlog::warn("Unknown opcode: 0x{:02x}", static_cast<uint8_t>(msg.opcode));
            return ipc::Message(msg.agent_id, msg.opcode, msg.payload);
    }
}

ipc::Message Kernel::handle_think(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    // Check if LLM is configured
    if (!llm_client_->is_configured()) {
        json response;
        response["success"] = false;
        response["error"] = "LLM not configured (set GEMINI_API_KEY)";
        response["content"] = "";
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_THINK, response.dump());
    }

    // Check LLM permission and quota
    if (!perms.can_use_llm()) {
        spdlog::warn("Agent {} denied LLM access (quota exceeded or permission denied)", msg.agent_id);
        json response;
        response["success"] = false;
        response["error"] = "Permission denied: LLM quota exceeded or not allowed";
        response["content"] = "";
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_THINK, response.dump());
    }

    std::string payload = msg.payload_str();
    spdlog::debug("Agent {} thinking: {}", msg.agent_id,
        payload.length() > 50 ? payload.substr(0, 50) + "..." : payload);

    // Call LLM service with extended options (supports JSON payload)
    auto result = llm_client_->complete_with_options(payload);

    // Track tokens in agent (if successful)
    if (result.success && result.tokens_used > 0) {
        auto agent = agent_manager_->get_agent(msg.agent_id);
        if (agent) {
            agent->record_llm_call(result.tokens_used);
        }
        // Also track in permissions for quota enforcement
        perms.record_llm_usage(result.tokens_used);
    }

    json response;
    response["success"] = result.success;
    if (result.success) {
        response["content"] = result.content;
        response["tokens"] = result.tokens_used;
        spdlog::debug("LLM response: {} tokens", result.tokens_used);
    } else {
        response["error"] = result.error;
        response["content"] = "";
        spdlog::warn("LLM error for agent {}: {}", msg.agent_id, result.error);
    }

    return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_THINK, response.dump());
}

ipc::Message Kernel::handle_spawn(const ipc::Message& msg) {
    // Parse JSON payload: {"name": "agent1", "script": "/path/to/script.py"}
    try {
        json j = json::parse(msg.payload_str());

        runtime::AgentConfig config;
        config.name = j.value("name", "agent_" + std::to_string(runtime::AgentProcess::generate_id()));
        config.script_path = j.value("script", "");
        config.python_path = j.value("python", "python3");
        config.sandboxed = config_.enable_sandboxing && j.value("sandboxed", true);
        config.enable_network = j.value("network", false);

        // Resource limits
        if (j.contains("limits")) {
            auto& lim = j["limits"];
            config.limits.memory_limit_bytes = lim.value("memory", 256 * 1024 * 1024);
            config.limits.max_pids = lim.value("max_pids", 64);
            config.limits.cpu_quota_us = lim.value("cpu_quota", 100000);
        }

        if (config.script_path.empty()) {
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SPAWN,
                R"({"error": "script path required"})");
        }

        spdlog::info("Spawning agent: {} (script={})", config.name, config.script_path);

        auto agent = agent_manager_->spawn_agent(config);
        if (!agent) {
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SPAWN,
                R"({"error": "failed to spawn agent"})");
        }

        // Track parent-child relationship
        agent->set_parent_id(msg.agent_id);

        // Update parent's child list (if parent exists)
        if (msg.agent_id > 0) {
            auto parent = agent_manager_->get_agent(msg.agent_id);
            if (parent) {
                parent->add_child(agent->id());
            }
        }

        json response;
        response["id"] = agent->id();
        response["name"] = agent->name();
        response["pid"] = agent->pid();
        response["status"] = "running";

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SPAWN, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse spawn request: {}", e.what());
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SPAWN,
            R"({"error": "invalid JSON"})");
    }
}

ipc::Message Kernel::handle_kill(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());

        bool killed = false;
        if (j.contains("id")) {
            killed = agent_manager_->kill_agent(j["id"].get<uint32_t>());
        } else if (j.contains("name")) {
            killed = agent_manager_->kill_agent(j["name"].get<std::string>());
        }

        json response;
        response["killed"] = killed;

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_KILL, response.dump());

    } catch (const std::exception& e) {
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_KILL,
            R"({"error": "invalid request"})");
    }
}

ipc::Message Kernel::handle_list(const ipc::Message& msg) {
    json response = json::array();

    for (const auto& agent : agent_manager_->list_agents()) {
        json a;
        a["id"] = agent->id();
        a["name"] = agent->name();
        a["pid"] = agent->pid();
        a["state"] = runtime::agent_state_to_string(agent->state());
        a["running"] = agent->is_running();
        response.push_back(a);
    }

    return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_LIST, response.dump());
}

ipc::Message Kernel::handle_exec(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    try {
        json j = json::parse(msg.payload_str());
        std::string command = j.value("command", "");
        std::string cwd = j.value("cwd", "");
        int timeout_sec = j.value("timeout", 30);

        if (command.empty()) {
            json response;
            response["success"] = false;
            response["error"] = "command required";
            response["stdout"] = "";
            response["stderr"] = "";
            response["exit_code"] = -1;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXEC, response.dump());
        }

        // Check permission
        if (!perms.can_execute_command(command)) {
            spdlog::warn("Agent {} denied exec: {}", msg.agent_id, command);
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: command not allowed";
            response["stdout"] = "";
            response["stderr"] = "";
            response["exit_code"] = -1;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXEC, response.dump());
        }

        spdlog::debug("Agent {} executing: {}", msg.agent_id, command);

        // Build the full command (with optional cwd)
        std::string full_command = command;
        if (!cwd.empty()) {
            full_command = "cd " + cwd + " && " + command;
        }
        // Redirect stderr to stdout with marker
        full_command += " 2>&1";

        // Execute via popen
        FILE* pipe = popen(full_command.c_str(), "r");
        if (!pipe) {
            json response;
            response["success"] = false;
            response["error"] = "failed to execute command";
            response["stdout"] = "";
            response["stderr"] = "";
            response["exit_code"] = -1;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXEC, response.dump());
        }

        // Read output
        std::string output;
        char buffer[4096];
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            output += buffer;
        }

        // Get exit code
        int status = pclose(pipe);
        int exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;

        json response;
        response["success"] = (exit_code == 0);
        response["stdout"] = output;
        response["stderr"] = "";  // Combined with stdout
        response["exit_code"] = exit_code;

        spdlog::debug("Command exit code: {}", exit_code);
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXEC, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse exec request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        response["stdout"] = "";
        response["stderr"] = "";
        response["exit_code"] = -1;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_EXEC, response.dump());
    }
}

ipc::Message Kernel::handle_read(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    try {
        json j = json::parse(msg.payload_str());
        std::string path = j.value("path", "");

        if (path.empty()) {
            json response;
            response["success"] = false;
            response["error"] = "path required";
            response["content"] = "";
            response["size"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_READ, response.dump());
        }

        // Check permission
        if (!perms.can_read_path(path)) {
            spdlog::warn("Agent {} denied read access to: {}", msg.agent_id, path);
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: path not allowed for reading";
            response["content"] = "";
            response["size"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_READ, response.dump());
        }

        spdlog::debug("Agent {} reading file: {}", msg.agent_id, path);

        // Open and read file
        std::ifstream file(path, std::ios::binary);
        if (!file.is_open()) {
            json response;
            response["success"] = false;
            response["error"] = "failed to open file";
            response["content"] = "";
            response["size"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_READ, response.dump());
        }

        // Get file size
        file.seekg(0, std::ios::end);
        size_t size = file.tellg();
        file.seekg(0, std::ios::beg);

        // Read content
        std::string content(size, '\0');
        file.read(&content[0], size);
        file.close();

        json response;
        response["success"] = true;
        response["content"] = content;
        response["size"] = size;

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_READ, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse read request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        response["content"] = "";
        response["size"] = 0;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_READ, response.dump());
    }
}

ipc::Message Kernel::handle_write(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    try {
        json j = json::parse(msg.payload_str());
        std::string path = j.value("path", "");
        std::string content = j.value("content", "");
        std::string mode = j.value("mode", "write");  // "write" or "append"

        if (path.empty()) {
            json response;
            response["success"] = false;
            response["error"] = "path required";
            response["bytes_written"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_WRITE, response.dump());
        }

        // Check permission
        if (!perms.can_write_path(path)) {
            spdlog::warn("Agent {} denied write access to: {}", msg.agent_id, path);
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: path not allowed for writing";
            response["bytes_written"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_WRITE, response.dump());
        }

        spdlog::debug("Agent {} writing file: {} (mode={})", msg.agent_id, path, mode);

        // Open file with appropriate mode
        std::ios_base::openmode file_mode = std::ios::binary;
        if (mode == "append") {
            file_mode |= std::ios::app;
        } else {
            file_mode |= std::ios::trunc;
        }

        std::ofstream file(path, file_mode);
        if (!file.is_open()) {
            json response;
            response["success"] = false;
            response["error"] = "failed to open file for writing";
            response["bytes_written"] = 0;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_WRITE, response.dump());
        }

        // Write content
        file.write(content.data(), content.size());
        file.close();

        json response;
        response["success"] = true;
        response["bytes_written"] = content.size();

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_WRITE, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse write request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        response["bytes_written"] = 0;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_WRITE, response.dump());
    }
}

// ============================================================================
// IPC Handlers - Inter-Agent Communication
// ============================================================================

ipc::Message Kernel::handle_register(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());
        std::string name = j.value("name", "");

        if (name.empty()) {
            json response;
            response["success"] = false;
            response["error"] = "name required";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_REGISTER, response.dump());
        }

        {
            std::lock_guard<std::mutex> lock(registry_mutex_);

            // Check if name already taken
            if (agent_names_.count(name) > 0 && agent_names_[name] != msg.agent_id) {
                json response;
                response["success"] = false;
                response["error"] = "name already registered";
                return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_REGISTER, response.dump());
            }

            // Register the name
            agent_names_[name] = msg.agent_id;
            agent_ids_to_names_[msg.agent_id] = name;
        }

        spdlog::info("Agent {} registered as '{}'", msg.agent_id, name);

        json response;
        response["success"] = true;
        response["agent_id"] = msg.agent_id;
        response["name"] = name;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_REGISTER, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse register request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_REGISTER, response.dump());
    }
}

ipc::Message Kernel::handle_send(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());

        // Determine target agent
        uint32_t target_id = j.value("to", 0u);
        std::string target_name = j.value("to_name", "");
        json message_content = j.value("message", json::object());

        // Resolve name to ID if needed
        if (target_id == 0 && !target_name.empty()) {
            std::lock_guard<std::mutex> lock(registry_mutex_);
            if (agent_names_.count(target_name) > 0) {
                target_id = agent_names_[target_name];
            } else {
                json response;
                response["success"] = false;
                response["error"] = "target agent not found: " + target_name;
                return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SEND, response.dump());
            }
        }

        if (target_id == 0) {
            json response;
            response["success"] = false;
            response["error"] = "target agent required (to or to_name)";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SEND, response.dump());
        }

        // Get sender's name
        std::string sender_name;
        {
            std::lock_guard<std::mutex> lock(registry_mutex_);
            if (agent_ids_to_names_.count(msg.agent_id) > 0) {
                sender_name = agent_ids_to_names_[msg.agent_id];
            }
        }

        // Create IPC message
        IPCMessage ipc_msg;
        ipc_msg.from_id = msg.agent_id;
        ipc_msg.from_name = sender_name;
        ipc_msg.message = message_content;
        ipc_msg.timestamp = std::chrono::steady_clock::now();

        // Queue message for target
        {
            std::lock_guard<std::mutex> lock(mailbox_mutex_);
            agent_mailboxes_[target_id].push(ipc_msg);
        }

        spdlog::debug("Agent {} sent message to agent {}", msg.agent_id, target_id);

        json response;
        response["success"] = true;
        response["delivered_to"] = target_id;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SEND, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse send request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SEND, response.dump());
    }
}

ipc::Message Kernel::handle_recv(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());
        int max_messages = j.value("max", 10);  // Default: retrieve up to 10 messages
        bool wait = j.value("wait", false);     // Non-blocking by default

        json messages_array = json::array();

        {
            std::lock_guard<std::mutex> lock(mailbox_mutex_);

            auto& mailbox = agent_mailboxes_[msg.agent_id];
            int count = 0;

            while (!mailbox.empty() && count < max_messages) {
                const IPCMessage& ipc_msg = mailbox.front();

                // Calculate time since message was sent
                auto now = std::chrono::steady_clock::now();
                auto age_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                    now - ipc_msg.timestamp).count();

                json msg_json;
                msg_json["from"] = ipc_msg.from_id;
                msg_json["from_name"] = ipc_msg.from_name;
                msg_json["message"] = ipc_msg.message;
                msg_json["age_ms"] = age_ms;

                messages_array.push_back(msg_json);
                mailbox.pop();
                count++;
            }
        }

        json response;
        response["success"] = true;
        response["messages"] = messages_array;
        response["count"] = messages_array.size();
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_RECV, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse recv request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        response["messages"] = json::array();
        response["count"] = 0;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_RECV, response.dump());
    }
}

ipc::Message Kernel::handle_broadcast(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());
        json message_content = j.value("message", json::object());
        bool include_self = j.value("include_self", false);

        // Get sender's name
        std::string sender_name;
        {
            std::lock_guard<std::mutex> lock(registry_mutex_);
            if (agent_ids_to_names_.count(msg.agent_id) > 0) {
                sender_name = agent_ids_to_names_[msg.agent_id];
            }
        }

        // Create IPC message
        IPCMessage ipc_msg;
        ipc_msg.from_id = msg.agent_id;
        ipc_msg.from_name = sender_name;
        ipc_msg.message = message_content;
        ipc_msg.timestamp = std::chrono::steady_clock::now();

        // Get all registered agents and queue message
        int delivered_count = 0;
        {
            std::lock_guard<std::mutex> reg_lock(registry_mutex_);
            std::lock_guard<std::mutex> mail_lock(mailbox_mutex_);

            for (const auto& [agent_id, name] : agent_ids_to_names_) {
                // Skip sender unless include_self is true
                if (agent_id == msg.agent_id && !include_self) {
                    continue;
                }

                agent_mailboxes_[agent_id].push(ipc_msg);
                delivered_count++;
            }
        }

        spdlog::debug("Agent {} broadcast message to {} agents", msg.agent_id, delivered_count);

        json response;
        response["success"] = true;
        response["delivered_count"] = delivered_count;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_BROADCAST, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse broadcast request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        response["delivered_count"] = 0;
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_BROADCAST, response.dump());
    }
}

// ============================================================================
// Permission Handlers
// ============================================================================

AgentPermissions& Kernel::get_agent_permissions(uint32_t agent_id) {
    std::lock_guard<std::mutex> lock(permissions_mutex_);

    auto it = agent_permissions_.find(agent_id);
    if (it == agent_permissions_.end()) {
        // Create default permissions for new agent (STANDARD level)
        agent_permissions_[agent_id] = AgentPermissions::from_level(PermissionLevel::STANDARD);
    }
    return agent_permissions_[agent_id];
}

ipc::Message Kernel::handle_get_perms(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    json response;
    response["success"] = true;
    response["permissions"] = perms.to_json();

    return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_GET_PERMS, response.dump());
}

ipc::Message Kernel::handle_set_perms(const ipc::Message& msg) {
    try {
        json j = json::parse(msg.payload_str());

        uint32_t target_id = j.value("agent_id", msg.agent_id);
        auto& caller_perms = get_agent_permissions(msg.agent_id);

        // Only agents with can_spawn permission can set other agents' permissions
        if (target_id != msg.agent_id && !caller_perms.can_spawn) {
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: cannot modify other agent's permissions";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SET_PERMS, response.dump());
        }

        // Parse and set new permissions
        if (j.contains("permissions")) {
            std::lock_guard<std::mutex> lock(permissions_mutex_);
            agent_permissions_[target_id] = AgentPermissions::from_json(j["permissions"]);
            spdlog::info("Agent {} set permissions for agent {}", msg.agent_id, target_id);
        } else if (j.contains("level")) {
            std::string level_str = j["level"].get<std::string>();
            PermissionLevel level = PermissionLevel::STANDARD;

            if (level_str == "unrestricted") level = PermissionLevel::UNRESTRICTED;
            else if (level_str == "standard") level = PermissionLevel::STANDARD;
            else if (level_str == "sandboxed") level = PermissionLevel::SANDBOXED;
            else if (level_str == "readonly") level = PermissionLevel::READONLY;
            else if (level_str == "minimal") level = PermissionLevel::MINIMAL;

            std::lock_guard<std::mutex> lock(permissions_mutex_);
            agent_permissions_[target_id] = AgentPermissions::from_level(level);
            spdlog::info("Agent {} set permission level {} for agent {}", msg.agent_id, level_str, target_id);
        }

        json response;
        response["success"] = true;
        response["agent_id"] = target_id;

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SET_PERMS, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse set_perms request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_SET_PERMS, response.dump());
    }
}

// ============================================================================
// HTTP Handler
// ============================================================================

ipc::Message Kernel::handle_http(const ipc::Message& msg) {
    auto& perms = get_agent_permissions(msg.agent_id);

    try {
        json j = json::parse(msg.payload_str());
        std::string method = j.value("method", "GET");
        std::string url = j.value("url", "");
        int timeout = j.value("timeout", 30);

        if (url.empty()) {
            json response;
            response["success"] = false;
            response["error"] = "URL required";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());
        }

        // Check HTTP permission
        if (!perms.can_http) {
            spdlog::warn("Agent {} denied HTTP access (permission denied)", msg.agent_id);
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: HTTP not allowed";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());
        }

        // Check domain whitelist
        std::string domain = PermissionChecker::extract_domain(url);
        if (!perms.can_access_domain(domain)) {
            spdlog::warn("Agent {} denied access to domain: {}", msg.agent_id, domain);
            json response;
            response["success"] = false;
            response["error"] = "Permission denied: domain not in whitelist: " + domain;
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());
        }

        spdlog::debug("Agent {} making {} request to {}", msg.agent_id, method, url);

        // Build curl command
        std::string curl_cmd = "curl -s -X " + method;
        curl_cmd += " --max-time " + std::to_string(timeout);

        // Add headers if present
        if (j.contains("headers") && j["headers"].is_object()) {
            for (auto& [key, val] : j["headers"].items()) {
                curl_cmd += " -H '" + key + ": " + val.get<std::string>() + "'";
            }
        }

        // Add body if present (for POST/PUT)
        if (j.contains("body") && (method == "POST" || method == "PUT" || method == "PATCH")) {
            std::string body = j["body"].get<std::string>();
            curl_cmd += " -d '" + body + "'";
        }

        curl_cmd += " '" + url + "' 2>&1";

        // Execute curl
        FILE* pipe = popen(curl_cmd.c_str(), "r");
        if (!pipe) {
            json response;
            response["success"] = false;
            response["error"] = "Failed to execute HTTP request";
            return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());
        }

        std::string output;
        char buffer[4096];
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            output += buffer;
        }

        int status = pclose(pipe);
        bool success = (WIFEXITED(status) && WEXITSTATUS(status) == 0);

        json response;
        response["success"] = success;
        response["body"] = output;
        response["status_code"] = success ? 200 : 0;  // Simplified - curl doesn't give us status code easily

        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse HTTP request: {}", e.what());
        json response;
        response["success"] = false;
        response["error"] = std::string("invalid request: ") + e.what();
        return ipc::Message(msg.agent_id, ipc::SyscallOp::SYS_HTTP, response.dump());
    }
}

} // namespace agentos::kernel
