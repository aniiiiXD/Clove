#pragma once
#include <string>
#include <memory>
#include <atomic>
#include <queue>
#include <unordered_map>
#include <mutex>
#include <chrono>
#include "kernel/reactor.hpp"
#include "kernel/llm_client.hpp"
#include "kernel/permissions.hpp"
#include "ipc/socket_server.hpp"
#include "runtime/agent_process.hpp"
#include <nlohmann/json.hpp>

namespace agentos::kernel {

// IPC Message for agent-to-agent communication
struct IPCMessage {
    uint32_t from_id;
    std::string from_name;
    nlohmann::json message;
    std::chrono::steady_clock::time_point timestamp;
};

// Kernel configuration
struct KernelConfig {
    std::string socket_path = "/tmp/agentos.sock";
    bool enable_sandboxing = true;
    std::string gemini_api_key;          // Gemini API key (or from env)
    std::string llm_model = "gemini-2.0-flash";
};

class Kernel {
public:
    using Config = KernelConfig;

    Kernel();
    explicit Kernel(const Config& config);
    ~Kernel();

    // Non-copyable
    Kernel(const Kernel&) = delete;
    Kernel& operator=(const Kernel&) = delete;

    // Initialize all subsystems
    bool init();

    // Run the kernel (blocks until shutdown)
    void run();

    // Request shutdown
    void shutdown();

    // Check if running
    bool is_running() const { return running_; }

    // Access to agent manager
    runtime::AgentManager& agents() { return *agent_manager_; }

private:
    Config config_;
    std::atomic<bool> running_{false};

    std::unique_ptr<Reactor> reactor_;
    std::unique_ptr<ipc::SocketServer> socket_server_;
    std::unique_ptr<runtime::AgentManager> agent_manager_;
    std::unique_ptr<LLMClient> llm_client_;

    // IPC: Agent mailboxes (message queues per agent)
    std::unordered_map<uint32_t, std::queue<IPCMessage>> agent_mailboxes_;
    std::mutex mailbox_mutex_;

    // IPC: Agent name registry (name -> agent_id)
    std::unordered_map<std::string, uint32_t> agent_names_;
    std::unordered_map<uint32_t, std::string> agent_ids_to_names_;
    std::mutex registry_mutex_;

    // Permissions: Per-agent permissions
    std::unordered_map<uint32_t, AgentPermissions> agent_permissions_;
    std::mutex permissions_mutex_;

    // Get or create permissions for an agent
    AgentPermissions& get_agent_permissions(uint32_t agent_id);

    // Event handlers
    void on_server_event(int fd, uint32_t events);
    void on_client_event(int fd, uint32_t events);

    // Message handler
    ipc::Message handle_message(const ipc::Message& msg);

    // Syscall handlers
    ipc::Message handle_think(const ipc::Message& msg);
    ipc::Message handle_spawn(const ipc::Message& msg);
    ipc::Message handle_kill(const ipc::Message& msg);
    ipc::Message handle_list(const ipc::Message& msg);
    ipc::Message handle_exec(const ipc::Message& msg);
    ipc::Message handle_read(const ipc::Message& msg);
    ipc::Message handle_write(const ipc::Message& msg);

    // IPC syscall handlers
    ipc::Message handle_send(const ipc::Message& msg);
    ipc::Message handle_recv(const ipc::Message& msg);
    ipc::Message handle_broadcast(const ipc::Message& msg);
    ipc::Message handle_register(const ipc::Message& msg);

    // Permission syscall handlers
    ipc::Message handle_get_perms(const ipc::Message& msg);
    ipc::Message handle_set_perms(const ipc::Message& msg);

    // Network syscall handlers
    ipc::Message handle_http(const ipc::Message& msg);

    // Update client in reactor (for write events)
    void update_client_events(int fd);
};

} // namespace agentos::kernel
